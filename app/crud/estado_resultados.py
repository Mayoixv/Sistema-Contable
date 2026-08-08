from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.agregados import sin_cero_negativo, sumar_por_cuenta
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
        if debito == 0 and credito == 0:
            continue  # sin actividad en el período: se omite del reporte

        # Ingreso (acreedora): crece con el crédito. Costo/Gasto (deudora): con el débito.
        monto = sin_cero_negativo((credito - debito) if tipo == TipoCuenta.INGRESO else (debito - credito))
        total += monto
        filas.append(
            {"cuenta_id": cuenta.id, "codigo": cuenta.codigo, "nombre": cuenta.nombre, "monto": monto}
        )
    return filas, sin_cero_negativo(total)


def get_estado_resultados(
    db: Session,
    *,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    incluir_cierres: bool = False,
) -> dict:
    """Estado de resultados del período.

    Por defecto ignora los asientos de cierre: son un artificio contable
    para saldar las cuentas nominales, no actividad del negocio, y si se
    contaran un ejercicio ya cerrado mostraría todo en cero. `balance_general`
    lo llama con `incluir_cierres=True` por el motivo contrario.
    """
    cuentas = list(
        db.scalars(
            select(Cuenta)
            .where(
                Cuenta.acepta_movimiento.is_(True),
                Cuenta.activa.is_(True),
                Cuenta.tipo.in_([TipoCuenta.INGRESO, TipoCuenta.COSTO, TipoCuenta.GASTO]),
            )
            .order_by(Cuenta.codigo)
        )
    )
    sumas = sumar_por_cuenta(
        db,
        cuenta_ids={c.id for c in cuentas},
        desde=fecha_desde,
        hasta=fecha_hasta,
        incluir_cierres=incluir_cierres,
    )

    ingresos, total_ingresos = _filas_por_tipo(cuentas, sumas, TipoCuenta.INGRESO)
    costos, total_costos = _filas_por_tipo(cuentas, sumas, TipoCuenta.COSTO)
    gastos, total_gastos = _filas_por_tipo(cuentas, sumas, TipoCuenta.GASTO)

    utilidad_bruta = sin_cero_negativo(total_ingresos - total_costos)
    utilidad_neta = sin_cero_negativo(utilidad_bruta - total_gastos)

    return {
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "ingresos": ingresos,
        "costos": costos,
        "gastos": gastos,
        "total_ingresos": total_ingresos,
        "total_costos": total_costos,
        "total_gastos": total_gastos,
        "utilidad_bruta": utilidad_bruta,
        "utilidad_neta": utilidad_neta,
    }
