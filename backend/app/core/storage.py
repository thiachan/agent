"""
storage.py — Unified file storage abstraction

STORAGE_BACKEND=local  (EC2 default) → local filesystem — no code changes needed
STORAGE_BACKEND=s3     (ECS prod)    → S3; presigned URLs for downloads

Usage:
    from app.core.storage import storage
    path = await storage.save(file_bytes, "uploads/foo.pdf")
    url  = await storage.url(path)
    data = await storage.read(path)
    await storage.delete(path)
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

STORAGE_BACKEND     = os.getenv("STORAGE_BACKEND", "local")
S3_UPLOADS_BUCKET   = os.getenv("S3_UPLOADS_BUCKET", "")
S3_GENERATED_BUCKET = os.getenv("S3_GENERATED_BUCKET", "")
AWS_REGION          = os.getenv("AWS_REGION", "us-east-1")
PRESIGNED_URL_EXPIRY = int(os.getenv("PRESIGNED_URL_EXPIRY", "3600"))


class LocalStorage:
    """Stores files on the local filesystem — identical to current EC2 behaviour."""

    async def save(self, data: bytes, relative_path: str) -> str:
        abs_path = Path(relative_path)
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_bytes(data)
        return relative_path

    async def save_from_path(self, src_path: str, dest_relative: str) -> str:
        import shutil
        dest = Path(dest_relative)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dest)
        return dest_relative

    async def url(self, relative_path: str, expiry: int = PRESIGNED_URL_EXPIRY) -> str:
        return relative_path

    async def read(self, relative_path: str) -> bytes:
        return Path(relative_path).read_bytes()

    async def read_to_tempfile(self, relative_path: str) -> str:
        return relative_path   # already a real path on local

    async def delete(self, relative_path: str) -> None:
        p = Path(relative_path)
        if p.exists():
            p.unlink()

    async def exists(self, relative_path: str) -> bool:
        return Path(relative_path).exists()


class S3Storage:
    """Stores files in S3. Used by ECS tasks."""

    def __init__(self):
        import boto3
        self._s3 = boto3.client("s3", region_name=AWS_REGION)

    def _bucket_and_key(self, relative_path: str):
        if relative_path.lstrip("./").startswith("uploads/"):
            bucket = S3_UPLOADS_BUCKET
        else:
            bucket = S3_GENERATED_BUCKET
        key = relative_path.lstrip("./")
        return bucket, key

    async def save(self, data: bytes, relative_path: str) -> str:
        bucket, key = self._bucket_and_key(relative_path)
        self._s3.put_object(Bucket=bucket, Key=key, Body=data)
        return relative_path

    async def save_from_path(self, src_path: str, dest_relative: str) -> str:
        bucket, key = self._bucket_and_key(dest_relative)
        self._s3.upload_file(src_path, bucket, key)
        return dest_relative

    async def url(self, relative_path: str, expiry: int = PRESIGNED_URL_EXPIRY) -> str:
        bucket, key = self._bucket_and_key(relative_path)
        return self._s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expiry,
        )

    async def read(self, relative_path: str) -> bytes:
        bucket, key = self._bucket_and_key(relative_path)
        return self._s3.get_object(Bucket=bucket, Key=key)["Body"].read()

    async def read_to_tempfile(self, relative_path: str) -> str:
        """Download to a temp file — needed for whisper/moviepy which require a real path."""
        import tempfile
        data = await self.read(relative_path)
        suffix = Path(relative_path).suffix
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(data)
        tmp.flush()
        tmp.close()
        return tmp.name

    async def delete(self, relative_path: str) -> None:
        bucket, key = self._bucket_and_key(relative_path)
        self._s3.delete_object(Bucket=bucket, Key=key)

    async def exists(self, relative_path: str) -> bool:
        import botocore
        bucket, key = self._bucket_and_key(relative_path)
        try:
            self._s3.head_object(Bucket=bucket, Key=key)
            return True
        except botocore.exceptions.ClientError:
            return False


def _build_storage():
    if STORAGE_BACKEND == "s3":
        if not S3_UPLOADS_BUCKET or not S3_GENERATED_BUCKET:
            raise EnvironmentError(
                "STORAGE_BACKEND=s3 requires S3_UPLOADS_BUCKET and S3_GENERATED_BUCKET env vars."
            )
        logger.info(f"[storage] S3 backend (uploads={S3_UPLOADS_BUCKET}, generated={S3_GENERATED_BUCKET})")
        return S3Storage()
    logger.info("[storage] local filesystem backend")
    return LocalStorage()


storage: LocalStorage | S3Storage = _build_storage()
