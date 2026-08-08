import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import crud
from app.models.cuenta import Cuenta, TipoCuenta
from app.schemas.cuenta import CuentaCreate


def test_crear_cuenta_raiz(db_session: Session) -> None:
    cuenta = crud.cuenta.create(
        db_session,
        obj_in=CuentaCreate(codigo="1", nombre="Activo", tipo=TipoCuenta.ACTIVO),
    )
    assert cuenta.id is not None
    assert cuenta.nivel == 1
    assert cuenta.naturaleza.value == "deudora"  # autocompletada según el tipo
    assert cuenta.acepta_movimiento is True


def test_crear_cuenta_hija_marca_padre_como_sumaria(db_session: Session) -> None:
    padre = crud.cuenta.create(
        db_session,
        obj_in=CuentaCreate(codigo="1", nombre="Activo", tipo=TipoCuenta.ACTIVO),
    )
    assert padre.acepta_movimiento is True

    hija = crud.cuenta.create(
        db_session,
        obj_in=CuentaCreate(
            codigo="1.1", nombre="Activo corriente", tipo=TipoCuenta.ACTIVO, padre_id=padre.id
        ),
    )
    db_session.refresh(padre)

    assert hija.nivel == 2
    assert padre.acepta_movimiento is False  # ganó una hija: ya no es de detalle


def test_eliminar_cuenta_con_hijas_bloqueado(db_session: Session) -> None:
    padre = crud.cuenta.create(
        db_session,
        obj_in=CuentaCreate(codigo="1", nombre="Activo", tipo=TipoCuenta.ACTIVO),
    )
    crud.cuenta.create(
        db_session,
        obj_in=CuentaCreate(
            codigo="1.1", nombre="Activo corriente", tipo=TipoCuenta.ACTIVO, padre_id=padre.id
        ),
    )

    with pytest.raises(crud.cuenta.CuentaConHijasError):
        crud.cuenta.remove(db_session, db_obj=padre)


def test_eliminar_cuenta_con_movimientos_bloqueado(
    db_session: Session, plan_cuentas: dict[str, Cuenta]
) -> None:
    from datetime import date

    from app.schemas.asiento import AsientoCreate
    from app.schemas.movimiento import MovimientoCreate

    crud.asiento.create(
        db_session,
        obj_in=AsientoCreate(
            fecha=date(2026, 1, 1),
            descripcion="Aporte inicial",
            movimientos=[
                MovimientoCreate(cuenta_id=plan_cuentas["caja"].id, debito="1000"),
                MovimientoCreate(cuenta_id=plan_cuentas["capital"].id, credito="1000"),
            ],
        ),
    )

    with pytest.raises(crud.cuenta.CuentaConMovimientosError):
        crud.cuenta.remove(db_session, db_obj=plan_cuentas["caja"])


def test_endpoint_crear_cuenta_codigo_duplicado(client: TestClient) -> None:
    payload = {"codigo": "1", "nombre": "Activo", "tipo": "activo"}
    r1 = client.post("/api/v1/cuentas/", json=payload)
    assert r1.status_code == 201

    r2 = client.post("/api/v1/cuentas/", json=payload)
    assert r2.status_code == 409


def test_endpoint_arbol_cuentas_anida_hijas(client: TestClient) -> None:
    padre = client.post(
        "/api/v1/cuentas/", json={"codigo": "1", "nombre": "Activo", "tipo": "activo"}
    ).json()
    client.post(
        "/api/v1/cuentas/",
        json={
            "codigo": "1.1",
            "nombre": "Activo corriente",
            "tipo": "activo",
            "padre_id": padre["id"],
        },
    )

    arbol = client.get("/api/v1/cuentas/arbol").json()
    assert len(arbol) == 1
    assert arbol[0]["codigo"] == "1"
    assert len(arbol[0]["hijas"]) == 1
    assert arbol[0]["hijas"][0]["codigo"] == "1.1"


def test_endpoint_eliminar_cuenta_inexistente_404(client: TestClient) -> None:
    r = client.delete("/api/v1/cuentas/999")
    assert r.status_code == 404
