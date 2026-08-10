import pytest
from pydantic import ValidationError

from app.core.config import SECRET_KEY_DESARROLLO, Settings

# _env_file=None evita que el .env del desarrollador se cuele y cambie el
# resultado según la máquina donde corran los tests.
SIN_ENV = {"_env_file": None}


def test_desarrollo_permite_la_clave_de_ejemplo() -> None:
    ajustes = Settings(ENTORNO="desarrollo", **SIN_ENV)
    assert ajustes.SECRET_KEY == SECRET_KEY_DESARROLLO
    assert ajustes.es_produccion is False


def test_produccion_rechaza_la_clave_de_ejemplo() -> None:
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(ENTORNO="produccion", SECRET_KEY=SECRET_KEY_DESARROLLO, **SIN_ENV)


def test_produccion_acepta_una_clave_propia() -> None:
    ajustes = Settings(ENTORNO="produccion", SECRET_KEY="a" * 64, **SIN_ENV)
    assert ajustes.es_produccion is True


@pytest.mark.parametrize("valor", ["produccion", "PRODUCCION", " Produccion "])
def test_el_entorno_no_depende_de_mayusculas_ni_espacios(valor: str) -> None:
    # Si "PRODUCCION" no se reconociera, la validación se saltearía en
    # silencio y el despliegue quedaría con la clave de ejemplo.
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(ENTORNO=valor, SECRET_KEY=SECRET_KEY_DESARROLLO, **SIN_ENV)
