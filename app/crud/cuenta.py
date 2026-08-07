from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asiento import MovimientoContable
from app.models.cuenta import Cuenta
from app.schemas.cuenta import CuentaCreate, CuentaUpdate


class CuentaNoEncontradaError(Exception):
    pass


class CuentaConHijasError(Exception):
    pass


class CuentaConMovimientosError(Exception):
    pass


def get(db: Session, cuenta_id: int) -> Cuenta | None:
    return db.get(Cuenta, cuenta_id)


def get_by_codigo(db: Session, codigo: str) -> Cuenta | None:
    return db.scalar(select(Cuenta).where(Cuenta.codigo == codigo))


def get_multi(db: Session, *, skip: int = 0, limit: int = 100) -> list[Cuenta]:
    stmt = select(Cuenta).order_by(Cuenta.codigo).offset(skip).limit(limit)
    return list(db.scalars(stmt))


def get_tree(db: Session) -> list[Cuenta]:
    """Cuentas raíz (sin padre); las hijas se cargan vía la relación ORM.

    Para un plan de cuentas muy grande conviene reemplazar esto por una
    consulta recursiva (CTE) en lugar de lazy-loading nodo por nodo.
    """
    stmt = select(Cuenta).where(Cuenta.padre_id.is_(None)).order_by(Cuenta.codigo)
    return list(db.scalars(stmt))


def create(db: Session, *, obj_in: CuentaCreate) -> Cuenta:
    padre: Cuenta | None = None
    nivel = 1
    if obj_in.padre_id is not None:
        padre = db.get(Cuenta, obj_in.padre_id)
        if padre is None:
            raise CuentaNoEncontradaError(
                f"La cuenta padre con id={obj_in.padre_id} no existe"
            )
        nivel = padre.nivel + 1

    db_obj = Cuenta(
        codigo=obj_in.codigo,
        nombre=obj_in.nombre,
        tipo=obj_in.tipo,
        naturaleza=obj_in.naturaleza,
        nivel=nivel,
        padre_id=obj_in.padre_id,
        acepta_movimiento=obj_in.acepta_movimiento,
        activa=obj_in.activa,
        descripcion=obj_in.descripcion,
    )
    db.add(db_obj)

    if padre is not None and padre.acepta_movimiento:
        # Una cuenta que gana una hija pasa a ser "sumaria": deja de aceptar
        # movimientos directos de asientos contables.
        padre.acepta_movimiento = False

    db.commit()
    db.refresh(db_obj)
    return db_obj


def update(db: Session, *, db_obj: Cuenta, obj_in: CuentaUpdate) -> Cuenta:
    datos = obj_in.model_dump(exclude_unset=True)
    for campo, valor in datos.items():
        setattr(db_obj, campo, valor)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def remove(db: Session, *, db_obj: Cuenta) -> None:
    # Se valida explícitamente en lugar de confiar solo en el FK
    # ON DELETE RESTRICT: algunos motores (ej. SQLite sin PRAGMA
    # foreign_keys) no lo hacen cumplir, y el mensaje de error propio
    # es más claro que un IntegrityError genérico.
    if db_obj.hijas:
        raise CuentaConHijasError(
            f"La cuenta '{db_obj.codigo}' tiene cuentas hijas y no puede eliminarse"
        )
    tiene_movimientos = db.scalar(
        select(MovimientoContable.id)
        .where(MovimientoContable.cuenta_id == db_obj.id)
        .limit(1)
    )
    if tiene_movimientos is not None:
        raise CuentaConMovimientosError(
            f"La cuenta '{db_obj.codigo}' tiene movimientos contables y no puede eliminarse"
        )
    db.delete(db_obj)
    db.commit()
