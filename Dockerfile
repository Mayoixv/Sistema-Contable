# --- Etapa 1: compilar la interfaz web ---
FROM node:22-slim AS frontend

WORKDIR /frontend

# Se copian primero los manifiestos: mientras no cambien, Docker reutiliza
# la capa de node_modules y no reinstala en cada build.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


# --- Etapa 2: la API, que además sirve el bundle compilado ---
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# El dist se toma de la etapa anterior, no del host: así el build no depende
# de que alguien haya corrido `npm run build` localmente.
COPY --from=frontend /frontend/dist ./frontend/dist

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
