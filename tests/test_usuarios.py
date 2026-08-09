from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.cuenta import Cuenta


def _id_de(client: TestClient, email: str) -> int:
    usuarios = client.get('/api/v1/usuarios/').json()
    return next(u['id'] for u in usuarios if u['email'] == email)


def test_admin_cambia_el_rol_de_otro(client: TestClient, headers_para) -> None:
    headers_para('contador')
    contador_id = _id_de(client, 'contador@example.com')

    r = client.patch(f'/api/v1/usuarios/{contador_id}', json={'rol': 'lector'})
    assert r.status_code == 200
    assert r.json()['rol'] == 'lector'


def test_admin_desactiva_a_otro_y_le_corta_el_acceso(client: TestClient, headers_para) -> None:
    contador = headers_para('contador')
    contador_id = _id_de(client, 'contador@example.com')
    assert client.get('/api/v1/cuentas/', headers=contador).status_code == 200

    assert client.patch(f'/api/v1/usuarios/{contador_id}', json={'activo': False}).status_code == 200

    # El token sigue siendo válido criptográficamente, pero get_current_user
    # rechaza a los usuarios inactivos.
    assert client.get('/api/v1/cuentas/', headers=contador).status_code == 401


def test_no_puede_cambiarse_el_rol_a_si_mismo(client: TestClient) -> None:
    from tests.conftest import TEST_USER_EMAIL

    propio_id = _id_de(client, TEST_USER_EMAIL)
    r = client.patch(f'/api/v1/usuarios/{propio_id}', json={'rol': 'lector'})
    assert r.status_code == 400


def test_no_puede_eliminarse_a_si_mismo(client: TestClient) -> None:
    from tests.conftest import TEST_USER_EMAIL

    propio_id = _id_de(client, TEST_USER_EMAIL)
    assert client.delete(f'/api/v1/usuarios/{propio_id}').status_code == 400


def test_siempre_queda_al_menos_un_admin_activo(client: TestClient, headers_para) -> None:
    """El sistema no puede quedarse sin administración.

    No hace falta contar admins para garantizarlo: quien ejecuta la acción es
    siempre un admin activo (`requiere_admin`) y no puede degradarse,
    desactivarse ni eliminarse a sí mismo, así que después de cualquier
    operación sigue en pie al menos él. Este test recorre las tres vías por
    las que un admin podría intentar quedar fuera.
    """
    from tests.conftest import TEST_USER_EMAIL

    propio_id = _id_de(client, TEST_USER_EMAIL)
    otro_admin = headers_para('admin', email='admin2@example.com')
    otro_id = _id_de(client, 'admin2@example.com')

    # Las tres vías de auto-exclusión están cerradas.
    assert client.patch(f'/api/v1/usuarios/{propio_id}', json={'rol': 'lector'}).status_code == 400
    assert client.patch(f'/api/v1/usuarios/{propio_id}', json={'activo': False}).status_code == 400
    assert client.delete(f'/api/v1/usuarios/{propio_id}').status_code == 400

    # Un admin sí puede degradar a otro, y el sistema conserva un admin activo.
    assert client.patch(f'/api/v1/usuarios/{otro_id}', json={'rol': 'contador'}).status_code == 200
    admins_activos = [
        u for u in client.get('/api/v1/usuarios/').json() if u['rol'] == 'admin' and u['activo']
    ]
    assert len(admins_activos) >= 1
    assert admins_activos[0]['email'] == TEST_USER_EMAIL

    # Y el degradado ya no puede administrar.
    assert client.get('/api/v1/usuarios/', headers=otro_admin).status_code == 403


def test_eliminar_usuario_sin_historial(client: TestClient, headers_para) -> None:
    headers_para('lector')
    lector_id = _id_de(client, 'lector@example.com')

    assert client.delete(f'/api/v1/usuarios/{lector_id}').status_code == 204
    emails = {u['email'] for u in client.get('/api/v1/usuarios/').json()}
    assert 'lector@example.com' not in emails


def test_no_se_elimina_un_usuario_con_asientos(
    client: TestClient, headers_para, plan_cuentas: dict[str, Cuenta]
) -> None:
    contador = headers_para('contador')
    contador_id = _id_de(client, 'contador@example.com')

    r = client.post(
        '/api/v1/asientos/',
        json={
            'fecha': '2026-01-01',
            'descripcion': 'Asiento del contador',
            'movimientos': [
                {'cuenta_id': plan_cuentas['caja'].id, 'debito': '100'},
                {'cuenta_id': plan_cuentas['capital'].id, 'credito': '100'},
            ],
        },
        headers=contador,
    )
    assert r.status_code == 201

    r = client.delete(f'/api/v1/usuarios/{contador_id}')
    assert r.status_code == 409
    assert 'Desactivalo' in r.json()['detail']

    # Desactivar sí funciona, y conserva la autoría del asiento.
    assert client.patch(f'/api/v1/usuarios/{contador_id}', json={'activo': False}).status_code == 200
    asiento = client.get('/api/v1/asientos/').json()['items'][0]
    assert asiento['usuario_email'] == 'contador@example.com'


def test_contador_y_lector_no_pueden_administrar_usuarios(
    client: TestClient, headers_para
) -> None:
    contador = headers_para('contador')
    lector = headers_para('lector')
    lector_id = _id_de(client, 'lector@example.com')

    assert client.patch(
        f'/api/v1/usuarios/{lector_id}', json={'rol': 'admin'}, headers=contador
    ).status_code == 403
    assert client.delete(f'/api/v1/usuarios/{lector_id}', headers=lector).status_code == 403


def test_usuario_inexistente_404(client: TestClient) -> None:
    assert client.patch('/api/v1/usuarios/9999', json={'rol': 'lector'}).status_code == 404
    assert client.delete('/api/v1/usuarios/9999').status_code == 404
