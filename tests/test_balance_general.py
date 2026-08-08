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


def test_balance_general_cuadra_incluyendo_resultado_acumulado(
    client: TestClient, plan_cuentas: dict[str, Cuenta]
) -> None:
    caja = plan_cuentas["caja"].id
    banco = plan_cuentas["banco"].id
    proveedores = plan_cuentas["proveedores"].id
    capital = plan_cuentas["capital"].id
    ventas = plan_cuentas["ventas"].id
    costo = plan_cuentas["costo_ventas"].id
    gasto = plan_cuentas["gastos_admin"].id

    _crear_asiento(client, "2026-01-01", caja, capital, "5000")  # aporte de capital
    _crear_asiento(client, "2026-01-02", banco, proveedores, "2000")  # deuda con proveedor
    _crear_asiento(client, "2026-01-10", caja, ventas, "1000")  # venta
    _crear_asiento(client, "2026-01-10", costo, caja, "400")  # costo de esa venta
    _crear_asiento(client, "2026-01-15", gasto, banco, "150")  # gasto operativo

    r = client.get("/api/v1/balance-general/", params={"fecha_corte": "2026-01-31"})
    assert r.status_code == 200
    data = r.json()

    assert Decimal(data["total_activo"]) == Decimal("7450.00")
    assert Decimal(data["total_pasivo"]) == Decimal("2000.00")
    assert Decimal(data["resultado_acumulado"]) == Decimal("450.00")
    assert Decimal(data["total_patrimonio"]) == Decimal("5450.00")
    assert Decimal(data["total_pasivo_mas_patrimonio"]) == Decimal("7450.00")
    assert data["balanceado"] is True

    estado = client.get(
        "/api/v1/estado-resultados/", params={"fecha_hasta": "2026-01-31"}
    ).json()
    assert Decimal(data["resultado_acumulado"]) == Decimal(estado["utilidad_neta"])


def test_balance_general_sin_movimientos_cuadra_en_cero(
    client: TestClient, plan_cuentas: dict[str, Cuenta]
) -> None:
    r = client.get("/api/v1/balance-general/")
    data = r.json()
    assert Decimal(data["total_activo"]) == Decimal("0")
    assert Decimal(data["total_pasivo_mas_patrimonio"]) == Decimal("0")
    assert data["balanceado"] is True


def test_exportar_csv(client: TestClient, plan_cuentas: dict[str, Cuenta]) -> None:
    _crear_asiento(client, "2026-01-01", plan_cuentas["caja"].id, plan_cuentas["capital"].id, "5000")

    r = client.get("/api/v1/balance-general/", params={"formato": "csv"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")

    filas = r.text.splitlines()
    assert filas[0] == "seccion,codigo,nombre,saldo"
    assert any(linea.startswith(f"activo,{plan_cuentas['caja'].codigo}") for linea in filas)
    assert any("Resultado acumulado" in linea for linea in filas)
    assert any("TOTAL ACTIVO" in linea for linea in filas)
