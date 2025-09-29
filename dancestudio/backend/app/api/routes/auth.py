from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ...core import security
from ...db.session import get_db
from ...db import models
from ...config import get_settings
from .. import deps


router = APIRouter(prefix="/auth", tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    admin = db.query(models.AdminUser).filter_by(login=form_data.username).first()
    if not admin or not security.verify_password(form_data.password, admin.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid credentials")
    settings = get_settings()
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_min)
    token = security.create_access_token({"sub": str(admin.id), "role": admin.role}, expire)
    admin.last_login_at = datetime.utcnow()
    db.commit()
    return TokenResponse(access_token=token, user={"id": admin.id, "login": admin.login, "role": admin.role})


@router.get("/me")
def me(current=Depends(deps.get_current_admin)):
    admin = current
    return {"id": admin.id, "login": admin.login, "role": admin.role}
