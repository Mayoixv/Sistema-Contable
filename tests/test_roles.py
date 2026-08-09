import re
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.cuenta import Cuenta
from app.models.usuario import RolUsuario, Usuario

NUEVA_CUENTA = {"codigo": "1.1.99", "nombre": "Cuenta de prueba", "tipo": "activo"}


def test_primer_usuario_del_sistema_es_admin(raw_client: TestClient) -> None:
    r = raw_client.post(
        "/api/v1/auth/registrar",
        json={"email": "primero@example.com", "nombre": "Primero", "password": "password123"},
    )
    assert r.status_code == 201
    assert r.json()["rol"] == "admin"


def test_bootstrap_ignora_el_rol_pedido(raw_client: TestClient) -> None:
    # Si el primer usuario pudiera crearse como 'lector', el sistema quedaría
    # sin ningún admin y sin forma de crear uno.
    r = raw_client.post(
        "/api/v1/auth/registrar",
        json={
            "email": "primero@example.com",
            "nombre": "Primero",
            "password": "password123",
            "rol": "lector",
        },
    )
    assert r.status_code == 201
    assert r.json()["rol"] == "admin"


def test_registro_anonimo_bloqueado_una_vez_que_hay_usuarios(
    raw_client: TestClient,
) -> None:
    raw_client.post(
        "/api/v1/auth/registrar",
        json={"email": "primero@example.com", "nombre": "Primero", "password": "password123"},
    )
    r = raw_client.post(
        "/api/v1/auth/registrar",
        json={"email": "colado@example.com", "nombre": "Colado", "password": "password123"},
    )
    assert r.status_code == 401


def test_admin_crea_usuario_contador_por_defecto(client: TestClient) -> None:
    r = client.post(
        "/api/v1/auth/registrar",
        json={"email": "nuevo@example.com", "nombre": "Nuevo", "password": "password123"},
    )
    assert r.status_code == 201
    assert r.json()["rol"] == "contador"


def test_admin_puede_fijar_el_rol(client: TestClient) -> None:
    r = client.post(
        "/api/v1/auth/registrar",
        json={
            "email": "solo-lectura@example.com",
            "nombre": "Lector",
            "password": "password123",
            "rol": "lector",
        },
    )
    assert r.status_code == 201
    assert r.json()["rol"] == "lector"


def test_contador_no_puede_crear_usuarios(client: TestClient, headers_para) -> None:
    contador = headers_para("contador")
    r = client.post(
        "/api/v1/auth/registrar",
        json={"email": "otro@example.com", "nombre": "Otro", "password": "password123"},
        headers=contador,
    )
    assert r.status_code == 403


def test_contador_puede_escribir_contabilidad(client: TestClient, headers_para) -> None:
    contador = headers_para("contador")
    assert client.post("/api/v1/cuentas/", json=NUEVA_CUENTA, headers=contador).status_code == 201


def test_lector_puede_leer_pero_no_escribir(
    client: TestClient, headers_para, plan_cuentas: dict[str, Cuenta]
) -> None:
    lector = headers_para("lector")

    assert client.get("/api/v1/cuentas/", headers=lector).status_code == 200
    assert client.get("/api/v1/balance-comprobacion/", headers=lector).status_code == 200

    r = client.post("/api/v1/cuentas/", json=NUEVA_CUENTA, headers=lector)
    assert r.status_code == 403
    assert "lector" in r.json()["detail"]


def test_lector_no_puede_cargar_ni_reversar_asientos(
    client: TestClient, headers_para, plan_cuentas: dict[str, Cuenta]
) -> None:
    lector = headers_para("lector")
    asiento_payload = {
        "fecha": "2026-01-01",
        "descripcion": "Intento de lector",
        "movimientos": [
            {"cuenta_id": plan_cuentas["caja"].id, "debito": "100"},
            {"cuenta_id": plan_cuentas["capital"].id, "credito": "100"},
        ],
    }
    assert client.post("/api/v1/asientos/", json=asiento_payload, headers=lector).status_code == 403

    # El admin sí puede, y el lector tampoco puede reversar ni borrar.
    creado = client.post("/api/v1/asientos/", json=asiento_payload).json()
    assert (
        client.post(f"/api/v1/asientos/{creado['id']}/reversar", headers=lector).status_code == 403
    )
    assert client.delete(f"/api/v1/asientos/{creado['id']}", headers=lector).status_code == 403


