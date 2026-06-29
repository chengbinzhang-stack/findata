import boto3
from botocore.exceptions import ClientError
import os
from pathlib import Path
from typing import Optional


def get_s3_client():
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_REGION", "ap-south-1")

    if access_key and secret_key:
        return boto3.client(
            "s3",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
    return None


def upload_to_s3(local_path: Path, s3_bucket: str, s3_key: str) -> tuple[bool, Optional[str]]:
    s3_client = get_s3_client()
    if not s3_client:
        return False, "S3 client not configured (missing AWS credentials)"

    try:
        s3_client.upload_file(str(local_path), s3_bucket, s3_key)
        s3_url = f"s3://{s3_bucket}/{s3_key}"
        return True, s3_url
    except ClientError as e:
        return False, str(e)


def upload_fileobj(file_obj, s3_bucket: str, s3_key: str, content_type: str = None) -> tuple[bool, Optional[str]]:
    s3_client = get_s3_client()
    if not s3_client:
        return False, "S3 client not configured"

    try:
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type
        s3_client.upload_fileobj(file_obj, s3_bucket, s3_key, ExtraArgs=extra_args)
        s3_url = f"s3://{s3_bucket}/{s3_key}"
        return True, s3_url
    except ClientError as e:
        return False, str(e)