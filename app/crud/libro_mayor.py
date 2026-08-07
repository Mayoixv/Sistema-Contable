from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.agregados import signo_naturaleza
from app.models.asiento import Asiento, MovimientoContable
from app.models.cuenta import Cuenta


def _saldo_inicial(db: Session, cuenta: Cuenta, fecha_desde: date | None) -> Decimal:
    if fecha_desde is None:
        return Decimal("0")

    signo = signo_naturaleza(cuenta.naturaleza)
    stmt = (
        select(MovimientoContable.debito, MovimientoContable.credito)
        .join(Asiento, Asiento.id == MovimientoContable.asiento_id)
        .where(MovimientoContable.cuenta_id == cuenta.id, Asiento.fecha < fecha_desde)
    )
    saldo = Decimal("0")
    for debito, credito in db.execute(stmt):
        saldo += signo * (debito - credito)
    return saldo


def get_libro_mayor(
    db: Session,
    *,
    cuenta: Cuenta,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
) -> dict:
    signo = signo_naturaleza(cuenta.naturaleza)
    saldo_inicial = _saldo_inicial(db, cuenta, fecha_desde)

    stmt = (
        select(MovimientoContable, Asiento)
        .join(Asiento, Asiento.id == MovimientoContable.asiento_id)
        .where(MovimientoContable.cuenta_id == cuenta.id)
    )
    if fecha_desde is not None:
        stmt = stmt.where(Asiento.fecha >= fecha_desde)
    if fecha_hasta is not None:
        stmt = stmt.where(Asiento.fecha <= fecha_hasta)
    stmt = stmt.order_by(Asiento.fecha, Asiento.numero, MovimientoContable.id)

    saldo = saldo_inicial
    total_debitos = Decimal("0")
    total_creditos = Decimal("0")
    lineas = []
    for movimiento, asiento in db.execute(stmt):
        saldo += signo * (movimiento.debito - movimiento.credito)
        total_debitos += movimiento.debito
        total_creditos += movimiento.credito
        lineas.append(
            {
                "asiento_id": asiento.id,
                "asiento_numero": asiento.numero,
                "fecha": asiento.fecha,
                "descripcion": movimiento.descripcion or asiento.descripcion,
                "debito": movimiento.debito,
                "credito": movimiento.credito,
                "saldo": saldo,
            }
        )

    return {
        "cuenta_id": cuenta.id,
        "codigo": cuenta.codigo,
        "nombre": cuenta.nombre,
        "naturaleza": cuenta.naturaleza,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "saldo_inicial": saldo_inicial,
        "movimientos": lineas,
        "total_debitos": total_debitos,
        "total_creditos": total_creditos,
        "saldo_final": saldo,
    }