def test_lector_no_puede_modificar_ni_borrar_cuentas(
    client: TestClient, headers_para, plan_cuentas: dict[str, Cuenta]
) -> None:
    lector = headers_para("lector")
    cuenta_id = plan_cuentas["caja"].id

    assert (
        client.patch(
            f"/api/v1/cuentas/{cuenta_id}", json={"nombre": "Otro"}, headers=lector
        ).status_code
        == 403
    )
    assert client.delete(f"/api/v1/cuentas/{cuenta_id}", headers=lector).status_code == 403


def test_el_rol_se_guarda_como_nombre_del_enum_no_como_valor(
    client: TestClient, db_session: Session
) -> None:
    """SQLAlchemy persiste el NOMBRE del miembro ('ADMIN'), no su valor
    ('admin'). Escribir el valor deja filas que el ORM no puede leer, y es
    un error fácil de cometer desde SQL crudo (una migración, un fix a mano).
    """
    guardado = db_session.execute(text("SELECT rol FROM usuarios LIMIT 1")).scalar_one()
    assert guardado == RolUsuario.ADMIN.name == "ADMIN"

    # Y una fila escrita con esa forma se lee bien desde el ORM.
    db_session.execute(
        text(
            "INSERT INTO usuarios (email, nombre, hashed_password, rol, activo) "
            "VALUES ('crudo@example.com', 'Crudo', 'x', 'LECTOR', 1)"
        )
    )
    usuario = db_session.scalar(select(Usuario).where(Usuario.email == "crudo@example.com"))
    assert usuario.rol is RolUsuario.LECTOR


def test_migracion_de_roles_usa_nombres_de_enum_validos() -> None:
    """Los tests crean el schema con metadata.create_all, así que nunca
    ejecutan las migraciones: un literal mal escrito ahí pasaría inadvertido
    hasta correr contra la base real. Esto revisa los literales de rol de la
    migración contra el enum."""
    migracion = Path(__file__).resolve().parents[1] / (
        "alembic/versions/0006_add_rol_usuarios.py"
    )
    contenido = migracion.read_text()
    nombres_validos = {r.name for r in RolUsuario}

    literales = set(re.findall(r"rol = '([^']+)'", contenido))
    literales |= set(re.findall(r'server_default="([^"]+)"', contenido))

    assert literales, "no se encontraron literales de rol en la migración"
    assert literales <= nombres_validos, (
        f"la migración usa literales que el ORM no puede leer: {literales - nombres_validos}"
    )


def test_listar_usuarios_es_solo_para_admin(client: TestClient, headers_para) -> None:
    contador = headers_para('contador')
    lector = headers_para('lector')

    r = client.get('/api/v1/usuarios/')
    assert r.status_code == 200
    emails = {u['email'] for u in r.json()}
    assert {'contador@example.com', 'lector@example.com'} <= emails
    assert all('hashed_password' not in u for u in r.json())

    assert client.get('/api/v1/usuarios/', headers=contador).status_code == 403
    assert client.get('/api/v1/usuarios/', headers=lector).status_code == 403


def test_sin_token_sigue_siendo_401_no_403(raw_client: TestClient) -> None:
    # Distinguir "no iniciaste sesión" (401) de "no tenés permiso" (403).
    raw_client.post(
        "/api/v1/auth/registrar",
        json={"email": "primero@example.com", "nombre": "Primero", "password": "password123"},
    )
    assert raw_client.post("/api/v1/cuentas/", json=NUEVA_CUENTA).status_code == 401
