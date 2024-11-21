import aiohttp
import json
from tenacity import retry, stop_after_attempt, wait_fixed


async def send_file_to_recognizer(token: str, bucket: str, file_name: str):
    url = "https://stt.api.cloud.yandex.net/stt/v3/recognizeFileAsync"
    headers = {"Authorization": token}
    data = {
        "uri": f"https://storage.yandexcloud.net/{bucket}/{file_name}",
        "recognitionModel": {
            "model": "general:rc",
            "audioFormat": {
                "containerAudio": {"containerAudioType": "OGG_OPUS"},
            },
            "textNormalization": {
                "textNormalization": "TEXT_NORMALIZATION_ENABLED",
                "profanityFilter": False,
                "literatureText": True,
                "phoneFormattingMode": "PHONE_FORMATTING_MODE_DISABLED",
            },
            "languageRestriction": {
                "languageCode": ["ru-RU"],
            },
            "audioProcessingType": "FULL_DATA",
        },
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise RuntimeError(
                    f"Response status code: {response.status}, {response.text}"
                )


@retry(stop=stop_after_attempt(50), wait=wait_fixed(2))
async def get_recognition(token: str, operationId: str) -> list:
    url = "https://stt.api.cloud.yandex.net/stt/v3/getRecognition"
    headers = {"Authorization": token, "Content-Type": "application/json"}
    params = {"operationId": operationId}
    recognized_content = []
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status != 200:
                raise RuntimeError("No recognized content yet")
            async for json_line in response.content:
                recognized_content.append(json_line.decode("utf-8"))
    return recognized_content


async def parse_recognition_result(json_objects: list) -> str:
    output_normalized_text = ""
    for json_object in json_objects:
        try:
            normalized_text = json.loads(json_object)
            normalized_text = normalized_text["result"]["finalRefinement"][
                "normalizedText"
            ]["alternatives"][0]["text"]
            output_normalized_text += normalized_text
        except (KeyError, IndexError):
            pass
    return output_normalized_text
