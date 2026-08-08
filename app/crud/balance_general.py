from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.agregados import signo_naturaleza, sin_cero_negativo, sumar_por_cuenta
from app.crud.estado_resultados import get_estado_resultados
from app.models.cuenta import Cuenta, TipoCuenta


def _filas_por_tipo(
    cuentas: list[Cuenta], sumas: dict[int, tuple[Decimal, Decimal]], tipo: TipoCuenta
) -> tuple[list[dict], Decimal]:
    filas = []
    total = Decimal("0")
    for cuenta in cuentas:
        if cuenta.tipo != tipo:
            continue
        debito, credito = sumas.get(cuenta.id, (Decimal("0"), Decimal("0")))
        saldo = sin_cero_negativo(signo_naturaleza(cuenta.naturaleza) * (debito - credito))
        total += saldo
        filas.append(
            {"cuenta_id": cuenta.id, "codigo": cuenta.codigo, "nombre": cuenta.nombre, "saldo": saldo}
        )
    return filas, sin_cero_negativo(total)


def get_balance_general(db: Session, *, fecha_corte: date | None = None) -> dict:
    cuentas = list(
        db.scalars(
            select(Cuenta)
            .where(
                Cuenta.acepta_movimiento.is_(True),
                Cuenta.activa.is_(True),
                Cuenta.tipo.in_([TipoCuenta.ACTIVO, TipoCuenta.PASIVO, TipoCuenta.PATRIMONIO]),
            )
            .order_by(Cuenta.codigo)
        )
    )
    sumas = sumar_por_cuenta(db, cuenta_ids={c.id for c in cuentas}, hasta=fecha_corte)

    activos, total_activo = _filas_por_tipo(cuentas, sumas, TipoCuenta.ACTIVO)
    pasivos, total_pasivo = _filas_por_tipo(cuentas, sumas, TipoCuenta.PASIVO)
    patrimonio, total_patrimonio_cuentas = _filas_por_tipo(cuentas, sumas, TipoCuenta.PATRIMONIO)

    # El resultado de las cuentas nominales (ingreso/costo/gasto) que todavía
    # NO fue cerrado no está reflejado en ninguna cuenta real: hay que sumarlo
    # al patrimonio para que Activo = Pasivo + Patrimonio cuadre.
    #
    # `incluir_cierres=True` es lo que hace que esto siga siendo correcto
    # después de un cierre de ejercicio: el asiento de cierre salda las
    # cuentas nominales contra patrimonio, así que al incluirlo el neto da
    # cero y la utilidad queda contada una sola vez (en la cuenta de
    # patrimonio). Si se excluyera, se contaría dos veces.
    resultado_acumulado = get_estado_resultados(
        db, fecha_desde=None, fecha_hasta=fecha_corte, incluir_cierres=True
    )["utilidad_neta"]
    total_patrimonio = sin_cero_negativo(total_patrimonio_cuentas + resultado_acumulado)
    total_pasivo_mas_patrimonio = sin_cero_negativo(total_pasivo + total_patrimonio)

    return {
        "fecha_corte": fecha_corte,
        "activos": activos,
        "pasivos": pasivos,
        "patrimonio": patrimonio,
        "resultado_acumulado": resultado_acumulado,
        "total_activo": total_activo,
        "total_pasivo": total_pasivo,
        "total_patrimonio": total_patrimonio,
        "total_pasivo_mas_patrimonio": total_pasivo_mas_patrimonio,
        "balanceado": total_activo == total_pasivo_mas_patrimonio,
    }
