import pytest
from fastapi.testclient import TestClient

from app.main import FRONTEND_DIST

# El bundle está gitignoreado: en CI (que solo corre el backend) y en un clon
# limpio no existe, y estas comprobaciones no aplican.
pytestmark = pytest.mark.skipif(
    not FRONTEND_DIST.is_dir(), reason="no hay build del frontend (frontend/dist)"
)


def test_raiz_devuelve_el_index(raw_client: TestClient) -> None:
    r = raw_client.get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")


def test_ruta_de_react_router_devuelve_el_index(raw_client: TestClient) -> None:
    # Una ruta que solo existe del lado del cliente: al recargar la página
    # el backend tiene que devolver el index, no un 404.
    r = raw_client.get("/asientos")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")


def test_api_inexistente_sigue_dando_404_json(raw_client: TestClient) -> None:
    # No debe caer en el fallback de la SPA: el cliente espera JSON acá.
    r = raw_client.get("/api/v1/no-existe")
    assert r.status_code == 404
    assert "html" not in r.headers["content-type"]


def test_endpoints_de_la_api_tienen_prioridad_sobre_la_spa(raw_client: TestClient) -> None:
    assert raw_client.get("/health").json() == {"status": "ok"}
    assert raw_client.get("/openapi.json").status_code == 200
    # Un endpoint protegido debe seguir dando 401, no el index.
    assert raw_client.get("/api/v1/cuentas/").status_code == 401


def test_no_permite_salir_del_directorio_del_bundle(raw_client: TestClient) -> None:
    # Path traversal: debe caer en el fallback (index), nunca servir un
    # archivo de fuera de frontend/dist.
    r = raw_client.get("/../../etc/passwd")
    assert r.status_code == 200
    assert "root:" not in r.text
