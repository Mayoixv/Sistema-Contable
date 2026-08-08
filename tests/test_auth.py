from fastapi.testclient import TestClient

from tests.conftest import TEST_USER_EMAIL, TEST_USER_PASSWORD


def test_registrar_y_login(raw_client: TestClient) -> None:
    r = raw_client.post(
        "/api/v1/auth/registrar",
        json={"email": "nueva@example.com", "nombre": "Nueva", "password": "password123"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "nueva@example.com"
    assert "hashed_password" not in data

    r = raw_client.post(
        "/api/v1/auth/login", data={"username": "nueva@example.com", "password": "password123"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_registrar_email_duplicado_409(raw_client: TestClient) -> None:
    payload = {"email": "dup@example.com", "nombre": "Dup", "password": "password123"}
    assert raw_client.post("/api/v1/auth/registrar", json=payload).status_code == 201
    r = raw_client.post("/api/v1/auth/registrar", json=payload)
    assert r.status_code == 409


def test_login_password_incorrecta_401(raw_client: TestClient) -> None:
    raw_client.post(
        "/api/v1/auth/registrar",
        json={"email": "u@example.com", "nombre": "U", "password": "password123"},
    )
    r = raw_client.post(
        "/api/v1/auth/login", data={"username": "u@example.com", "password": "incorrecta"}
    )
    assert r.status_code == 401


def test_login_email_no_distingue_mayusculas(raw_client: TestClient) -> None:
    raw_client.post(
        "/api/v1/auth/registrar",
        json={"email": "Mixta@Example.com", "nombre": "Mixta", "password": "password123"},
    )
    for variante in ("Mixta@Example.com", "mixta@example.com", "MIXTA@EXAMPLE.COM"):
        r = raw_client.post(
            "/api/v1/auth/login", data={"username": variante, "password": "password123"}
        )
        assert r.status_code == 200, f"falló con {variante}"


def test_registrar_mismo_email_en_otra_capitalizacion_es_duplicado(
    raw_client: TestClient,
) -> None:
    primero = {"email": "dup2@example.com", "nombre": "Uno", "password": "password123"}
    assert raw_client.post("/api/v1/auth/registrar", json=primero).status_code == 201

    segundo = {"email": "DUP2@example.com", "nombre": "Dos", "password": "password123"}
    assert raw_client.post("/api/v1/auth/registrar", json=segundo).status_code == 409


def test_login_con_nombre_en_vez_de_email_401(raw_client: TestClient) -> None:
    # Trampa clásica: el campo del formulario OAuth2 se llama "username",
    # pero lo que se espera es el email, no el nombre del usuario.
    raw_client.post(
        "/api/v1/auth/registrar",
        json={"email": "conombre@example.com", "nombre": "Pepe", "password": "password123"},
    )
    r = raw_client.post(
        "/api/v1/auth/login", data={"username": "Pepe", "password": "password123"}
    )
    assert r.status_code == 401


def test_login_usuario_inexistente_401(raw_client: TestClient) -> None:
    r = raw_client.post(
        "/api/v1/auth/login", data={"username": "nadie@example.com", "password": "x"}
    )
    assert r.status_code == 401


def test_endpoint_protegido_sin_token_401(raw_client: TestClient) -> None:
    assert raw_client.get("/api/v1/cuentas/").status_code == 401


def test_endpoint_protegido_con_token_invalido_401(raw_client: TestClient) -> None:
    raw_client.headers.update({"Authorization": "Bearer token-invalido"})
    assert raw_client.get("/api/v1/cuentas/").status_code == 401


def test_me_devuelve_usuario_autenticado(client: TestClient) -> None:
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == TEST_USER_EMAIL


def test_health_no_requiere_auth(raw_client: TestClient) -> None:
    assert raw_client.get("/health").status_code == 200
