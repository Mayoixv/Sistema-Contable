from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioCreate


class EmailYaRegistradoError(Exception):
    pass


def get_by_email(db: Session, email: str) -> Usuario | None:
    return db.scalar(select(Usuario).where(Usuario.email == email))


def create(db: Session, *, obj_in: UsuarioCreate) -> Usuario:
    if get_by_email(db, obj_in.email) is not None:
        raise EmailYaRegistradoError(f"Ya existe un usuario con el email '{obj_in.email}'")

    db_obj = Usuario(
        email=obj_in.email,
        nombre=obj_in.nombre,
        hashed_password=hash_password(obj_in.password),
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def authenticate(db: Session, *, email: str, password: str) -> Usuario | None:
    usuario = get_by_email(db, email)
    if usuario is None or not usuario.activo:
        return None
    if not verify_password(password, usuario.hashed_password):
        return None
    return usuario
