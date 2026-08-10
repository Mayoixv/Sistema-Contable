from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse

from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Salud"])
def health() -> dict[str, str]:
    return {"status": "ok"}


# Bundle compilado del frontend (lo genera `npm run build` en frontend/).
FRONTEND_DIST = (Path(__file__).resolve().parent.parent / "frontend" / "dist").resolve()


def _montar_frontend() -> None:
    """Sirve la SPA desde el mismo origen que la API.

    El cliente arma las URLs con `window.location.origin` (ver
    frontend/src/api/client.js), así que servir todo desde un único origen
    evita tener que configurar CORS. En desarrollo esto no se usa: el dev
    server de Vite proxea /api al backend (ver frontend/vite.config.js).

    Se registra al final para que las rutas de la API, /health y las de
    documentación (/docs, /openapi.json) tengan prioridad: Starlette
    resuelve por orden de registro.
    """

    @app.get("/{ruta:path}", include_in_schema=False)
    def servir_spa(ruta: str) -> FileResponse:
        # Sin este corte, una ruta /api inexistente devolvería el index.html
        # con 200 en vez de un 404, y el cliente recibiría HTML donde espera
        # JSON — un error mucho más difícil de diagnosticar.
        if ruta.startswith("api/"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

        archivo = (FRONTEND_DIST / ruta).resolve()
        # is_relative_to corta el path traversal (?ruta=../../etc/passwd).
        if ruta and archivo.is_file() and archivo.is_relative_to(FRONTEND_DIST):
            return FileResponse(archivo)

        # Cualquier otra ruta es de React Router: se devuelve el index y el
        # ruteo lo resuelve el cliente.
        return FileResponse(FRONTEND_DIST / "index.html")


# Si no hay build (desarrollo con Vite, o CI que solo corre el backend) la
# app funciona igual, solo que sin servir la interfaz.
if FRONTEND_DIST.is_dir():
    _montar_frontend()
