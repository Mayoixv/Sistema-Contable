# Sistema Contable

[![CI](https://github.com/Mayoixv/Sistema-Contable/actions/workflows/ci.yml/badge.svg)](https://github.com/Mayoixv/Sistema-Contable/actions/workflows/ci.yml)

Sistema de contabilidad por partida doble: API REST con FastAPI +
PostgreSQL + SQLAlchemy + Alembic, e interfaz web en React.

```bash
docker compose up -d --build   # http://localhost:8001
```

Qué cubre:

- **Plan de cuentas** jerárquico, con cuentas sumarias y de detalle.
- **Asientos contables** con validación de partida doble en el schema y en
  la base; no se editan, se **reversan** (queda el error y su corrección).
- **Reportes**: libro mayor, balance de comprobación, estado de resultados
  y balance general, exportables a CSV.
- **Cierre de ejercicio**, que traslada el resultado a patrimonio sin
  romper los reportes del período cerrado.
- **Usuarios con roles** (admin/contador/lector) y auditoría de quién cargó
  cada asiento.

Corren 102 tests de backend (pytest) y 20 de frontend (Vitest) en CI.

## Estructura

```
app/
  core/
    config.py               # Settings (lee .env)
    security.py             # Hash de passwords (bcrypt) y JWT
  db/
    base_class.py           # Base declarativa
    base.py                 # Importa todos los modelos (para Alembic)
    session.py              # engine, SessionLocal, get_db
  models/
    cuenta.py               # Cuenta (plan de cuentas jerárquico)
    asiento.py              # Asiento + MovimientoContable (partida doble)
    usuario.py              # Usuario + RolUsuario
    cierre.py               # Cierre de ejercicio
  schemas/                  # Un módulo por recurso/reporte
  crud/
    cuenta.py, asiento.py, usuario.py, cierre.py
    agregados.py            # Consulta agregada compartida por los reportes
    libro_mayor.py, balance_comprobacion.py
    estado_resultados.py, balance_general.py
  api/
    deps.py                 # get_db, get_current_user, requiere_rol
    v1/endpoints/           # Un router por recurso/reporte
  utils/csv_export.py       # Exportación de reportes a CSV
  main.py                   # App FastAPI
alembic/versions/           # 0001..0007 (migraciones escritas a mano)
tests/                      # Suite pytest (SQLite en memoria)
```

## Puesta en marcha

### Opción A: Docker Compose (recomendado)

```bash
docker compose up -d --build
```

Levanta el sistema completo — Postgres, la API y la interfaz web — en un
solo paso: `db` espera a pasar su healthcheck (`pg_isready`) antes de que
arranque `api`, y el contenedor de la API corre `alembic upgrade head`
automáticamente antes de `uvicorn` (ver `Dockerfile`, `CMD`) — no hace
falta crear la base ni migrar a mano.

- **Interfaz web: `http://localhost:8001`**
- API: `http://localhost:8001/api/v1` (docs en `/docs`)
- Postgres: `localhost:5433` (puertos 8000/5432 quedan libres para no
  chocar con otros proyectos locales)

No hay un servicio `web` separado: el `Dockerfile` es multi-etapa
(`node:20-slim` compila el frontend, `python:3.12-slim` corre la API) y la
app sirve el bundle desde el mismo origen que la API. Un nginx aparte
habría significado un contenedor más y configurar CORS o un proxy, sin
ganar nada a esta escala. El `npm ci` pasa dentro de la imagen, así que el
build no depende de que hayas corrido `npm run build` en tu máquina.
- Los datos persisten en el volumen nombrado `contable_pgdata` entre
  reinicios; `docker compose down -v` si además querés borrarlos.
- `SECRET_KEY` se puede sobreescribir exportándola antes del `up`
  (`export SECRET_KEY=...`) — si no, usa el default de desarrollo. Para
  levantarlo como producción:
  `ENTORNO=produccion SECRET_KEY=$(openssl rand -hex 32) docker compose up -d`

Para logs: `docker compose logs -f api`. Para bajar todo: `docker compose down`.

> Si ya tenías un Postgres corriendo a mano en el puerto 5433 (por ejemplo
> con `docker run --name contable-db ...`, como se hacía antes de tener
> `docker-compose.yml`), pará ese contenedor primero (`docker stop
> contable-db`) — si no, `docker compose up` va a fallar al intentar
> tomar el mismo puerto. Los datos de ese contenedor viejo no se migran
> solos al volumen de compose.

### Opción B: entorno local (venv + Postgres aparte)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # ajustar DATABASE_URL

createdb contable_db   # o crear la DB manualmente en PostgreSQL

alembic upgrade head
uvicorn app.main:app --reload
```

Docs interactivas: `http://localhost:8000/docs`

## Interfaz web (`frontend/`)

React + Vite. Para **usarla**, alcanza con `docker compose up` y entrar a
`http://localhost:8001` (ver arriba). Lo de acá abajo es para
**desarrollarla**, con hot-reload: son dos procesos, la API en `8001` y el
dev server en `5173`.

```bash
cd frontend
npm install
npm run dev     # http://localhost:5173
```

En producción, en cambio, no hay dev server: FastAPI sirve el bundle
compilado (`frontend/dist`) y cae en `index.html` para cualquier ruta que
no sea de la API, porque el ruteo es del lado del cliente
(`BrowserRouter`) y al recargar `/asientos` el backend tiene que devolver
el index en vez de un 404. Las rutas bajo `/api/` quedan excluidas de ese
fallback a propósito: si no, un endpoint mal escrito devolvería HTML con
`200` donde el cliente espera JSON, que es un error bastante más difícil
de diagnosticar que un `404`.

**No hace falta configurar CORS.** El dev server de Vite proxea `/api` y
`/health` al backend (ver `vite.config.js`), así que el navegador ve un solo
origen; y en producción FastAPI sirve el bundle ya compilado, con lo cual
tampoco hay cruce de orígenes. Es un ajuste de tres líneas que evita tener
que abrir la API a otro dominio.

Estructura:

```
frontend/src/
  api/client.js         # fetch con el token, descarga de CSV, errores del backend
  auth/contexto.js      # Context + hook useAuth
  auth/AuthContext.jsx  # AuthProvider (sesión, rol del usuario)
  components/           # FiltrosFecha
  hooks/useCargar.js    # carga con estados de cargando/error
  pages/                # Login, PlanCuentas, LibroMayor, Asientos, reportes, Cierres
  formato.js            # formateo de montos
```

Pantallas: login, plan de cuentas (árbol, con alta/edición/borrado),
asientos (alta con partida doble en vivo, filtros, paginación, reversión
con fecha elegible y borrado), libro mayor, balance de comprobación, estado
de resultados, balance general, cierre de ejercicio y usuarios (solo
admin). Los cuatro reportes se pueden bajar en CSV. La interfaz cubre toda
la API.

Al editar una cuenta solo se dejan cambiar `codigo`, `nombre`,
`descripcion` y `activa`, aunque el `PATCH` acepte más: cambiar el `tipo` o
la `naturaleza` de una cuenta que ya tiene movimientos reclasificaría en
silencio los asientos históricos y alteraría reportes de períodos ya
cerrados. Para eso conviene crear una cuenta nueva.

Detalles de diseño:

- El token va en `localStorage`. Es lo habitual en una SPA y encaja con el
  JWT que ya expone la API, pero conviene saber que es vulnerable a XSS: una
  cookie `HttpOnly` sería más segura, a cambio de tener que agregar
  autenticación por cookie en el backend (hoy solo entiende el header
  `Authorization`).
- El 401 se maneja en un solo lugar (`onSesionExpirada` en el cliente): si el
  token venció, se cierra la sesión sin que cada pantalla tenga que
  ocuparse.
- Los montos llegan como string (`Decimal` serializado) para no perder
  precisión, y se convierten a número **solo para mostrarlos**.
- En la carga de asientos, el control de partida doble compara **centavos
  enteros**, no floats: en punto flotante `0.10 + 0.20` da
  `0.30000000000000004`, y un asiento perfectamente balanceado se marcaría
  como descuadrado.
- La descarga de CSV se hace con `fetch` + blob, no con un `<a href>`: la
  API exige el header `Authorization`, que el navegador **no** manda en una
  navegación normal, así que un enlace común devolvería 401.
- La UI oculta las acciones de escritura si el rol no alcanza, pero eso es
  comodidad, no seguridad: quien manda la petición igual choca con el `403`
  del backend.

## Autenticación

Toda la API bajo `/api/v1` exige un JWT, salvo `/api/v1/auth/*` y `/health`.

```
POST /api/v1/auth/registrar   {"email", "nombre", "password", "rol"?}  -> 201 UsuarioRead
POST /api/v1/auth/login       form-urlencoded: username=<email>&password=<password>  -> {"access_token", "token_type"}
GET  /api/v1/auth/me          (con Authorization: Bearer <token>)  -> UsuarioRead
GET    /api/v1/usuarios/       (solo admin)  -> [UsuarioRead]
PATCH  /api/v1/usuarios/{id}   (solo admin)  {"rol"?, "activo"?}
DELETE /api/v1/usuarios/{id}   (solo admin)
```

Sobre la administración de usuarios:

- **Un admin no puede degradarse, desactivarse ni eliminarse a sí mismo**
  (`400`). No es una comodidad: es lo que garantiza que el sistema nunca se
  quede sin admin activo. Como `requiere_admin` asegura que quien ejecuta la
  acción es un admin activo y el objetivo siempre es otro usuario, después
  de cualquier operación queda en pie al menos quien la ejecutó. Importa
  porque no habría recuperación posible: sin admins nadie puede crear
  usuarios, y el registro público solo se reabre si no queda **ningún**
  usuario.
- **Eliminar un usuario con historial contable se rechaza** (`409`, por el
  `ON DELETE RESTRICT` de `asientos`/`cierres`): borrarlo destruiría la
  trazabilidad de quién cargó qué. Para esos casos está `activo=false`, que
  le corta el acceso conservando la autoría.

`/login` usa `OAuth2PasswordRequestForm` (por eso es form-urlencoded y no
JSON, y el campo se llama `username` aunque en este sistema es el email) —
es el estándar que además hace que el botón "Authorize" de `/docs`
funcione solo, sin tener que pegar el token a mano.

> **En `username` va el email, no el nombre del usuario.** Es la confusión
> más fácil de cometer al probar desde `/docs`, y el síntoma es un `401`
> idéntico al de contraseña incorrecta. El `summary` del endpoint lo aclara
> en la documentación interactiva.

### Probar desde `/docs`

Hacer "Try it out" sobre `POST /auth/login` **no** deja logueada la sesión
de Swagger: solo muestra el token. Para que el resto de los endpoints
funcionen hay que usar el botón verde **Authorize**, que ofrece dos formas
(cualquiera sirve, son el mismo header `Authorization: Bearer <token>`):

- **OAuth2PasswordBearer** — email + contraseña; Swagger hace el login y
  guarda el token solo.
- **HTTPBearer** — pegar directamente un token ya obtenido (por ejemplo el
  que devuelve `curl`), sin re-tipear credenciales.

Ambos esquemas se declaran en `app/api/deps.py` con `auto_error=False`, de
modo que fallar uno no corta la petición si el otro la resolvió; el `401`
lo emite `get_current_user` cuando no llegó token por ninguna vía. En el
OpenAPI quedan como alternativas (OR), no como requisitos simultáneos.

Al recargar `/docs` la autorización se pierde y hay que repetirla.

### Roles y permisos

Tres roles (`Usuario.rol`):

| Rol | Puede |
|---|---|
| `admin` | todo, incluido crear usuarios y fijarles el rol |
| `contador` | crear/modificar cuentas y cargar/reversar asientos |
| `lector` | solo consultar (listados y reportes) |

`POST /auth/registrar` es **público solo mientras no exista ningún
usuario**: esa primera alta crea el `admin` inicial (ignorando el `rol` que
se haya pedido — si el primero pudiera ser `lector`, el sistema quedaría
sin administración y sin forma de recuperarla). A partir de ahí el alta
exige un admin autenticado, que sí elige el rol (`contador` por defecto).

La distinción de códigos importa: **401** es "no iniciaste sesión" y
**403** es "iniciaste sesión pero tu rol no alcanza" (el detalle dice qué
rol hace falta y cuál tenés).

> Al persistir enums, SQLAlchemy guarda el **nombre** del miembro
> (`'ADMIN'`), no su valor (`'admin'`) — igual que `cuentas.tipo`. Una
> migración que escriba el valor en minúscula inserta filas que el ORM
> después no puede leer. Como la suite crea el schema con
> `metadata.create_all` y nunca corre las migraciones, ese error no
> aparecería en los tests: por eso hay uno que valida los literales de rol
> de la migración contra el enum.

Notas de diseño:

- El password se hashea con `bcrypt` directo (no `passlib`, para evitar el
  problema conocido de incompatibilidad entre `passlib` y `bcrypt>=4`). El
  límite de 72 bytes de bcrypt se refleja en `UsuarioCreate.password`
  (`max_length=72`).
- El email se normaliza a minúsculas (`_normalizar_email` en
  `crud/usuario.py`) tanto al registrar como al buscar, así el login no
  distingue mayúsculas y `DUP@x.com` se detecta como duplicado de
  `dup@x.com` en lugar de crear dos cuentas distintas.
- El JWT se firma con `SECRET_KEY` (HS256, expira a las
  `ACCESS_TOKEN_EXPIRE_MINUTES`, por defecto 8 horas). El valor por defecto
  en `config.py` **está publicado en este repositorio**, así que sirve solo
  para desarrollo: con él, cualquiera que haya visto el código podría
  firmarse un token de admin. Por eso, con `ENTORNO=produccion` la app
  **se niega a arrancar** si `SECRET_KEY` sigue siendo el de ejemplo
  (`_exigir_secret_key_propia` en `core/config.py`) — es preferible que el
  proceso no levante a que levante inseguro y nadie lo note.

## Modelo: plan de cuentas (`Cuenta`)

Árbol jerárquico auto-referenciado (`padre_id` → `cuentas.id`):

- `codigo`, `nombre`, `tipo` (activo/pasivo/patrimonio/ingreso/gasto/costo)
- `naturaleza` (deudora/acreedora) — se autocompleta según `tipo` si no se envía
- `nivel` — profundidad en el árbol, calculado al crear
- `acepta_movimiento` — solo cuentas de detalle (hojas) reciben asientos; una
  cuenta se marca automáticamente como sumaria (`False`) al ganar una hija
- Borrar una cuenta con hijas, o con movimientos contables asociados, está
  bloqueado (409)

Endpoints en `/api/v1/cuentas`: `POST /`, `GET /`, `GET /arbol`, `GET /{id}`,
`PATCH /{id}`, `DELETE /{id}`.

## Modelo: asientos contables (`Asiento` + `MovimientoContable`)

Un `Asiento` es el encabezado (número autoincremental, fecha, descripción) y
contiene una o más líneas `MovimientoContable` (débito o crédito sobre una
cuenta). Las líneas se crean/leen/borran siempre junto con su asiento — no
hay edición de una línea suelta ni endpoint de `PATCH` para asientos
(coherente con que un asiento contable no se corrige, se reversa).

**Validación de partida doble** (`AsientoCreate`, en `app/schemas/asiento.py`):
- mínimo 2 movimientos
- cada movimiento tiene débito **o** crédito (no ambos, no ninguno)
- `sum(débitos) == sum(créditos)` para todo el asiento — si no, `422`

Además, a nivel de base de datos cada `movimiento_contable` tiene
`CHECK` constraints que refuerzan lo mismo (montos no negativos, no
ambos lados a la vez, al menos uno > 0), como defensa adicional ante
escrituras que no pasen por la API.

Al crear el asiento también se valida (`crud/asiento.py`) que cada cuenta
referenciada exista, esté `activa` y `acepta_movimiento` (no sea sumaria) —
si no, `400`.

Endpoints en `/api/v1/asientos`: `POST /`, `GET /`, `GET /{id}`, `DELETE /{id}`
(borra en cascada sus movimientos, pero rechaza con `409` si el asiento ya
fue reversado — se perdería la trazabilidad).

`GET /` acepta `skip`, `limit` (máx. 500), `fecha_desde`, `fecha_hasta` y
`cuenta_id` (asientos que tengan al menos un movimiento sobre esa cuenta,
vía `Asiento.movimientos.any(...)`). Devuelve un objeto paginado:

```json
{"total": 42, "skip": 0, "limit": 100, "items": [ ... ]}
```

`total` se calcula con un `COUNT` aparte (mismos filtros, sin `LIMIT`) para
que el cliente sepa cuántas páginas hay sin traer todos los registros.

### Auditoría: quién cargó cada asiento

Cada asiento guarda el usuario autenticado que lo creó (`usuario_id`), y
`AsientoRead` lo expone junto con `usuario_email` para no tener que
resolver el id aparte. Aplica igual a las reversiones: queda registrado
quién reversó, que suele ser más interesante que quién cargó el original.

El campo es **nullable** a propósito: los asientos cargados antes de que
existiera la autenticación no tienen autor y no se puede inventar uno.

El FK es `ON DELETE RESTRICT`, y la relación `Usuario.asientos` usa
`passive_deletes="all"`. Sin eso, SQLAlchemy "ayuda" poniendo
`usuario_id=NULL` en los asientos al borrar un usuario, y el borrado
parece funcionar mientras destruye la trazabilidad en silencio; con
`passive_deletes` no toca las hijas y deja que la restricción de la base
rechace el borrado.

### Reversión de asientos

`POST /api/v1/asientos/{id}/reversar?fecha=YYYY-MM-DD` (fecha opcional,
por defecto hoy)

Un asiento no se corrige in-place: se reversa. Esto crea un **nuevo**
asiento con las mismas líneas pero débito/crédito invertidos — así el
saldo neto vuelve a cero pero ambos movimientos quedan visibles en el
libro mayor (auditoría completa: se ve el error original y su corrección,
no se lo esconde). Reglas:

- Un asiento solo puede reversarse una vez (`409` si ya tiene una
  reversión, expuesto como `reversado_por_id` en `AsientoRead`).
- Se revalidan las cuentas involucradas (por si alguna se desactivó desde
  la creación del asiento original) — `400` si no.
- El asiento resultante se relaciona con el original vía `reversa_de_id`.

> Nota: el número de asiento se calcula como `MAX(numero) + 1` dentro de la
> misma transacción; bajo alta concurrencia esto puede colisionar (el
> `UniqueConstraint` lo evita silenciosamente pasar, pero haría fallar la
> transacción). Para producción con múltiples escritores simultáneos conviene
> una secuencia de base de datos o `SELECT ... FOR UPDATE`.

## Libro mayor por cuenta

`GET /api/v1/libro-mayor/{cuenta_id}?fecha_desde=&fecha_hasta=`

Devuelve, para la cuenta dada: saldo inicial (calculado a partir de los
movimientos previos a `fecha_desde`, si se indica), el detalle de
movimientos en el rango con saldo corriente línea a línea, y los totales
(`total_debitos`, `total_creditos`, `saldo_final`).

El signo del saldo depende de la `naturaleza` de la cuenta: en cuentas
deudoras el saldo sube con el débito y baja con el crédito; en cuentas
acreedoras es al revés.

## Balance de comprobación

`GET /api/v1/balance-comprobacion/?fecha_desde=&fecha_hasta=`

Una fila por cada cuenta de detalle activa (`acepta_movimiento=True`,
`activa=True`) — incluye las que no tuvieron movimientos en el rango, con
saldo en cero — con `saldo_inicial`, `debito`, `credito` y `saldo_final`
(agregado con dos `GROUP BY` en SQL, no iterando cuenta por cuenta).

Al final, `total_debitos` y `total_creditos` globales y un booleano
`balanceado` (`total_debitos == total_creditos`). Por construcción de la
partida doble esto debería dar siempre `true` para cualquier rango — es
precisamente el propósito del reporte: una prueba de que la contabilidad
está internamente consistente. Si alguna vez diera `false`, sería señal de
que algo escribió en `movimientos_contables` sin pasar por la validación
de la API.

## Estado de resultados

`GET /api/v1/estado-resultados/?fecha_desde=&fecha_hasta=`

Reporte de **período** (no acumulativo desde el inicio, a diferencia de los
otros reportes): agrupa por cuenta las de tipo `ingreso`, `costo` y `gasto`
con actividad en el rango — a diferencia del balance de comprobación, aquí
sí se omiten las cuentas sin movimientos, porque un estado de resultados no
debería listar cada cuenta nominal que existe alguna vez, solo la actividad
real del período.

```
utilidad_bruta = total_ingresos - total_costos
utilidad_neta  = utilidad_bruta - total_gastos
```

## Balance general

`GET /api/v1/balance-general/?fecha_corte=`

Saldos acumulados (desde el inicio del sistema, no por período) de las
cuentas `activo`, `pasivo` y `patrimonio` a una fecha de corte.

El detalle no obvio: como el sistema no tiene asientos de cierre de
ejercicio que trasladen el resultado de las cuentas nominales
(ingreso/costo/gasto) a una cuenta de patrimonio, ese resultado vive
"flotando" fuera de las cuentas reales. `balance_general` lo calcula
llamando internamente a `get_estado_resultados(fecha_desde=None,
fecha_hasta=fecha_corte)` y lo suma al patrimonio como
`resultado_acumulado` — sin este paso, el balance **no cuadraría** ante
cualquier venta o gasto ya registrado. Con eso:

```
total_patrimonio = suma(cuentas de patrimonio) + resultado_acumulado
balanceado = total_activo == total_pasivo + total_patrimonio
```

## Cierre de ejercicio

`POST /api/v1/cierres/` (solo admin) — `{"fecha_cierre", "cuenta_resultado_id"}`
`GET /api/v1/cierres/` — historial de cierres

Genera un asiento que salda las cuentas de ingreso, costo y gasto contra una
cuenta de **patrimonio** (la que se indique en `cuenta_resultado_id`), y
registra el cierre en la tabla `cierres` con el asiento generado, el autor y
la utilidad resultante. Se guarda el asiento en vez de recalcularlo para que
quede auditable exactamente qué se cerró y por cuánto.

Reglas: la cuenta de resultado debe ser de patrimonio, activa y de detalle
(`400`); no se puede cerrar dos veces la misma fecha ni con una fecha
anterior al último cierre (`409`); y si no hay saldos nominales pendientes,
`400`.

Cada cierre toma el saldo de las cuentas nominales **incluyendo los cierres
anteriores**. Como el cierre previo las dejó en cero, el neto que queda es
solo la actividad posterior — no hace falta llevar la cuenta de "desde
cuándo" cerrar.

### El detalle que hace que los reportes sigan siendo correctos

El asiento de cierre lleva `es_cierre=True`, y los dos reportes que tocan
cuentas nominales lo tratan **al revés** a propósito:

- **Estado de resultados: lo excluye.** El asiento de cierre es un artificio
  para saldar cuentas, no actividad del negocio. Si se contara, un ejercicio
  ya cerrado mostraría ingresos y gastos en cero, que es exactamente lo que
  no se quiere de un reporte histórico.
- **Balance general: lo incluye.** Después del cierre la utilidad vive en la
  cuenta de patrimonio; si además se la sumara como `resultado_acumulado`
  (que se calcula en vivo desde las nominales), se contaría **dos veces** y
  el balance dejaría de cuadrar. Al incluir el asiento de cierre, las
  nominales netean cero, `resultado_acumulado` queda en 0 y la utilidad se
  cuenta una sola vez.

Por eso `sumar_por_cuenta` y `get_estado_resultados` toman
`incluir_cierres`, y `balance_general` es el único que lo pasa en `True`.
Hay tests que fijan justamente esto: que después de cerrar, el balance
general siga cuadrando y el estado de resultados siga mostrando la
actividad real del período.

> Caso borde cubierto: si la utilidad da exactamente cero no se agrega la
> línea de resultado (sería un movimiento de 0/0 y violaría el `CHECK` que
> exige débito o crédito mayor a cero). El asiento igual balancea, porque
> las líneas que saldan las nominales ya suman cero entre sí.

`agregados.py` centraliza el signo por naturaleza y la consulta agregada
por cuenta (`GROUP BY`) que usan `balance_comprobacion`, `estado_resultados`
y `balance_general` — se extrajo cuando el mismo cálculo se empezó a repetir
en el tercer/cuarto reporte.

## Exportar reportes a CSV

Los cuatro reportes (`libro-mayor`, `balance-comprobacion`,
`estado-resultados`, `balance-general`) aceptan `?formato=csv` (además de
sus filtros normales de fecha) y devuelven un archivo descargable
(`Content-Disposition: attachment`) en vez del JSON de siempre:

```
GET /api/v1/balance-comprobacion/?formato=csv
GET /api/v1/estado-resultados/?fecha_desde=2026-01-01&fecha_hasta=2026-01-31&formato=csv
GET /api/v1/libro-mayor/{cuenta_id}?formato=csv
```

Se eligió CSV (vía el módulo `csv` de la librería estándar,
`app/utils/csv_export.py`) en lugar de Excel o PDF: no agrega dependencias
nuevas, Excel lo abre igual de bien, y evita el riesgo de romperse por
desactualización de librerías de terceros (ya pasó una vez en este proyecto
con las versiones de FastAPI/Starlette). Cada reporte de tipo "sección +
total" (estado de resultados, balance general) se aplana a filas con una
columna `seccion`, y lleva filas de totales al final.

Estos endpoints declaran `response_model=None` porque devuelven JSON o CSV
según el parámetro — a cambio, `/docs` no puede mostrar el schema de
respuesta para ellos.

## Tests

```bash
pip install -r requirements-dev.txt
pytest                       # backend

cd frontend && npm test      # frontend (Vitest)
```

La suite (`tests/`) corre contra SQLite en memoria (no requiere Docker ni
Postgres levantado) usando un `TestClient` de FastAPI con `get_db`
sobreescrito por sesión de test — cada test parte de una base vacía.
`tests/conftest.py::plan_cuentas` arma un plan de cuentas mínimo
(activo/pasivo/patrimonio/ingreso/costo/gasto) reutilizado por los módulos
de reportes.

Cobertura por módulo:

- `test_cuentas.py` — jerarquía (una cuenta se vuelve sumaria al ganar una
  hija), y los bloqueos de borrado (`CuentaConHijasError`,
  `CuentaConMovimientosError`).
- `test_asientos.py` — validación de partida doble a nivel de schema
  (Pydantic), rechazo de cuentas sumarias/inactivas, numeración
  autoincremental, y el flujo completo de reversión (montos invertidos,
  enlace `reversa_de_id`/`reversado_por_id`, bloqueo de doble reversión y
  de borrado de un asiento ya reversado).
- `test_libro_mayor.py` — saldo corriente línea a línea según naturaleza
  deudora/acreedora, y `saldo_inicial` calculado a partir de movimientos
  previos a `fecha_desde`.
- `test_balance_comprobacion.py` — incluye cuentas de detalle sin
  movimientos, `balanceado=true` por construcción, y el caso puntual de
  cero negativo (`sin_cero_negativo`) cuando un saldo se cancela por
  completo.
- `test_estado_resultados.py` — cálculo de utilidad bruta/neta y omisión de
  cuentas nominales sin actividad en el rango.
- `test_balance_general.py` — un escenario contable completo (aporte de
  capital, deuda con proveedor, venta con su costo y un gasto) donde
  `total_activo == total_pasivo + total_patrimonio` gracias al
  `resultado_acumulado`, verificado además contra `estado_resultados`.
- `test_auth.py` — registro/login, email insensible a mayúsculas, y los dos
  esquemas de autorización de `/docs`.
- `test_roles.py` — el primer usuario es admin (aunque pida otro rol), el
  registro se cierra después, y qué puede hacer cada rol. Incluye el test
  que valida los literales de enum de la migración, que la suite no
  ejecutaría de otro modo.
- `test_cierre.py` — el escenario contable más completo: que el balance
  general siga cuadrando después de cerrar, que el estado de resultados
  siga mostrando la actividad del período cerrado, que un segundo cierre
  tome solo lo posterior, y los casos de pérdida y de utilidad exactamente
  cero.
- `test_spa.py` — que la API sirva el bundle del frontend con fallback a
  `index.html`, sin tragarse los 404 de `/api/` ni permitir path traversal.
  Se saltea si no hay build (`frontend/dist` está gitignoreado).

### Frontend (Vitest + Testing Library)

Requiere **Node 22+**: jsdom 30 usa APIs de undici que no existen en Node
20 (`webidl.util.markAsUncloneable`), y sin eso los tests ni arrancan. Está
declarado en `engines` de `frontend/package.json`.

- `src/api/client.test.js` — el cliente HTTP: header `Authorization`, login
  como formulario, el 401 que borra el token y avisa que expiró la sesión,
  el armado del mensaje a partir de los errores de validación 422 de
  FastAPI, y el descarte de params vacíos en la query.
- `src/pages/AsientoNuevo.test.jsx` — la pantalla con más lógica: detección
  de balance, exclusión mutua entre débito y crédito, que no se descuadre
  por redondeo de punto flotante (`0.1 + 0.2`), y que solo viajen al
  backend las líneas con datos.
- `src/pages/Login.test.jsx` — login exitoso guardando el token, y el error
  de credenciales sin dejar la sesión a medias.

`src/test/setup.js` instala un `localStorage` propio en memoria en vez de
usar el de jsdom. Node 26 expone un `localStorage` nativo experimental que
queda deshabilitado sin `--localstorage-file` y termina tapando al de
jsdom; en Node 22 eso no pasa. Sin esta implementación propia los tests
pasarían en CI y fallarían en una máquina con Node 26.
