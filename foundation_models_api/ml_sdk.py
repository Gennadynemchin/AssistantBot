import io
import asyncio

from PIL import Image
from random import getrandbits
from yandex_cloud_ml_sdk import AsyncYCloudML
from settings import FOLDER_ID, ART_TOKEN


async def generate_image() -> None:
    sdk = AsyncYCloudML(folder_id=FOLDER_ID, auth=ART_TOKEN.split(" ")[1])
    model = sdk.models.image_generation("yandex-art")
    configured_model = model.configure(
        width_ratio=1, height_ratio=2, seed=getrandbits(63)
    )
    try:
        operation = await configured_model.run_deferred(
            ["a red sheltie", "Miyazaki style"]
        )
        result = await operation
        return result
        # image_stream = io.BytesIO(result.image_bytes)
        # image = Image.open(image_stream)
        # image.show()
    except Exception as e:
        print(e)


async def promt_request(
    folder_id: str,
    token: str,
    model_id: str,
    text: str,
    temperature: float = 0.3,
    role: str = "system",
) -> None:
    sdk = AsyncYCloudML(folder_id=folder_id, auth=token)
    model = sdk.models.completions(model_id)
    model = model.configure(temperature=temperature)
    messages: list[dict[str, str] | str] = [{"role": role, "text": text}]
    result = await model.run(messages)
    messages.append(result[0])
    return result[0].text
