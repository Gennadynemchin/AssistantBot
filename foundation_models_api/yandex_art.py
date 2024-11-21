import os
import asyncio
import aiohttp
import base64
from io import BytesIO
from dotenv import load_dotenv
from PIL import Image
from tenacity import retry, stop_after_attempt, wait_fixed


load_dotenv()

TOKEN = os.getenv("TOKEN")
FOLDER_ID = os.getenv("FOLDER_ID")


async def send_prompt(
    token: str, folder_id: str, promt: str, seed: str = "1863"
) -> str:
    promt = {
        "modelUri": f"art://{folder_id}/yandex-art/latest",
        "generationOptions": {
            "seed": seed,
            "aspectRatio": {"widthRatio": "2", "heightRatio": "1"},
        },
        "messages": [
            {
                "weight": "1",
                "text": promt,
            }
        ],
    }
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/imageGenerationAsync"
    headers = {"Authorization": token}
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url, headers=headers, json=promt, ssl=False
        ) as response:
            if response.status == 200:
                response_data = await response.json()
                return response_data.get("id")
            else:
                raise RuntimeError(
                    f"Image generation request failed with status: {response.status}"
                )


@retry(stop=stop_after_attempt(10), wait=wait_fixed(5))
async def get_image(token: str, operation_id: str) -> Image.Image:
    url = f"https://llm.api.cloud.yandex.net:443/operations/{operation_id}"
    headers = {"Authorization": token}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, ssl=False) as response:
            if response.status == 200:
                response_data = await response.json()
                base64_image = response_data.get("response", {}).get("image")
                if not base64_image:
                    raise ValueError("No image data in the response.")
                image_bytes = base64.b64decode(base64_image)
                image_stream = BytesIO(image_bytes)
                # image = Image.open(image_stream)
                # image.show()
                return image_stream
            else:
                raise RuntimeError(
                    f"Image retrieval failed with status: {response.status}"
                )
