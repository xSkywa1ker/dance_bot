from fastapi import APIRouter, Depends
from ...api import deps
from ...db import models
from ...services import google_sheets

router = APIRouter(tags=["misc"])


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.post("/export/google-sheets")
def export_google_sheets(
    payload: dict,
    _: models.AdminUser = Depends(deps.require_roles("admin", "manager")),
):
    result = google_sheets.export_to_sheets(payload)
    return {"message": result}
