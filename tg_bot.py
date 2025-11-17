import os
import io
import re
import aiohttp
import urllib.parse
import json
import random
import ydb
from functools import partial
from telegram import Update
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from foundation_models_api.stt import (
    send_file_to_recognizer,
    get_recognition,
    parse_recognition_result,
)
from foundation_models_api.yandex_art import send_prompt, get_image
from foundation_models_api.ml_sdk import promt_request
from botlogger.logger import logger
from settings import s3, driver


RECOGNIZE_TOKEN = os.getenv("RECOGNIZE_TOKEN")
ART_TOKEN = os.getenv("ART_TOKEN")
BUCKET_NAME = os.getenv("BUCKET_NAME")
BUCKET_FOLDER = os.getenv("BUCKET_FOLDER")
ORGID = os.getenv("ORGID")
OAUTH_TOKEN = os.getenv("OAUTH_TOKEN")
HEADER = os.getenv("HEADER")
TG_TOKEN = os.getenv("TG_TOKEN")
FOLDER_ID = os.getenv("FOLDER_ID")
INCLUDED_TG_LOGINS = os.getenv("INCLUDED_TG_LOGINS")


def user_check():
    def decorator(func):
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if update.message.from_user.username in INCLUDED_TG_LOGINS.split(","):
                return await func(update, context)
            else:
                await update.message.reply_text(
                    "You are not allowed to use this command."
                )

        return wrapper

    return decorator


async def create_comment(
    issue_key: str,
    reply_text: str,
    user: str,
    header: str,
    orgid: str,
    oauth_token: str,
):
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.tracker.yandex.net/v2/issues/{issue_key}/comments"
            headers = {
                header: orgid,
                "Authorization": oauth_token,
            }
            data = {
                "text": f"Пользователь {user} оставил комментарий к задаче через Telegram:\n\n{reply_text}"
            }
            logger.info("Session for send comment has been prepared")
            try:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 201:
                        try:
                            result = await response.json()
                            logger.info("201 OK")
                            return result
                        except (aiohttp.ContentTypeError, json.JSONDecodeError) as e:
                            result = {"error": f"Response parsing failed: {str(e)}"}
                            logger.error(result)
                            return result
                    else:
                        try:
                            error_body = await response.text()
                            logger.error("Got error %s from server", error_body)
                            return {
                                "error": f"API request failed (Status {response.status})",
                                "details": error_body,
                            }
                        except Exception as e:
                            result = {
                                "error": f"Failed to read error response: {str(e)}"
                            }
                            logger.error(result)
                            return result
            except aiohttp.ClientError as e:
                result = {"error": f"Network error occurred: {str(e)}"}
                logger.error(result)
                return result

    except Exception as e:
        result = {"error": f"Unexpected error in comment creation: {str(e)}"}
        logger.error(result)
        return result


# Обновление chat_id в YDB
async def update_chatid(driver, telegram: str, new_values: str):
    async with ydb.aio.QuerySessionPool(driver) as pool:
        select = await pool.execute_with_retries(
            f"""
                SELECT * FROM users WHERE telegram = "{telegram}";
                """
        )
        try:
            selected_user = select[0].rows[0]
            await pool.execute_with_retries(
                f"""
                UPDATE users SET {new_values} WHERE telegram = "{telegram}";
            """
            )
            message = f"Привет, {telegram}! Твой chat_id успешно обновлен"
        except IndexError:
            message = f"Пользователь {telegram} не найден в базе данных"
    return message


@user_check()
async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    voice_message = update.message.voice
    voice_object = await context.bot.get_file(voice_message.file_id)
    voice_file = await voice_object.download_as_bytearray()
    byte_stream = io.BytesIO(voice_file)
    byte_stream.seek(0)
    s3.upload_fileobj(
        byte_stream,
        BUCKET_NAME,
        f"{BUCKET_FOLDER}/{voice_message.file_unique_id}.ogg",
    )

    recognition_request = await send_file_to_recognizer(
        RECOGNIZE_TOKEN,
        BUCKET_NAME,
        f"{BUCKET_FOLDER}/{voice_message.file_unique_id}.ogg",
    )
    recognition_response = await get_recognition(
        RECOGNIZE_TOKEN, recognition_request.get("id")
    )
    recognition_result = await parse_recognition_result(recognition_response)
    await update.message.reply_text(recognition_result)


@user_check()
async def art_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_input = " ".join(context.args)
    seed = random.getrandbits(63)
    operation_id = await send_prompt(ART_TOKEN, FOLDER_ID, user_input, seed)
    image = await get_image(ART_TOKEN, operation_id)
    await update.message.reply_photo(image)


@user_check()
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    models = {
                "y": "yandexgpt"
            }
    token = ART_TOKEN.split(" ")[1]
    user_input = " ".join(context.args)
    model_type = update.message.text.split()[0].lstrip('/')
    promt_response = await promt_request(FOLDER_ID, token, models.get(model_type), user_input)
    try:
        await update.message.reply_text(promt_response, parse_mode="Markdown")
    except BadRequest:
        await update.message.reply_text(promt_response, parse_mode="HTML")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user.username
    chat_id = update.message.chat_id
    query = f"tg_chat_id = {chat_id}"
    try:
        message = await update_chatid(driver, user, query)
    except Exception as e:
        message = f"Привет, {user}!\n\nПроизошла ошибка: {str(e)}"
    await update.message.reply_text(message)


# хэндлер для реплаев на ссылку с задачей от бота
async def reply_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    header: str,
    orgid: str,
    oauth_token: str,
) -> None:
    url_regex = r"(https?://[^\s]+)"
    user = update.message.from_user.username
    original_message = update.message.reply_to_message.text
    try:
        url = re.findall(url_regex, original_message)[0]
        parsed_url = urllib.parse.urlparse(url)
        issue_key = str(parsed_url[2]).replace("/", "")
        reply_text = update.message.text
        created_comment = await create_comment(
            issue_key, reply_text, user, header, orgid, oauth_token
        )
        if created_comment.get("error") is None:
            await update.message.reply_text(
                f"Комментарий к задаче {issue_key} отправлен"
            )
            logger.info("Comment created for issue %s by %s", issue_key, user)
        else:
            error = created_comment.get("error", "Unknown error")
            await update.message.reply_text(
                f"Произошло досадное недоразумение. Комментарий не отправлен"
            )
            logger.error("Comment creation failed for %s: %s", issue_key, error)
    except IndexError:
        message = "Не удалось найти ссылку на задачу в ответе на сообщение"
        await update.message.reply_text(message)
        logger.error(message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Команды бота:\n"
        "/start - запуск бота\n"
        "/art - запрос на генерацию картинки. Через пробел от команды пишется запрос\n"
        "/y - запрос на генерацию текста. Через пробел от команды пишется запрос. YandexGPT Pro\n"
    )


def main() -> None:
    application = Application.builder().token(TG_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    application.add_handler(
        MessageHandler(
            filters.REPLY,
            partial(reply_handler, header=HEADER, orgid=ORGID, oauth_token=OAUTH_TOKEN),
        )
    )

    application.add_handler(
        MessageHandler(filters.VOICE & ~filters.COMMAND, voice_handler)
    )
    application.add_handler(CommandHandler("art", art_handler))
    application.add_handler(CommandHandler("y", text_handler))
    application.add_handler(CommandHandler("q", text_handler))
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
