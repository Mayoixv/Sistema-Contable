from decimal import Decimal

from fastapi.testclient import TestClient

from app.models.cuenta import Cuenta


def _crear_asiento(client: TestClient, fecha: str, debito_id: int, credito_id: int, monto: str) -> None:
    r = client.post(
        "/api/v1/asientos/",
        json={
            "fecha": fecha,
            "descripcion": f"Movimiento {fecha}",
            "movimientos": [
                {"cuenta_id": debito_id, "debito": monto},
                {"cuenta_id": credito_id, "credito": monto},
            ],
        },
    )
    assert r.status_code == 201


def test_incluye_cuentas_de_detalle_sin_movimientos(
    client: TestClient, plan_cuentas: dict[str, Cuenta]
) -> None:
    r = client.get("/api/v1/balance-comprobacion/")
    data = r.json()
    codigos = {fila["codigo"] for fila in data["cuentas"]}
    # todas las cuentas de detalle aparecen aunque nunca tuvieron actividad
    assert codigos == {c.codigo for c in plan_cuentas.values()}
    for fila in data["cuentas"]:
        assert Decimal(fila["saldo_final"]) == Decimal("0")


def test_siempre_balanceado_por_partida_doble(
    client: TestClient, plan_cuentas: dict[str, Cuenta]
) -> None:
    _crear_asiento(client, "2026-01-05", plan_cuentas["caja"].id, plan_cuentas["capital"].id, "1000")
    _crear_asiento(
        client, "2026-01-10", plan_cuentas["gastos_admin"].id, plan_cuentas["banco"].id, "150"
    )

    r = client.get("/api/v1/balance-comprobacion/")
    data = r.json()

    assert data["balanceado"] is True
    assert Decimal(data["total_debitos"]) == Decimal(data["total_creditos"])
    assert Decimal(data["total_debitos"]) == Decimal("1150.00")


def test_no_muestra_cero_negativo_cuando_se_cancela_el_saldo(
    client: TestClient, plan_cuentas: dict[str, Cuenta]
) -> None:
    proveedores_id = plan_cuentas["proveedores"].id
    caja_id = plan_cuentas["caja"].id
    # Se genera la deuda (crédito en proveedores) y luego se cancela por completo
    # (débito en proveedores): el saldo neto debe quedar en "0", no en "-0".
    _crear_asiento(client, "2026-01-05", caja_id, proveedores_id, "100")
    _crear_asiento(client, "2026-01-10", proveedores_id, caja_id, "100")

    r = client.get("/api/v1/balance-comprobacion/")
    fila = next(f for f in r.json()["cuentas"] if f["cuenta_id"] == proveedores_id)

    assert Decimal(fila["saldo_final"]) == Decimal("0")
    assert not fila["saldo_final"].startswith("-")


def test_exportar_csv(client: TestClient, plan_cuentas: dict[str, Cuenta]) -> None:
    _crear_asiento(client, "2026-01-05", plan_cuentas["caja"].id, plan_cuentas["capital"].id, "1000")

    r = client.get("/api/v1/balance-comprobacion/", params={"formato": "csv"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]

    filas = r.text.splitlines()
    assert filas[0] == "codigo,nombre,naturaleza,saldo_inicial,debito,credito,saldo_final"
    assert any(linea.startswith(plan_cuentas["caja"].codigo) for linea in filas)
    assert filas[-1].split(",")[1] == "TOTAL"
