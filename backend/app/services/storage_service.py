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
        """Delete an image from R2 or local filesystem.

        Extracts the object key from the stored URL and issues a delete.
        """
        try:
            if self._use_r2:
                key = self._extract_r2_key(url)
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

    @staticmethod
    def _extract_r2_key(url: str) -> str:
        """Extract the R2 object key from a stored URL.

        Upload produces two URL formats:
          - Public:  {r2_public_url}/scans/uuid.jpg
          - Direct:  https://{account}.r2.cloudflarestorage.com/{bucket}/scans/uuid.jpg
        """
        public = settings.r2_public_url
        if public and url.startswith(public.rstrip("/")):
            return url[len(public.rstrip("/")) + 1:]

        # Direct URL: everything after "{bucket}/"
        marker = f"{settings.r2_bucket_name}/"
        idx = url.find(marker)
        if idx != -1:
            return url[idx + len(marker):]

        # Fallback: treat whole URL as key
        return url
