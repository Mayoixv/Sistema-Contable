from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app import crud
from app.models.cuenta import Cuenta
from app.schemas.asiento import AsientoCreate
from app.schemas.cuenta import CuentaCreate
from app.schemas.movimiento import MovimientoCreate


def test_asiento_no_balanceado_falla_en_el_schema() -> None:
    with pytest.raises(ValidationError, match="no está balanceado"):
        AsientoCreate(
            fecha=date(2026, 1, 1),
            descripcion="Desbalanceado",
            movimientos=[
                MovimientoCreate(cuenta_id=1, debito="100"),
                MovimientoCreate(cuenta_id=2, credito="50"),
            ],
        )


def test_movimiento_con_debito_y_credito_a_la_vez_falla() -> None:
    with pytest.raises(ValidationError, match="débito y crédito a la vez"):
        MovimientoCreate(cuenta_id=1, debito="100", credito="100")


def test_movimiento_sin_monto_falla() -> None:
    with pytest.raises(ValidationError, match="débito o crédito mayor a cero"):
        MovimientoCreate(cuenta_id=1)


def test_asiento_con_un_solo_movimiento_falla() -> None:
    with pytest.raises(ValidationError):
        AsientoCreate(
            fecha=date(2026, 1, 1),
            descripcion="Un solo movimiento",
            movimientos=[MovimientoCreate(cuenta_id=1, debito="100")],
        )


