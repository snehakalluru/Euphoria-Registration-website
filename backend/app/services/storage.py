"""Emergent Object Storage wrapper for the Euphoria platform."""
import logging
import os
import uuid
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
APP_NAME = os.environ.get("APP_NAME", "euphoria-hackathon")

MIME_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "gif": "image/gif",
    "pdf": "application/pdf",
    "svg": "image/svg+xml",
}
ALLOWED_IMAGE_EXTS = {"png", "jpg", "jpeg", "webp", "svg"}
ALLOWED_PROOF_EXTS = {"png", "jpg", "jpeg", "webp", "pdf"}
MAX_LOGO_BYTES = 5 * 1024 * 1024
MAX_PROOF_BYTES = 5 * 1024 * 1024

_storage_key: str | None = None


class StorageError(Exception):
    pass


def _emergent_key() -> str:
    key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if not key:
        raise StorageError("EMERGENT_LLM_KEY is not configured")
    return key


def init_storage() -> str:
    global _storage_key
    if _storage_key:
        return _storage_key
    try:
        resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": _emergent_key()}, timeout=30)
        resp.raise_for_status()
        _storage_key = resp.json()["storage_key"]
        logger.info("Emergent object storage initialised")
        return _storage_key
    except Exception as exc:
        logger.warning("Storage init failed: %s", exc)
        raise StorageError(str(exc)) from exc


def _ext(filename: str, fallback: str = "bin") -> str:
    name = Path(filename or "").suffix.lower().lstrip(".")
    return name or fallback


def content_type_for(filename: str, fallback: str = "application/octet-stream") -> str:
    return MIME_TYPES.get(_ext(filename), fallback)


def build_path(kind: str, filename: str) -> str:
    return f"{APP_NAME}/{kind}/{uuid.uuid4()}.{_ext(filename)}"


def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data,
        timeout=120,
    )
    if resp.status_code >= 400:
        raise StorageError(f"Upload failed ({resp.status_code}): {resp.text[:200]}")
    return resp.json()


def get_object(path: str) -> tuple[bytes, str]:
    key = init_storage()
    resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    if resp.status_code >= 400:
        raise StorageError(f"Download failed ({resp.status_code})")
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


def validate_upload(filename: str, size: int, kind: str) -> None:
    ext = _ext(filename)
    if kind == "logo":
        if ext not in ALLOWED_IMAGE_EXTS:
            raise StorageError("Only PNG, JPG, WEBP or SVG logos are supported.")
        if size > MAX_LOGO_BYTES:
            raise StorageError("Logo file must be under 5 MB.")
    elif kind == "id_proof":
        if ext not in ALLOWED_PROOF_EXTS:
            raise StorageError("ID proof must be PNG, JPG, WEBP or PDF.")
        if size > MAX_PROOF_BYTES:
            raise StorageError("ID proof file must be under 5 MB.")
    else:
        raise StorageError("Unknown upload kind.")
