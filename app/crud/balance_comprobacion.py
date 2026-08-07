from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.agregados import signo_naturaleza, sin_cero_negativo, sumar_por_cuenta
from app.models.cuenta import Cuenta


def get_balance_comprobacion(
    db: Session, *, fecha_desde: date | None = None, fecha_hasta: date | None = None
) -> dict:
    cuentas = list(
        db.scalars(
            select(Cuenta)
            .where(Cuenta.acepta_movimiento.is_(True), Cuenta.activa.is_(True))
            .order_by(Cuenta.codigo)
        )
    )
    cuenta_ids = {c.id for c in cuentas}

    previas = (
        sumar_por_cuenta(db, cuenta_ids=cuenta_ids, hasta=fecha_desde, hasta_exclusive=True)
        if fecha_desde is not None
        else {}
    )
    del_periodo = sumar_por_cuenta(db, cuenta_ids=cuenta_ids, desde=fecha_desde, hasta=fecha_hasta)

    filas = []
    total_debitos = Decimal("0")
    total_creditos = Decimal("0")
    for cuenta in cuentas:
        signo = signo_naturaleza(cuenta.naturaleza)
        d0, c0 = previas.get(cuenta.id, (Decimal("0"), Decimal("0")))
        saldo_inicial = sin_cero_negativo(signo * (d0 - c0))

        debito, credito = del_periodo.get(cuenta.id, (Decimal("0"), Decimal("0")))
        saldo_final = sin_cero_negativo(saldo_inicial + signo * (debito - credito))

        total_debitos += debito
        total_creditos += credito

        filas.append(
            {
                "cuenta_id": cuenta.id,
                "codigo": cuenta.codigo,
                "nombre": cuenta.nombre,
                "naturaleza": cuenta.naturaleza,
                "saldo_inicial": saldo_inicial,
                "debito": debito,
                "credito": credito,
                "saldo_final": saldo_final,
            }
        )

    return {
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "cuentas": filas,
        "total_debitos": total_debitos,
        "total_creditos": total_creditos,
        "balanceado": total_debitos == total_creditos,
    }
