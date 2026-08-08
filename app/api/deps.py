from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.crud import usuario as crud_usuario
from app.db.session import get_db  # noqa: F401
from app.models.usuario import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

_credenciales_invalidas = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="No se pudo validar las credenciales",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Usuario:
    email = decode_access_token(token)
    if email is None:
        raise _credenciales_invalidas
    usuario = crud_usuario.get_by_email(db, email)
    if usuario is None or not usuario.activo:
        raise _credenciales_invalidas
    return usuario
