from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud
from app.api.deps import get_db, requiere_admin
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioRead

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.get(
    "/",
    response_model=list[UsuarioRead],
    summary="Listar usuarios (solo admin)",
    description=(
        "Restringido a admin: saber qué cuentas existen y con qué rol es "
        "información de administración, no algo que necesite un contador o "
        "un lector para su trabajo."
    ),
)
def listar_usuarios(
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_admin),
) -> list[Usuario]:
    return crud.usuario.get_multi(db)
