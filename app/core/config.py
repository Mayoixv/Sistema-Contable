from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Sistema Contable"
    API_V1_PREFIX: str = "/api/v1"
    DATABASE_URL: str = (
        "postgresql+psycopg2://contable_user:contable_pass@localhost:5432/contable_db"
    )

    # Clave para firmar los JWT. El default solo sirve para desarrollo local;
    # en producción se debe sobreescribir con una clave larga y aleatoria
    # (ej. `openssl rand -hex 32`) vía la variable de entorno SECRET_KEY.
    SECRET_KEY: str = "dev-secret-key-cambiar-en-produccion"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 horas


settings = Settings()
