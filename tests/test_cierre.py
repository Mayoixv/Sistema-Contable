from decimal import Decimal

from fastapi.testclient import TestClient

from app.models.cuenta import Cuenta


def _crear_asiento(
    client: TestClient, fecha: str, debito_id: int, credito_id: int, monto: str
) -> dict:
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
    assert r.status_code == 201, r.text
    return r.json()


def _operacion_del_ejercicio(client: TestClient, cuentas: dict[str, Cuenta]) -> None:
    """Aporte, venta, costo y gasto: utilidad neta = 1000 - 400 - 150 = 450."""
    _crear_asiento(client, "2026-01-01", cuentas["caja"].id, cuentas["capital"].id, "5000")
    _crear_asiento(client, "2026-03-10", cuentas["caja"].id, cuentas["ventas"].id, "1000")
    _crear_asiento(client, "2026-03-10", cuentas["costo_ventas"].id, cuentas["caja"].id, "400")
    _crear_asiento(client, "2026-06-15", cuentas["gastos_admin"].id, cuentas["caja"].id, "150")


def test_cierre_salda_nominales_y_traslada_utilidad(
    client: TestClient, plan_cuentas: dict[str, Cuenta]
) -> None:
    _operacion_del_ejercicio(client, plan_cuentas)

    r = client.post(
        "/api/v1/cierres/",
        json={"fecha_cierre": "2026-12-31", "cuenta_resultado_id": plan_cuentas["capital"].id},
    )
    assert r.status_code == 201, r.text
    cierre = r.json()
    assert Decimal(cierre["utilidad_neta"]) == Decimal("450.00")

    # Las cuentas nominales quedan en cero después del cierre...
    balance = client.get(
        "/api/v1/balance-comprobacion/", params={"fecha_hasta": "2026-12-31"}
    ).json()
    for clave in ("ventas", "costo_ventas", "gastos_admin"):
        fila = next(f for f in balance["cuentas"] if f["cuenta_id"] == plan_cuentas[clave].id)
        assert Decimal(fila["saldo_final"]) == Decimal("0"), clave

    # ...y la utilidad quedó en la cuenta de patrimonio (5000 de aporte + 450).
    fila_capital = next(
        f for f in balance["cuentas"] if f["cuenta_id"] == plan_cuentas["capital"].id
    )
    assert Decimal(fila_capital["saldo_final"]) == Decimal("5450.00")


def test_balance_general_sigue_cuadrando_despues_del_cierre(
    client: TestClient, plan_cuentas: dict[str, Cuenta]
) -> None:
    _operacion_del_ejercicio(client, plan_cuentas)

    antes = client.get("/api/v1/balance-general/", params={"fecha_corte": "2026-12-31"}).json()
    assert antes["balanceado"] is True
    assert Decimal(antes["resultado_acumulado"]) == Decimal("450.00")

    client.post(
        "/api/v1/cierres/",
        json={"fecha_cierre": "2026-12-31", "cuenta_resultado_id": plan_cuentas["capital"].id},
    )

    despues = client.get("/api/v1/balance-general/", params={"fecha_corte": "2026-12-31"}).json()
    assert despues["balanceado"] is True
    # Ahora la utilidad vive en patrimonio, no "flotando": si el balance
    # general no incluyera los asientos de cierre al calcularlo, contaría 450
    # dos veces y el patrimonio daría 5900.
    assert Decimal(despues["resultado_acumulado"]) == Decimal("0")
    assert Decimal(despues["total_patrimonio"]) == Decimal("5450.00")
    assert Decimal(despues["total_activo"]) == Decimal(antes["total_activo"])
    assert Decimal(despues["total_patrimonio"]) == Decimal(antes["total_patrimonio"])


