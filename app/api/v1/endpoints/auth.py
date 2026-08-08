from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import crud
from app.api.deps import get_current_user, get_db
from app.core.security import create_access_token
from app.models.usuario import Usuario
from app.schemas.usuario import Token, UsuarioCreate, UsuarioRead

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/registrar", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED)
def registrar_usuario(usuario_in: UsuarioCreate, db: Session = Depends(get_db)) -> Usuario:
    try:
        return crud.usuario.create(db, obj_in=usuario_in)
    except crud.usuario.EmailYaRegistradoError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/login", response_model=Token)
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
