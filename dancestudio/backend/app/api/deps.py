from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from ..config import get_settings
from ..db.session import get_db
from ..db.models import AdminUser
from ..core.security import ALGORITHM


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_admin(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> AdminUser:
    settings = get_settings()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise credentials_exception from exc
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    user = db.get(AdminUser, int(user_id))
    if user is None:
        raise credentials_exception
    return user


def require_roles(*roles: str):
    def dependency(user: Annotated[AdminUser, Depends(get_current_admin)]) -> AdminUser:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return dependency