def test_estado_resultados_ignora_el_asiento_de_cierre(
    client: TestClient, plan_cuentas: dict[str, Cuenta]
) -> None:
    _operacion_del_ejercicio(client, plan_cuentas)
    client.post(
        "/api/v1/cierres/",
        json={"fecha_cierre": "2026-12-31", "cuenta_resultado_id": plan_cuentas["capital"].id},
    )

    # El ejercicio cerrado debe seguir mostrando lo que pasó, no ceros.
    er = client.get(
        "/api/v1/estado-resultados/",
        params={"fecha_desde": "2026-01-01", "fecha_hasta": "2026-12-31"},
    ).json()
    assert Decimal(er["total_ingresos"]) == Decimal("1000.00")
    assert Decimal(er["total_costos"]) == Decimal("400.00")
    assert Decimal(er["total_gastos"]) == Decimal("150.00")
    assert Decimal(er["utilidad_neta"]) == Decimal("450.00")


def test_segundo_cierre_solo_toma_la_actividad_posterior(
    client: TestClient, plan_cuentas: dict[str, Cuenta]
) -> None:
    _operacion_del_ejercicio(client, plan_cuentas)
    primero = client.post(
        "/api/v1/cierres/",
        json={"fecha_cierre": "2026-12-31", "cuenta_resultado_id": plan_cuentas["capital"].id},
    ).json()
    assert Decimal(primero["utilidad_neta"]) == Decimal("450.00")

    # Ejercicio siguiente: una venta de 700 y un gasto de 200 -> 500.
    _crear_asiento(client, "2027-02-01", plan_cuentas["caja"].id, plan_cuentas["ventas"].id, "700")
    _crear_asiento(
        client, "2027-05-01", plan_cuentas["gastos_admin"].id, plan_cuentas["caja"].id, "200"
    )

    segundo = client.post(
        "/api/v1/cierres/",
        json={"fecha_cierre": "2027-12-31", "cuenta_resultado_id": plan_cuentas["capital"].id},
    ).json()
    # No vuelve a cerrar los 450 del ejercicio anterior.
    assert Decimal(segundo["utilidad_neta"]) == Decimal("500.00")

    balance = client.get(
        "/api/v1/balance-general/", params={"fecha_corte": "2027-12-31"}
    ).json()
    assert balance["balanceado"] is True
    assert Decimal(balance["total_patrimonio"]) == Decimal("5950.00")  # 5000 + 450 + 500


def test_cierre_con_perdida_debita_patrimonio(
    client: TestClient, plan_cuentas: dict[str, Cuenta]
) -> None:
    _crear_asiento(client, "2026-01-01", plan_cuentas["caja"].id, plan_cuentas["capital"].id, "5000")
    _crear_asiento(client, "2026-03-01", plan_cuentas["caja"].id, plan_cuentas["ventas"].id, "100")
    _crear_asiento(
        client, "2026-04-01", plan_cuentas["gastos_admin"].id, plan_cuentas["caja"].id, "300"
    )

    cierre = client.post(
        "/api/v1/cierres/",
        json={"fecha_cierre": "2026-12-31", "cuenta_resultado_id": plan_cuentas["capital"].id},
    ).json()
    assert Decimal(cierre["utilidad_neta"]) == Decimal("-200.00")

    balance = client.get(
        "/api/v1/balance-general/", params={"fecha_corte": "2026-12-31"}
    ).json()
    assert balance["balanceado"] is True
    assert Decimal(balance["total_patrimonio"]) == Decimal("4800.00")  # 5000 - 200


def test_cierre_con_resultado_exactamente_cero(
    client: TestClient, plan_cuentas: dict[str, Cuenta]
) -> None:
    # Sin línea de resultado el asiento igual debe balancear (y no violar el
    # CHECK que exige débito o crédito > 0 en cada movimiento).
    _crear_asiento(client, "2026-03-01", plan_cuentas["caja"].id, plan_cuentas["ventas"].id, "300")
    _crear_asiento(
        client, "2026-04-01", plan_cuentas["gastos_admin"].id, plan_cuentas["caja"].id, "300"
    )

    r = client.post(
        "/api/v1/cierres/",
        json={"fecha_cierre": "2026-12-31", "cuenta_resultado_id": plan_cuentas["capital"].id},
    )
    assert r.status_code == 201, r.text
    assert Decimal(r.json()["utilidad_neta"]) == Decimal("0")

    balance = client.get("/api/v1/balance-comprobacion/").json()
    assert balance["balanceado"] is True


