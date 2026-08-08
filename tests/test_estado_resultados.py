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


def test_omite_cuentas_nominales_sin_actividad(
    client: TestClient, plan_cuentas: dict[str, Cuenta]
) -> None:
    r = client.get("/api/v1/estado-resultados/")
    data = r.json()
    assert data["ingresos"] == []
    assert data["costos"] == []
    assert data["gastos"] == []
    assert Decimal(data["utilidad_neta"]) == Decimal("0")


def test_utilidad_bruta_y_neta(client: TestClient, plan_cuentas: dict[str, Cuenta]) -> None:
    caja_id = plan_cuentas["caja"].id
    ventas_id = plan_cuentas["ventas"].id
    costo_id = plan_cuentas["costo_ventas"].id
    gasto_id = plan_cuentas["gastos_admin"].id

    _crear_asiento(client, "2026-01-05", caja_id, ventas_id, "1000")  # ingreso
    _crear_asiento(client, "2026-01-05", costo_id, caja_id, "400")  # costo de venta
    _crear_asiento(client, "2026-01-10", gasto_id, caja_id, "150")  # gasto operativo

    r = client.get("/api/v1/estado-resultados/", params={"fecha_desde": "2026-01-01", "fecha_hasta": "2026-01-31"})
    data = r.json()

    assert Decimal(data["total_ingresos"]) == Decimal("1000.00")
    assert Decimal(data["total_costos"]) == Decimal("400.00")
    assert Decimal(data["total_gastos"]) == Decimal("150.00")
    assert Decimal(data["utilidad_bruta"]) == Decimal("600.00")
    assert Decimal(data["utilidad_neta"]) == Decimal("450.00")


def test_periodo_excluye_movimientos_fuera_de_rango(
    client: TestClient, plan_cuentas: dict[str, Cuenta]
) -> None:
    caja_id = plan_cuentas["caja"].id
    ventas_id = plan_cuentas["ventas"].id
    _crear_asiento(client, "2026-01-05", caja_id, ventas_id, "1000")
    _crear_asiento(client, "2026-02-05", caja_id, ventas_id, "500")

    r = client.get(
        "/api/v1/estado-resultados/", params={"fecha_desde": "2026-01-01", "fecha_hasta": "2026-01-31"}
    )
    data = r.json()
    assert Decimal(data["total_ingresos"]) == Decimal("1000.00")


def test_exportar_csv(client: TestClient, plan_cuentas: dict[str, Cuenta]) -> None:
    _crear_asiento(client, "2026-01-05", plan_cuentas["caja"].id, plan_cuentas["ventas"].id, "1000")

    r = client.get("/api/v1/estado-resultados/", params={"formato": "csv"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")

    filas = r.text.splitlines()
    assert filas[0] == "seccion,codigo,nombre,monto"
    assert any(linea.startswith(f"ingreso,{plan_cuentas['ventas'].codigo}") for linea in filas)
    assert any("UTILIDAD NETA" in linea for linea in filas)
