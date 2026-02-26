import os
import shutil
import uuid
from typing import Optional
from pathlib import Path

from fastapi import UploadFile

from app.config import get_settings

settings = get_settings()


class StorageService:
    """
    Service for file storage operations.
    
    Supports:
    - AWS S3
    - MinIO (S3-compatible, for local development)
    - Local filesystem (for testing)
    """

    def __init__(self):
        self.upload_dir = Path("uploads")
        self.upload_dir.mkdir(exist_ok=True)
        self._init_client()

    def _init_client(self):
        """Initialize S3 client."""
        # For now, we are using local storage as default for development
        pass

    async def upload_image(
        self,
        file: UploadFile,
        folder: str = "scans",
    ) -> str:
        """
        Upload image to storage.
        
        Args:
            file: Uploaded file
            folder: Storage folder/prefix
            
        Returns:
            Public URL of uploaded image
        """
        # Create folder if it doesn't exist
        folder_path = self.upload_dir / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_extension = file.filename.split(".")[-1] if file.filename else "jpg"
        filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = folder_path / filename
        
        # Save to local filesystem
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Return path (in real S3 this would be a URL)
        return str(file_path)

    async def delete_image(self, url: str) -> bool:
        """Delete image from storage."""
        try:
            path = Path(url)
            if path.exists():
                os.remove(path)
                return True
            return False
        except Exception:
            return False

    def _generate_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
    ) -> str:
        """Generate presigned URL for private objects."""
        # For local storage, just return the path
        return key
