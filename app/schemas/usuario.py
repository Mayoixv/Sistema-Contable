from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.usuario import RolUsuario


class UsuarioCreate(BaseModel):
    email: EmailStr
    nombre: str = Field(..., min_length=1, max_length=150)
    password: str = Field(..., min_length=8, max_length=72)
    rol: RolUsuario | None = Field(
        default=None,
        description=(
            "Solo lo puede fijar un admin. Si se omite: el primer usuario del "
            "sistema es 'admin', el resto 'contador'."
        ),
    )


class UsuarioUpdate(BaseModel):
    rol: RolUsuario | None = None
    activo: bool | None = None


class UsuarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    nombre: str
    rol: RolUsuario
    activo: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
