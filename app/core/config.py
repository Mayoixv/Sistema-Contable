from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Valor centinela: sirve para desarrollo, pero al estar publicado en el repo
# cualquiera podría firmarse un token de admin. `ENTORNO=produccion` lo
# rechaza (ver _exigir_secret_key_propia).
SECRET_KEY_DESARROLLO = "dev-secret-key-cambiar-en-produccion"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Sistema Contable"
    API_V1_PREFIX: str = "/api/v1"
    DATABASE_URL: str = (
        "postgresql+psycopg2://contable_user:contable_pass@localhost:5432/contable_db"
    )

    # "desarrollo" o "produccion". En producción la app se niega a arrancar
    # con la clave de ejemplo.
    ENTORNO: str = "desarrollo"

    # Clave para firmar los JWT. En producción hay que definirla por variable
    # de entorno con un valor largo y aleatorio (`openssl rand -hex 32`).
    SECRET_KEY: str = SECRET_KEY_DESARROLLO
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 horas

    @property
    def es_produccion(self) -> bool:
        return self.ENTORNO.strip().lower() == "produccion"

    @model_validator(mode="after")
    def _exigir_secret_key_propia(self) -> "Settings":
        """Falla al arrancar antes que servir con una clave conocida.

        Un despliegue con la clave de ejemplo permite que cualquiera que
        haya visto el repositorio se fabrique un token de admin válido. Es
        preferible que el proceso no levante a que levante inseguro.
        """
        if self.es_produccion and self.SECRET_KEY == SECRET_KEY_DESARROLLO:
            raise ValueError(
                "SECRET_KEY tiene el valor de ejemplo del repositorio y ENTORNO=produccion. "
                "Definí una clave propia, por ejemplo: SECRET_KEY=$(openssl rand -hex 32)"
            )
        return self


settings = Settings()
