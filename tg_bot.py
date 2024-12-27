import os
import io
import re
import aiohttp
import urllib.parse
import random
import ydb
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
from botlogger import logger
from settings import s3, driver


RECOGNIZE_TOKEN = os.getenv("RECOGNIZE_TOKEN")
ART_TOKEN = os.getenv("ART_TOKEN")
BUCKET_NAME = os.getenv("BUCKET_NAME")
BUCKET_FOLDER = os.getenv("BUCKET_FOLDER")
ORGID = os.getenv("ORGID")
OAUTH_TOKEN = os.getenv("OAUTH_TOKEN")
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


# создает коммент в задаче по реплаю Telegram-пользователя
async def create_comment(issue_key: str, reply_text: str, user: str):
    async with aiohttp.ClientSession() as session:
        url = f"https://api.tracker.yandex.net/v2/issues/{issue_key}/comments"
        headers = {
            "X-Cloud-Org-Id": ORGID,
            "Authorization": OAUTH_TOKEN,
        }
        data = {
            "text": f"Пользователь {user} оставил комментарий к задаче через Telegram:\n\n{reply_text}"
        }
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                return result
            else:
                return {"error": f"Request failed with status {response.status}"}


# Обновление chat_id в YDB
async def update_chatid(driver, telegram: str, new_values: str):
    async with ydb.aio.QuerySessionPool(driver) as pool:
        await pool.execute_with_retries(
            f"""
            UPDATE users SET {new_values} WHERE telegram = "{telegram}";
            """
        )
        message = "Hello! Your chat_id has been saved to the database"
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
    token = ART_TOKEN.split(" ")[1]
    user_input = " ".join(context.args)
    promt_response = await promt_request(FOLDER_ID, token, "yandexgpt", user_input)
    try:
        await update.message.reply_text(promt_response, parse_mode="Markdown")
    except BadRequest:
        await update.message.reply_text(promt_response, parse_mode="HTML")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user.username
    chat_id = update.message.chat_id
    query = f"tg_chat_id = {chat_id}"
    message = await update_chatid(driver, user, query)
    await update.message.reply_text(message)


# хэндлер для реплаев на ссылку с задачей от бота
async def reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url_regex = r"(https?://[^\s]+)"
    user = update.message.from_user.username
    original_message = update.message.reply_to_message.text
    url = re.findall(url_regex, original_message)[0]
    parsed_url = urllib.parse.urlparse(url)
    issue_key = str(parsed_url[2]).replace("/", "")
    reply_text = update.message.text
    await create_comment(issue_key, reply_text, user)
    await update.message.reply_text(f"Комментарий к задаче {issue_key} отправлен")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Команды бота:\n"
        "/start - зпуск бота\n"
        "/art - запрос на генерацию картинки. Через пробел от команды пишется запрос\n"
        "/text - запрос на генерацию текста. Через пробел от команды пишется запрос\n"
    )


def main() -> None:
    application = Application.builder().token(TG_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(
        MessageHandler(filters.VOICE & ~filters.COMMAND, voice_handler)
    )
    application.add_handler(MessageHandler(filters.REPLY, reply_handler))
    application.add_handler(CommandHandler("art", art_handler))
    application.add_handler(CommandHandler("text", text_handler))
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
