import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.storage import StorageError, build_path, content_type_for, put_object, validate_upload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/uploads")


@router.post("/id-proof")
async def upload_id_proof(file: UploadFile = File(...), _: AsyncSession = Depends(get_db)):
    """Public endpoint used during registration.

    Returns a stable path that must be embedded in the registration payload so the file
    stays orphaned unless the registration succeeds.
    """
    data = await file.read()
    try:
        validate_upload(file.filename or "", len(data), "id_proof")
        path = build_path("id-proofs", file.filename or "id.bin")
        ctype = file.content_type or content_type_for(file.filename or "")
        result = put_object(path, data, ctype)
    except StorageError as exc:
        logger.warning("id-proof upload failed: %s", exc)
        raise HTTPException(status_code=400, detail={"code": "UPLOAD_FAILED", "message": str(exc)}) from exc
    return {"success": True, "data": {"path": result["path"], "filename": file.filename, "content_type": ctype, "size": result.get("size", len(data))}}
