from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import crud
from app.api.deps import get_db, requiere_admin
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioRead, UsuarioUpdate

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


def _obtener_o_404(db: Session, usuario_id: int) -> Usuario:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return usuario


# Invariante: el sistema nunca se queda sin admin activo.
#
# Lo garantiza el bloqueo de auto-modificación de más abajo, sin necesidad de
# contar admins: `requiere_admin` asegura que quien ejecuta la acción es un
# admin activo, y un admin no puede degradarse, desactivarse ni eliminarse a
# sí mismo. Como el objetivo siempre es otro usuario, después de cualquier
# operación queda en pie al menos quien la ejecutó.
#
# Importa porque no habría cómo recuperarse: sin admins nadie puede crear
# usuarios, y el registro público solo se reabre si no queda NINGÚN usuario.


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


@router.patch(
    "/{usuario_id}",
    response_model=UsuarioRead,
    summary="Cambiar rol o activar/desactivar un usuario (solo admin)",
)
def actualizar_usuario(
    usuario_id: int,
    datos: UsuarioUpdate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requiere_admin),
) -> Usuario:
    objetivo = _obtener_o_404(db, usuario_id)

    # Cambiarse el rol a uno mismo es la forma más fácil de perder el acceso
    # sin querer, y no hay forma de recuperarlo desde la propia app.
    if objetivo.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No podés cambiar tu propio rol ni desactivarte a vos mismo",
        )

    return crud.usuario.update(db, db_obj=objetivo, obj_in=datos)


@router.delete(
    "/{usuario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un usuario (solo admin)",
    description=(
        "Solo se pueden eliminar usuarios sin historial contable. Si cargó "
        "asientos o hizo cierres, el borrado se rechaza para no perder la "
        "trazabilidad: en ese caso, desactivalo."
    ),
)
def eliminar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requiere_admin),
) -> None:
    objetivo = _obtener_o_404(db, usuario_id)

    if objetivo.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No podés eliminar tu propio usuario",
        )

    try:
        crud.usuario.remove(db, db_obj=objetivo)
    except IntegrityError as exc:
        # El FK de asientos/cierres es ON DELETE RESTRICT.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"El usuario '{objetivo.email}' tiene asientos o cierres registrados a su "
                "nombre y no puede eliminarse sin perder la trazabilidad. Desactivalo en "
                "su lugar."
            ),
        ) from exc
