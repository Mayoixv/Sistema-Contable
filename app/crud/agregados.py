from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.asiento import Asiento, MovimientoContable
from app.models.cuenta import NaturalezaCuenta


def signo_naturaleza(naturaleza: NaturalezaCuenta) -> int:
    # Cuentas deudoras (activo/gasto/costo): el saldo aumenta con el débito.
    # Cuentas acreedoras (pasivo/patrimonio/ingreso): aumenta con el crédito.
    return 1 if naturaleza == NaturalezaCuenta.DEUDORA else -1


def sin_cero_negativo(valor: Decimal) -> Decimal:
    # Decimal conserva el signo al multiplicar por -1 (da "-0"); se normaliza
    # para que la API nunca muestre un saldo cero como negativo.
    return valor + Decimal("0")


def sumar_por_cuenta(
    db: Session,
    *,
    cuenta_ids: set[int] | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    hasta_exclusive: bool = False,
    incluir_cierres: bool = True,
) -> dict[int, tuple[Decimal, Decimal]]:
    """Suma débito/crédito agrupado por cuenta_id, en el rango de fechas dado.

    `incluir_cierres=False` deja fuera los asientos de cierre de ejercicio.
    Lo necesita el estado de resultados: el asiento de cierre salda las
    cuentas nominales, así que incluirlo haría que un período ya cerrado
    reportara ingresos y gastos en cero. El balance general, en cambio, los
    necesita incluidos (ver `balance_general.py`).
    """
    stmt = (
        select(
            MovimientoContable.cuenta_id,
            func.sum(MovimientoContable.debito),
            func.sum(MovimientoContable.credito),
        )
        .join(Asiento, Asiento.id == MovimientoContable.asiento_id)
        .group_by(MovimientoContable.cuenta_id)
    )
    if not incluir_cierres:
        stmt = stmt.where(Asiento.es_cierre.is_(False))
    if cuenta_ids is not None:
        stmt = stmt.where(MovimientoContable.cuenta_id.in_(cuenta_ids))
    if desde is not None:
        stmt = stmt.where(Asiento.fecha >= desde)
    if hasta is not None:
        stmt = stmt.where(Asiento.fecha < hasta if hasta_exclusive else Asiento.fecha <= hasta)
    return {cuenta_id: (debito, credito) for cuenta_id, debito, credito in db.execute(stmt)}