def test_crear_asiento_endpoint_exitoso(
    client: TestClient, plan_cuentas: dict[str, Cuenta]
) -> None:
    payload = {
        "fecha": "2026-01-01",
        "descripcion": "Aporte inicial de capital",
        "movimientos": [
            {"cuenta_id": plan_cuentas["caja"].id, "debito": "1000.00"},
            {"cuenta_id": plan_cuentas["capital"].id, "credito": "1000.00"},
        ],
    }
    r = client.post("/api/v1/asientos/", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["numero"] == 1
    assert data["reversa_de_id"] is None
    assert data["reversado_por_id"] is None
    assert len(data["movimientos"]) == 2


def test_crear_asiento_cuenta_sumaria_rechazada(
    client: TestClient, plan_cuentas: dict[str, Cuenta], db_session: Session
) -> None:
    padre = crud.cuenta.create(
        db_session,
        obj_in=CuentaCreate(codigo="1", nombre="Activo", tipo="activo"),
    )
    crud.cuenta.create(
        db_session,
        obj_in=CuentaCreate(codigo="1.1", nombre="Activo corriente", tipo="activo", padre_id=padre.id),
    )
    # padre ahora es sumaria (ganó una hija): no puede recibir movimientos

    payload = {
        "fecha": "2026-01-01",
        "descripcion": "Intento inválido",
        "movimientos": [
            {"cuenta_id": padre.id, "debito": "100"},
            {"cuenta_id": plan_cuentas["capital"].id, "credito": "100"},
        ],
    }
    r = client.post("/api/v1/asientos/", json=payload)
    assert r.status_code == 400
    assert "sumaria" in r.json()["detail"]


def test_crear_asiento_cuenta_inactiva_rechazada(
    client: TestClient, plan_cuentas: dict[str, Cuenta]
) -> None:
    r = client.patch(f"/api/v1/cuentas/{plan_cuentas['caja'].id}", json={"activa": False})
    assert r.status_code == 200

    payload = {
        "fecha": "2026-01-01",
        "descripcion": "Intento con cuenta inactiva",
        "movimientos": [
            {"cuenta_id": plan_cuentas["caja"].id, "debito": "100"},
            {"cuenta_id": plan_cuentas["capital"].id, "credito": "100"},
        ],
    }
    r = client.post("/api/v1/asientos/", json=payload)
    assert r.status_code == 400
    assert "inactiva" in r.json()["detail"]


def test_numeracion_autoincremental(client: TestClient, plan_cuentas: dict[str, Cuenta]) -> None:
    payload = {
        "fecha": "2026-01-01",
        "descripcion": "Asiento",
        "movimientos": [
            {"cuenta_id": plan_cuentas["caja"].id, "debito": "100"},
            {"cuenta_id": plan_cuentas["capital"].id, "credito": "100"},
        ],
    }
    primero = client.post("/api/v1/asientos/", json=payload).json()
    segundo = client.post("/api/v1/asientos/", json=payload).json()
    assert primero["numero"] == 1
    assert segundo["numero"] == 2


def test_reversar_asiento_invierte_montos_y_enlaza(
    client: TestClient, plan_cuentas: dict[str, Cuenta]
) -> None:
    payload = {
        "fecha": "2026-01-01",
        "descripcion": "Aporte inicial",
        "movimientos": [
            {"cuenta_id": plan_cuentas["caja"].id, "debito": "1000"},
            {"cuenta_id": plan_cuentas["capital"].id, "credito": "1000"},
        ],
    }
    original = client.post("/api/v1/asientos/", json=payload).json()

    r = client.post(f"/api/v1/asientos/{original['id']}/reversar?fecha=2026-01-15")
    assert r.status_code == 201
    reversion = r.json()

    assert reversion["reversa_de_id"] == original["id"]
    assert reversion["fecha"] == "2026-01-15"

    montos_originales = {
        m["cuenta_id"]: (Decimal(m["debito"]), Decimal(m["credito"]))
        for m in original["movimientos"]
    }
    for m in reversion["movimientos"]:
        debito_orig, credito_orig = montos_originales[m["cuenta_id"]]
        assert Decimal(m["debito"]) == credito_orig
        assert Decimal(m["credito"]) == debito_orig

    original_actualizado = client.get(f"/api/v1/asientos/{original['id']}").json()
    assert original_actualizado["reversado_por_id"] == reversion["id"]


def test_reversar_dos_veces_bloqueado(client: TestClient, plan_cuentas: dict[str, Cuenta]) -> None:
    payload = {
        "fecha": "2026-01-01",
        "descripcion": "Aporte inicial",
        "movimientos": [
            {"cuenta_id": plan_cuentas["caja"].id, "debito": "1000"},
            {"cuenta_id": plan_cuentas["capital"].id, "credito": "1000"},
        ],
    }
    original = client.post("/api/v1/asientos/", json=payload).json()
    client.post(f"/api/v1/asientos/{original['id']}/reversar")

    r = client.post(f"/api/v1/asientos/{original['id']}/reversar")
    assert r.status_code == 409


def test_eliminar_asiento_reversado_bloqueado(
    client: TestClient, plan_cuentas: dict[str, Cuenta]
) -> None:
    payload = {
        "fecha": "2026-01-01",
        "descripcion": "Aporte inicial",
        "movimientos": [
            {"cuenta_id": plan_cuentas["caja"].id, "debito": "1000"},
            {"cuenta_id": plan_cuentas["capital"].id, "credito": "1000"},
        ],
    }
    original = client.post("/api/v1/asientos/", json=payload).json()
    client.post(f"/api/v1/asientos/{original['id']}/reversar")

    r = client.delete(f"/api/v1/asientos/{original['id']}")
    assert r.status_code == 409


def _crear(client: TestClient, fecha: str, debito_id: int, credito_id: int, monto: str = "100") -> dict:
    payload = {
        "fecha": fecha,
        "descripcion": f"Asiento {fecha}",
        "movimientos": [
            {"cuenta_id": debito_id, "debito": monto},
            {"cuenta_id": credito_id, "credito": monto},
        ],
    }
    r = client.post("/api/v1/asientos/", json=payload)
    assert r.status_code == 201
    return r.json()


def test_listar_asientos_respuesta_paginada(
    client: TestClient, plan_cuentas: dict[str, Cuenta]
) -> None:
    for _ in range(3):
        _crear(client, "2026-01-01", plan_cuentas["caja"].id, plan_cuentas["capital"].id)

    r = client.get("/api/v1/asientos/", params={"skip": 1, "limit": 1})
    data = r.json()
    assert data["total"] == 3
    assert data["skip"] == 1
    assert data["limit"] == 1
    assert len(data["items"]) == 1


def test_listar_asientos_filtra_por_rango_de_fecha(
    client: TestClient, plan_cuentas: dict[str, Cuenta]
) -> None:
    _crear(client, "2026-01-05", plan_cuentas["caja"].id, plan_cuentas["capital"].id)
    _crear(client, "2026-02-05", plan_cuentas["caja"].id, plan_cuentas["capital"].id)

    r = client.get(
        "/api/v1/asientos/", params={"fecha_desde": "2026-01-01", "fecha_hasta": "2026-01-31"}
    )
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["fecha"] == "2026-01-05"


def test_listar_asientos_filtra_por_cuenta(
    client: TestClient, plan_cuentas: dict[str, Cuenta]
) -> None:
    _crear(client, "2026-01-01", plan_cuentas["caja"].id, plan_cuentas["capital"].id)
    _crear(client, "2026-01-02", plan_cuentas["banco"].id, plan_cuentas["capital"].id)

    r = client.get("/api/v1/asientos/", params={"cuenta_id": plan_cuentas["banco"].id})
    data = r.json()
    assert data["total"] == 1
    assert any(m["cuenta_id"] == plan_cuentas["banco"].id for m in data["items"][0]["movimientos"])


def test_listar_asientos_fecha_desde_posterior_a_hasta_400(
    client: TestClient, plan_cuentas: dict[str, Cuenta]
) -> None:
    r = client.get(
        "/api/v1/asientos/", params={"fecha_desde": "2026-02-01", "fecha_hasta": "2026-01-01"}
    )
    assert r.status_code == 400


def test_eliminar_asiento_normal_ok(client: TestClient, plan_cuentas: dict[str, Cuenta]) -> None:
    payload = {
        "fecha": "2026-01-01",
        "descripcion": "Aporte inicial",
        "movimientos": [
            {"cuenta_id": plan_cuentas["caja"].id, "debito": "1000"},
            {"cuenta_id": plan_cuentas["capital"].id, "credito": "1000"},
        ],
    }
    original = client.post("/api/v1/asientos/", json=payload).json()

    r = client.delete(f"/api/v1/asientos/{original['id']}")
    assert r.status_code == 204
    assert client.get(f"/api/v1/asientos/{original['id']}").status_code == 404
