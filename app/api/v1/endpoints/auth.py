from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import crud
from app.api.deps import get_current_user, get_current_user_optional, get_db
from app.core.security import create_access_token
from app.models.usuario import RolUsuario, Usuario
from app.schemas.usuario import Token, UsuarioCreate, UsuarioRead

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post(
    "/registrar",
    response_model=UsuarioRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear usuario (el primero es admin; después solo un admin puede)",
    description=(
        "Mientras no exista ningún usuario, este endpoint es público y crea "
        "el **admin** inicial. A partir de ahí exige un admin autenticado, "
        "que puede elegir el `rol` del nuevo usuario (por defecto `contador`)."
    ),
)
def registrar_usuario(
    usuario_in: UsuarioCreate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario | None = Depends(get_current_user_optional),
) -> Usuario:
    # Bootstrap: sin usuarios en el sistema, cualquiera puede crear el
    # primero (y queda como admin). Después, alta solo por un admin.
    es_bootstrap = crud.usuario.sistema_sin_usuarios(db)
    if not es_bootstrap:
        if usuario_actual is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Se requiere un admin autenticado para crear usuarios",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if usuario_actual.rol != RolUsuario.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo un admin puede crear usuarios",
            )

    # En el bootstrap se ignora el rol pedido: si el primer usuario pudiera
    # crearse como 'lector', el sistema quedaría sin ningún admin y sin
    # forma de crear uno.
    rol = RolUsuario.ADMIN if es_bootstrap else usuario_in.rol
    try:
        return crud.usuario.create(db, obj_in=usuario_in, rol=rol)
    except crud.usuario.EmailYaRegistradoError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/login",
    response_model=Token,
    summary="Iniciar sesión (en 'username' va el EMAIL)",
    description=(
        "El campo se llama `username` porque lo exige el estándar OAuth2, "
        "pero hay que enviar el **email** con el que se registró el usuario "
        "(no el nombre). No distingue mayúsculas de minúsculas."
    ),
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
) -> dict:
    # OAuth2PasswordRequestForm usa "username": ahí va el email.
    usuario = crud.usuario.authenticate(
        db, email=form_data.username, password=form_data.password
    )
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": create_access_token(subject=usuario.email)}


@router.get("/me", response_model=UsuarioRead)
def usuario_actual(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    return usuario
