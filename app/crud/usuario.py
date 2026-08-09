from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.usuario import RolUsuario, Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioUpdate


class EmailYaRegistradoError(Exception):
    pass


def _normalizar_email(email: str) -> str:
    # Los emails se guardan y se buscan siempre en minúsculas: si no,
    # registrarse como "Juan@x.com" e intentar entrar con "juan@x.com"
    # da 401, que es un fallo muy confuso para el usuario.
    return email.strip().lower()


def get_by_email(db: Session, email: str) -> Usuario | None:
    return db.scalar(select(Usuario).where(Usuario.email == _normalizar_email(email)))


def get_multi(db: Session) -> list[Usuario]:
    return list(db.scalars(select(Usuario).order_by(Usuario.email)))


def contar(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Usuario)) or 0


def sistema_sin_usuarios(db: Session) -> bool:
    """True mientras no exista ningún usuario.

    Es la condición de arranque del sistema: sin esto no habría forma de
    crear el primer admin, porque crear usuarios ya requiere ser admin.
    """
    return contar(db) == 0


def create(db: Session, *, obj_in: UsuarioCreate, rol: RolUsuario | None = None) -> Usuario:
    if get_by_email(db, obj_in.email) is not None:
        raise EmailYaRegistradoError(f"Ya existe un usuario con el email '{obj_in.email}'")

    # El primer usuario del sistema es admin sí o sí: si fuera contador,
    # nadie podría dar de alta a nadie más.
    if rol is None:
        rol = RolUsuario.ADMIN if sistema_sin_usuarios(db) else RolUsuario.CONTADOR

    db_obj = Usuario(
        email=_normalizar_email(obj_in.email),
        nombre=obj_in.nombre,
        hashed_password=hash_password(obj_in.password),
        rol=rol,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update(db: Session, *, db_obj: Usuario, obj_in: UsuarioUpdate) -> Usuario:
    for campo, valor in obj_in.model_dump(exclude_unset=True).items():
        setattr(db_obj, campo, valor)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def remove(db: Session, *, db_obj: Usuario) -> None:
    db.delete(db_obj)
    db.commit()


def authenticate(db: Session, *, email: str, password: str) -> Usuario | None:
    usuario = get_by_email(db, email)
    if usuario is None or not usuario.activo:
        return None
    if not verify_password(password, usuario.hashed_password):
        return None
    return usuario
