from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.crud import usuario as crud_usuario
from app.db.session import get_db  # noqa: F401
from app.models.usuario import Usuario

# Dos esquemas para el MISMO header `Authorization: Bearer <token>`; la
# diferencia es solo cómo los ofrece el botón "Authorize" de /docs:
#   - OAuth2PasswordBearer: pedís email+contraseña y Swagger hace el login solo.
#   - HTTPBearer: pegás un token que ya tenías (útil si lo sacaste por curl,
#     o para no re-tipear credenciales cada vez que se recarga /docs).
# Ambos con auto_error=False: si uno solo falla no debe cortar la petición,
# porque puede venir resuelta por el otro. El 401 lo emitimos nosotros abajo.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login", auto_error=False
)
bearer_scheme = HTTPBearer(auto_error=False)

_credenciales_invalidas = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="No se pudo validar las credenciales",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    credenciales: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    token = token or (credenciales.credentials if credenciales else None)
    if token is None:
        raise _credenciales_invalidas
    email = decode_access_token(token)
    if email is None:
        raise _credenciales_invalidas
    usuario = crud_usuario.get_by_email(db, email)
    if usuario is None or not usuario.activo:
        raise _credenciales_invalidas
    return usuario
