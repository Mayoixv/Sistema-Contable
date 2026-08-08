from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UsuarioCreate(BaseModel):
    email: EmailStr
    nombre: str = Field(..., min_length=1, max_length=150)
    password: str = Field(..., min_length=8, max_length=72)


class UsuarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    nombre: str
    activo: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
