import os
import boto3
import ydb
from dotenv import load_dotenv


load_dotenv(dotenv_path=os.path.join("credentials", ".env"))

S3KEY_ID = os.getenv("S3KEY_ID")
S3KEY = os.getenv("S3KEY")
YDB_ENDPOINT = os.getenv("YDB_ENDPOINT")
YDB_DATABASE = os.getenv("YDB_DATABASE")
SA_KEY_FILE = os.getenv("SA_KEY_FILE")


session = boto3.session.Session()

s3 = session.client(
    service_name="s3",
    endpoint_url="https://storage.yandexcloud.net",
    aws_access_key_id=S3KEY_ID,
    aws_secret_access_key=S3KEY,
)


driver = ydb.Driver(
    endpoint=YDB_ENDPOINT,
    database=YDB_DATABASE,
    credentials=ydb.iam.ServiceAccountCredentials.from_file(SA_KEY_FILE),
)


pool = ydb.QuerySessionPool(driver)
