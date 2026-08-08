from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.asiento import Asiento, MovimientoContable
from app.models.cuenta import Cuenta
from app.models.usuario import Usuario
from app.schemas.asiento import AsientoCreate


class CuentaInvalidaError(Exception):
    pass


class AsientoYaReversadoError(Exception):
    pass


class AsientoReversadoError(Exception):
    pass


def get(db: Session, asiento_id: int) -> Asiento | None:
    stmt = (
        select(Asiento)
        .where(Asiento.id == asiento_id)
        .options(
            selectinload(Asiento.movimientos),
            selectinload(Asiento.reversiones),
            selectinload(Asiento.usuario),
        )
    )
    return db.scalar(stmt)


def _aplicar_filtros(
    stmt,
    *,
    fecha_desde: date | None,
    fecha_hasta: date | None,
    cuenta_id: int | None,
):
    if fecha_desde is not None:
        stmt = stmt.where(Asiento.fecha >= fecha_desde)
    if fecha_hasta is not None:
        stmt = stmt.where(Asiento.fecha <= fecha_hasta)
    if cuenta_id is not None:
        stmt = stmt.where(Asiento.movimientos.any(MovimientoContable.cuenta_id == cuenta_id))
    return stmt


def get_multi(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    cuenta_id: int | None = None,
) -> list[Asiento]:
    stmt = (
        select(Asiento)
        .options(
            selectinload(Asiento.movimientos),
            selectinload(Asiento.reversiones),
            selectinload(Asiento.usuario),
        )
        .order_by(Asiento.numero.desc())
    )
    stmt = _aplicar_filtros(
        stmt, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, cuenta_id=cuenta_id
    )
    stmt = stmt.offset(skip).limit(limit)
    return list(db.scalars(stmt))


def count(
    db: Session,
    *,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    cuenta_id: int | None = None,
) -> int:
    stmt = select(func.count()).select_from(Asiento)
    stmt = _aplicar_filtros(
        stmt, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, cuenta_id=cuenta_id
    )
    return db.scalar(stmt) or 0


def siguiente_numero(db: Session) -> int:
    # NOTA: bajo escrituras concurrentes esto puede colisionar (el
    # UniqueConstraint de "numero" haría fallar la transacción en ese caso);
    # para alta concurrencia conviene una secuencia de BD o SELECT ... FOR UPDATE.
    ultimo = db.scalar(select(func.max(Asiento.numero)))
    return (ultimo or 0) + 1


def _validar_cuentas(db: Session, cuenta_ids: set[int]) -> None:
    cuentas = {c.id: c for c in db.scalars(select(Cuenta).where(Cuenta.id.in_(cuenta_ids)))}
    for cuenta_id in cuenta_ids:
        cuenta = cuentas.get(cuenta_id)
        if cuenta is None:
            raise CuentaInvalidaError(f"La cuenta con id={cuenta_id} no existe")
        if not cuenta.acepta_movimiento:
            raise CuentaInvalidaError(
                f"La cuenta '{cuenta.codigo}' es sumaria y no acepta movimientos directos"
            )
        if not cuenta.activa:
            raise CuentaInvalidaError(f"La cuenta '{cuenta.codigo}' está inactiva")


def create(db: Session, *, obj_in: AsientoCreate, usuario: Usuario | None = None) -> Asiento:
    _validar_cuentas(db, {m.cuenta_id for m in obj_in.movimientos})

    db_obj = Asiento(
        numero=siguiente_numero(db),
        fecha=obj_in.fecha,
        descripcion=obj_in.descripcion,
        usuario_id=usuario.id if usuario else None,
        movimientos=[
            MovimientoContable(
                cuenta_id=m.cuenta_id,
                debito=m.debito,
                credito=m.credito,
                descripcion=m.descripcion,
            )
            for m in obj_in.movimientos
        ],
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def reversar(
    db: Session,
    *,
    original: Asiento,
    fecha: date | None = None,
    usuario: Usuario | None = None,
) -> Asiento:
    if original.reversiones:
        reversion_previa = original.reversiones[0]
        raise AsientoYaReversadoError(
            f"El asiento #{original.numero} ya fue reversado por el asiento "
            f"#{reversion_previa.numero}"
        )

    _validar_cuentas(db, {m.cuenta_id for m in original.movimientos})

    db_obj = Asiento(
        numero=siguiente_numero(db),
        fecha=fecha or date.today(),
        descripcion=f"Reversión del asiento #{original.numero}: {original.descripcion}",
        reversa_de_id=original.id,
        usuario_id=usuario.id if usuario else None,
        movimientos=[
            MovimientoContable(
                cuenta_id=m.cuenta_id,
                # Se invierten débito y crédito para anular el efecto original.
                debito=m.credito,
                credito=m.debito,
                descripcion=m.descripcion,
            )
            for m in original.movimientos
        ],
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def remove(db: Session, *, db_obj: Asiento) -> None:
    if db_obj.reversiones:
        raise AsientoReversadoError(
            f"El asiento #{db_obj.numero} ya fue reversado y no puede eliminarse"
        )
    db.delete(db_obj)
    db.commit()