def test_el_asiento_de_cierre_queda_marcado_y_auditado(
    client: TestClient, plan_cuentas: dict[str, Cuenta]
) -> None:
    from tests.conftest import TEST_USER_EMAIL

    _operacion_del_ejercicio(client, plan_cuentas)
    cierre = client.post(
        "/api/v1/cierres/",
        json={"fecha_cierre": "2026-12-31", "cuenta_resultado_id": plan_cuentas["capital"].id},
    ).json()

    asiento = client.get(f"/api/v1/asientos/{cierre['asiento_id']}").json()
    assert asiento["usuario_email"] == TEST_USER_EMAIL
    assert "Cierre de ejercicio" in asiento["descripcion"]

    total_debitos = sum(Decimal(m["debito"]) for m in asiento["movimientos"])
    total_creditos = sum(Decimal(m["credito"]) for m in asiento["movimientos"])
    assert total_debitos == total_creditos


def test_no_se_puede_cerrar_dos_veces_la_misma_fecha(
    client: TestClient, plan_cuentas: dict[str, Cuenta]
) -> None:
    _operacion_del_ejercicio(client, plan_cuentas)
    payload = {"fecha_cierre": "2026-12-31", "cuenta_resultado_id": plan_cuentas["capital"].id}
    assert client.post("/api/v1/cierres/", json=payload).status_code == 201

    r = client.post("/api/v1/cierres/", json=payload)
    assert r.status_code == 409


def test_cierre_con_fecha_anterior_al_ultimo_es_rechazado(
    client: TestClient, plan_cuentas: dict[str, Cuenta]
) -> None:
    _operacion_del_ejercicio(client, plan_cuentas)
    client.post(
        "/api/v1/cierres/",
        json={"fecha_cierre": "2026-12-31", "cuenta_resultado_id": plan_cuentas["capital"].id},
    )
    r = client.post(
        "/api/v1/cierres/",
        json={"fecha_cierre": "2026-06-30", "cuenta_resultado_id": plan_cuentas["capital"].id},
    )
    assert r.status_code == 409


def test_cuenta_resultado_debe_ser_de_patrimonio(
    client: TestClient, plan_cuentas: dict[str, Cuenta]
) -> None:
    _operacion_del_ejercicio(client, plan_cuentas)
    r = client.post(
        "/api/v1/cierres/",
        json={"fecha_cierre": "2026-12-31", "cuenta_resultado_id": plan_cuentas["caja"].id},
    )
    assert r.status_code == 400
    assert "patrimonio" in r.json()["detail"]


def test_cerrar_sin_actividad_es_400(
    client: TestClient, plan_cuentas: dict[str, Cuenta]
) -> None:
    r = client.post(
        "/api/v1/cierres/",
        json={"fecha_cierre": "2026-12-31", "cuenta_resultado_id": plan_cuentas["capital"].id},
    )
    assert r.status_code == 400


def test_solo_admin_puede_cerrar(
    client: TestClient, headers_para, plan_cuentas: dict[str, Cuenta]
) -> None:
    _operacion_del_ejercicio(client, plan_cuentas)
    payload = {"fecha_cierre": "2026-12-31", "cuenta_resultado_id": plan_cuentas["capital"].id}

    contador = headers_para("contador")
    assert client.post("/api/v1/cierres/", json=payload, headers=contador).status_code == 403

    lector = headers_para("lector")
    assert client.post("/api/v1/cierres/", json=payload, headers=lector).status_code == 403

    # El admin sí, y el contador puede consultar la lista.
    assert client.post("/api/v1/cierres/", json=payload).status_code == 201
    assert client.get("/api/v1/cierres/", headers=contador).status_code == 200
