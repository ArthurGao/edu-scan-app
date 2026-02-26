import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

import boto3
from botocore.config import Config
from fastapi import UploadFile

from app.config import get_settings

settings = get_settings()


class StorageService:
    """
    Image storage service.

    Uses Cloudflare R2 when configured, falls back to local filesystem.
    """

    def __init__(self):
        self._s3 = None
        self._use_r2 = bool(
            settings.r2_access_key_id and settings.r2_secret_access_key
        )
        if self._use_r2:
            self._s3 = boto3.client(
                "s3",
                endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
                aws_access_key_id=settings.r2_access_key_id,
                aws_secret_access_key=settings.r2_secret_access_key,
                config=Config(signature_version="s3v4"),
                region_name="auto",
            )
        else:
            self._upload_dir = Path("uploads")
            self._upload_dir.mkdir(exist_ok=True)

    async def upload_image(
        self,
        file: UploadFile,
        folder: str = "scans",
    ) -> str:
        file_ext = file.filename.split(".")[-1] if file.filename else "jpg"
        key = f"{folder}/{uuid.uuid4()}.{file_ext}"

        if self._use_r2:
            content = await file.read()
            self._s3.put_object(
                Bucket=settings.r2_bucket_name,
                Key=key,
                Body=content,
                ContentType=file.content_type or "image/jpeg",
            )
            if settings.r2_public_url:
                return f"{settings.r2_public_url.rstrip('/')}/{key}"
            return f"https://{settings.r2_account_id}.r2.cloudflarestorage.com/{settings.r2_bucket_name}/{key}"

        # Local fallback
        folder_path = self._upload_dir / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        file_path = folder_path / key.split("/")[-1]
        with open(file_path, "wb") as buf:
            shutil.copyfileobj(file.file, buf)
        return str(file_path)

    async def delete_image(self, url: str) -> bool:
        try:
            if self._use_r2:
                # Extract key from URL
                key = url.split(f"{settings.r2_bucket_name}/")[-1]
                if settings.r2_public_url:
                    key = url.replace(settings.r2_public_url.rstrip("/") + "/", "")
                self._s3.delete_object(
                    Bucket=settings.r2_bucket_name,
                    Key=key,
                )
                return True

            path = Path(url)
            if path.exists():
                os.remove(path)
                return True
            return False
        except Exception:
            return False
