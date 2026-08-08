from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.crud.agregados import sin_cero_negativo, sumar_por_cuenta
from app.crud.asiento import siguiente_numero
from app.models.asiento import Asiento, MovimientoContable
from app.models.cierre import Cierre
from app.models.cuenta import Cuenta, TipoCuenta
from app.models.usuario import Usuario

TIPOS_NOMINALES = (TipoCuenta.INGRESO, TipoCuenta.COSTO, TipoCuenta.GASTO)


class CuentaResultadoInvalidaError(Exception):
    pass


class PeriodoYaCerradoError(Exception):
    pass


class SinResultadoParaCerrarError(Exception):
    pass


def get_multi(db: Session) -> list[Cierre]:
    stmt = (
        select(Cierre)
        .options(selectinload(Cierre.usuario))
        .order_by(Cierre.fecha_cierre.desc())
    )
    return list(db.scalars(stmt))


def get_ultimo(db: Session) -> Cierre | None:
    return db.scalar(select(Cierre).order_by(Cierre.fecha_cierre.desc()).limit(1))


def _validar_cuenta_resultado(db: Session, cuenta_id: int) -> Cuenta:
    cuenta = db.get(Cuenta, cuenta_id)
    if cuenta is None:
        raise CuentaResultadoInvalidaError(f"La cuenta con id={cuenta_id} no existe")
    if cuenta.tipo != TipoCuenta.PATRIMONIO:
        raise CuentaResultadoInvalidaError(
            f"La cuenta '{cuenta.codigo}' es de tipo '{cuenta.tipo.value}': el resultado "
            "del ejercicio debe trasladarse a una cuenta de patrimonio"
        )
    if not cuenta.acepta_movimiento:
        raise CuentaResultadoInvalidaError(
            f"La cuenta '{cuenta.codigo}' es sumaria y no acepta movimientos directos"
        )
    if not cuenta.activa:
        raise CuentaResultadoInvalidaError(f"La cuenta '{cuenta.codigo}' está inactiva")
    return cuenta


def crear(
    db: Session,
    *,
    fecha_cierre: date,
    cuenta_resultado_id: int,
    usuario: Usuario | None = None,
) -> Cierre:
    """Genera el asiento que salda las cuentas nominales contra patrimonio.

    El saldo de cada cuenta nominal se calcula **incluyendo** los asientos de
    cierres anteriores. Eso hace que lo ya cerrado dé cero y solo se cierre
    la actividad posterior, sin tener que llevar la cuenta del último cierre.
    """
    cuenta_resultado = _validar_cuenta_resultado(db, cuenta_resultado_id)

    ultimo = get_ultimo(db)
    if ultimo is not None and fecha_cierre <= ultimo.fecha_cierre:
        raise PeriodoYaCerradoError(
            f"Ya existe un cierre al {ultimo.fecha_cierre}; la fecha del nuevo cierre "
            "debe ser posterior"
        )

    nominales = list(
        db.scalars(
            select(Cuenta)
            .where(
                Cuenta.acepta_movimiento.is_(True),
                Cuenta.activa.is_(True),
                Cuenta.tipo.in_(TIPOS_NOMINALES),
            )
            .order_by(Cuenta.codigo)
        )
    )
    sumas = sumar_por_cuenta(
        db, cuenta_ids={c.id for c in nominales}, hasta=fecha_cierre, incluir_cierres=True
    )

    movimientos: list[MovimientoContable] = []
    neto_debito_total = Decimal("0")
    for cuenta in nominales:
        debito, credito = sumas.get(cuenta.id, (Decimal("0"), Decimal("0")))
        neto_debito = debito - credito
        if neto_debito == 0:
            continue  # ya saldada (o sin actividad): no se genera línea

        neto_debito_total += neto_debito
        # Se contra-asienta el saldo: una cuenta con saldo deudor se cancela
        # con un crédito por el mismo importe, y viceversa.
        movimientos.append(
            MovimientoContable(
                cuenta_id=cuenta.id,
                debito=Decimal("0") if neto_debito > 0 else -neto_debito,
                credito=neto_debito if neto_debito > 0 else Decimal("0"),
                descripcion="Cierre de ejercicio",
            )
        )

    if not movimientos:
        raise SinResultadoParaCerrarError(
            f"No hay saldos nominales pendientes de cierre al {fecha_cierre}"
        )

    # Gastos y costos suman al neto deudor; los ingresos lo restan. Por eso
    # la utilidad es el neto deudor cambiado de signo.
    utilidad_neta = sin_cero_negativo(-neto_debito_total)
    if utilidad_neta != 0:
        movimientos.append(
            MovimientoContable(
                cuenta_id=cuenta_resultado.id,
                debito=-utilidad_neta if utilidad_neta < 0 else Decimal("0"),
                credito=utilidad_neta if utilidad_neta > 0 else Decimal("0"),
                descripcion="Resultado del ejercicio",
            )
        )
    # Con utilidad exactamente cero no se agrega la línea de resultado: sería
    # un movimiento de 0/0 y violaría el CHECK que exige débito o crédito
    # mayor a cero. El asiento igual queda balanceado, porque las líneas que
    # saldan las cuentas nominales ya suman cero entre sí.

    asiento = Asiento(
        numero=siguiente_numero(db),
        fecha=fecha_cierre,
        descripcion=f"Cierre de ejercicio al {fecha_cierre}",
        es_cierre=True,
        usuario_id=usuario.id if usuario else None,
        movimientos=movimientos,
    )
    db.add(asiento)
    db.flush()  # necesita el id del asiento para enlazarlo desde el cierre

    db_obj = Cierre(
        fecha_cierre=fecha_cierre,
        asiento_id=asiento.id,
        cuenta_resultado_id=cuenta_resultado.id,
        usuario_id=usuario.id if usuario else None,
        utilidad_neta=utilidad_neta,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
