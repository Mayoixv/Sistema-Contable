from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import crud
from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.models.cuenta import Cuenta, TipoCuenta
from app.schemas.cuenta import CuentaCreate


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    # SQLite en memoria: rápido y suficiente para probar lógica de la app.
    # StaticPool comparte la misma conexión para que la BD "en memoria"
    # persista entre queries dentro del mismo test.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _activar_fk(dbapi_connection, connection_record) -> None:  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "contrasena-de-prueba"


@pytest.fixture()
def raw_client(db_session: Session) -> Generator[TestClient, None, None]:
    """Cliente sin token, para probar el flujo de autenticación en sí."""

    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def client(raw_client: TestClient) -> TestClient:
    """Cliente autenticado (usuario de prueba registrado + token en headers),
    usado por defecto en el resto de la suite ya que todo /api/v1 (salvo
    /auth) exige sesión iniciada."""
    raw_client.post(
        "/api/v1/auth/registrar",
        json={"email": TEST_USER_EMAIL, "nombre": "Usuario de prueba", "password": TEST_USER_PASSWORD},
    )
    login = raw_client.post(
        "/api/v1/auth/login",
        data={"username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    token = login.json()["access_token"]
    raw_client.headers.update({"Authorization": f"Bearer {token}"})
    return raw_client


@pytest.fixture()
def plan_cuentas(db_session: Session) -> dict[str, Cuenta]:
    """Un plan de cuentas mínimo pero completo (activo/pasivo/patrimonio/
    ingreso/costo/gasto), todas cuentas de detalle listas para recibir
    movimientos, reutilizable entre módulos de test."""

    def _crear(codigo: str, nombre: str, tipo: TipoCuenta) -> Cuenta:
        return crud.cuenta.create(
            db_session, obj_in=CuentaCreate(codigo=codigo, nombre=nombre, tipo=tipo)
        )

    return {
        "caja": _crear("1.1.01", "Caja", TipoCuenta.ACTIVO),
        "banco": _crear("1.1.02", "Banco", TipoCuenta.ACTIVO),
        "proveedores": _crear("2.1.01", "Proveedores", TipoCuenta.PASIVO),
        "capital": _crear("3.1.01", "Capital social", TipoCuenta.PATRIMONIO),
        "ventas": _crear("4.1.01", "Ventas", TipoCuenta.INGRESO),
        "costo_ventas": _crear("5.1.01", "Costo de ventas", TipoCuenta.COSTO),
        "gastos_admin": _crear("6.1.01", "Gastos de administración", TipoCuenta.GASTO),
    }
