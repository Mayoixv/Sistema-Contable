from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.models.cuenta import Cuenta


def _crear_asiento(client: TestClient, fecha: str, caja_id: int, capital_id: int, monto: str) -> None:
    client.post(
        "/api/v1/asientos/",
        json={
            "fecha": fecha,
            "descripcion": f"Movimiento {fecha}",
            "movimientos": [
                {"cuenta_id": caja_id, "debito": monto},
                {"cuenta_id": capital_id, "credito": monto},
            ],
        },
    )


def test_saldo_corre_linea_a_linea_en_cuenta_deudora(
    client: TestClient, plan_cuentas: dict[str, Cuenta]
) -> None:
    caja_id = plan_cuentas["caja"].id
    capital_id = plan_cuentas["capital"].id
    _crear_asiento(client, "2026-01-05", caja_id, capital_id, "100.00")
    _crear_asiento(client, "2026-01-10", caja_id, capital_id, "50.00")

    r = client.get(f"/api/v1/libro-mayor/{caja_id}")
    assert r.status_code == 200
    data = r.json()

    assert data["saldo_inicial"] == "0.00" or Decimal(data["saldo_inicial"]) == Decimal("0")
    assert len(data["movimientos"]) == 2
    assert Decimal(data["movimientos"][0]["saldo"]) == Decimal("100.00")
    assert Decimal(data["movimientos"][1]["saldo"]) == Decimal("150.00")
    assert Decimal(data["saldo_final"]) == Decimal("150.00")
    assert Decimal(data["total_debitos"]) == Decimal("150.00")


def test_saldo_baja_con_credito_en_cuenta_acreedora(
    client: TestClient, plan_cuentas: dict[str, Cuenta]
) -> None:
    caja_id = plan_cuentas["caja"].id
    capital_id = plan_cuentas["capital"].id
    _crear_asiento(client, "2026-01-05", caja_id, capital_id, "100.00")

    r = client.get(f"/api/v1/libro-mayor/{capital_id}")
    data = r.json()
    # capital es acreedora: el crédito sube el saldo
    assert Decimal(data["saldo_final"]) == Decimal("100.00")


def test_saldo_inicial_considera_movimientos_previos_a_fecha_desde(
    client: TestClient, plan_cuentas: dict[str, Cuenta]
) -> None:
    caja_id = plan_cuentas["caja"].id
    capital_id = plan_cuentas["capital"].id
    _crear_asiento(client, "2026-01-05", caja_id, capital_id, "100.00")
    _crear_asiento(client, "2026-01-20", caja_id, capital_id, "30.00")

    r = client.get(f"/api/v1/libro-mayor/{caja_id}", params={"fecha_desde": "2026-01-10"})
    data = r.json()

    assert Decimal(data["saldo_inicial"]) == Decimal("100.00")
    assert len(data["movimientos"]) == 1
    assert Decimal(data["saldo_final"]) == Decimal("130.00")


def test_fecha_desde_posterior_a_fecha_hasta_es_400(
    client: TestClient, plan_cuentas: dict[str, Cuenta]
) -> None:
    caja_id = plan_cuentas["caja"].id
    r = client.get(
        f"/api/v1/libro-mayor/{caja_id}",
        params={"fecha_desde": "2026-02-01", "fecha_hasta": "2026-01-01"},
    )
    assert r.status_code == 400


def test_cuenta_inexistente_404(client: TestClient) -> None:
    assert client.get("/api/v1/libro-mayor/999").status_code == 404


def test_exportar_csv(client: TestClient, plan_cuentas: dict[str, Cuenta]) -> None:
    caja_id = plan_cuentas["caja"].id
    capital_id = plan_cuentas["capital"].id
    _crear_asiento(client, "2026-01-05", caja_id, capital_id, "100.00")

    r = client.get(f"/api/v1/libro-mayor/{caja_id}", params={"formato": "csv"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert f"libro_mayor_{plan_cuentas['caja'].codigo}.csv" in r.headers["content-disposition"]

    filas = r.text.splitlines()
    assert filas[0] == "fecha,asiento_numero,descripcion,debito,credito,saldo"
    assert filas[1].split(",")[2] == "Saldo inicial"
    assert filas[-1].split(",")[2] == "TOTAL"
