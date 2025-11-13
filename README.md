# AssistantBot

## This Telegram bot integrates with Yandex services (Tracker, Object Storage, YandexGPT, Yandex Art, and YDB) to provide the following functionality:
- Voice Message Recognition: Converts voice messages to text using Yandex's STT (Speech-to-Text) service.
- AI Image Generation: Generates images from text prompts via Yandex Art.
- Text Generation: Produces text responses using YandexGPT.
- Issue Tracker Integration: Allows users to post comments to Yandex Tracker issues directly from Telegram replies.
- User Management: Links Telegram users to YDB for chat ID tracking.

## Prerequisites
### Environment Variables
Configure these variables in your environment (use sample.env then rename it to .env):
- RECOGNIZE_TOKEN: Token for Yandex SpeechKit (STT).
- ART_TOKEN: Token for Yandex Art image generation.
- BUCKET_NAME: Yandex Object Storage bucket name.
- BUCKET_FOLDER: Folder path within the bucket for voice files.
- ORGID, OAUTH_TOKEN, HEADER: Yandex Tracker API credentials.
- TG_TOKEN: Telegram Bot API token.
- FOLDER_ID: Yandex Cloud folder ID.
- INCLUDED_TG_LOGINS: Comma-separated list of allowed Telegram usernames.
- YDB_ENDPOINT=grpcs://ydb.serverless.yandexcloud.net:2135
- YDB_DATABASE=/ru-central1/b1g3vadgq2**********/etncqob93i********** find it in your YDB settings
- SA_KEY_FILE=credentials/authorized_key.json path to authorized key which has been released for service account
- S3KEY_ID=id of S3 key
- S3KEY=S3 key as a string

### Dependencies
- Python 3.12
- requirements.txt:
```
aiohttp==3.10.10
boto3==1.35.57
pillow==11.0.0
python-dotenv==1.0.1
python-telegram-bot==21.7
requests==2.32.3
tenacity==9.0.0
urllib3==2.2.3
ydb[yc]==3.18.8
yandex-cloud-ml-sdk==0.2.0
```

### Functionality Details
1. User Authentication
- Decorator @user_check(): Restricts command access to users in INCLUDED_TG_LOGINS.
- Example: Unauthorized users receive "You are not allowed to use this command."
2. Voice Message Handling
- Command: Automatically triggered by voice messages.
- Flow:
  - Uploads voice file to Yandex Object Storage.
  - Submits the file to Yandex SpeechKit for recognition.
  - Replies with the transcribed text.
1. Image Generation (/art)
- Usage: /art <prompt>
- Flow:
  - Generates an image using Yandex Art.
  - Sends the resulting image to the user.
1. Text Generation (/text)
- Usage: /text <prompt>
- Flow:
  - Submits the prompt to YandexGPT.
  - Replies with the generated text (supports Markdown/HTML).
1. Tracker Comment Integration
- Trigger: Replying to a message containing a Yandex Tracker issue URL.
- Flow:
  - Extracts the issue key from the URL.
  - Posts the reply text as a comment to the issue via Yandex Tracker API.
1. User Setup (/start)
- Usage: /start
- Links the user's Telegram chat_id to their username in YDB.



### Security
- Access Control: Restricted via INCLUDED_TG_LOGINS.
- Data Storage: Voice files are stored in a private Yandex Object Storage bucket.

### Example Usage
- Generate an Image:
  - /art A sunset over mountains
  - Bot replies with an AI-generated image.
- Post a Tracker Comment:
  - Reply to a message containing https://tracker.yandex.ru/MYPROJECT-123 with "Fix this ASAP".
  - Bot posts the comment to issue MYPROJECT-123.
- Transcribe Voice Message:
  - Send a voice note. Bot replies with the transcribed text.

### Setup Instructions
- Install dependencies:
`pip install -r requirements.txt`
- Configure environment variables (e.g., via .env file).
- Deploy YDB table users with fields telegram (string) and tg_chat_id (integer) for example in Yandex Cloud.
- Run the bot:
`python tg_bot.py`

### Run with Docker
.dockerignore:
```
.env
venv
authorized_key.json
```
`docker build -t <IMAGE NAME> .`

`docker run -d --name assistant-bot --env-file .env -v ./authorized_key.json:/app/credentials/authorized_key.json --restart always assistant_bot:latest`