# Sistema Contable

API de contabilidad con FastAPI + PostgreSQL + SQLAlchemy + Alembic.

## Estructura

```
app/
  core/config.py          # Settings (lee .env)
  db/
    base_class.py          # Base declarativa
    base.py                 # Importa todos los modelos (para Alembic)
    session.py              # engine, SessionLocal, get_db
  models/
    cuenta.py               # Cuenta (plan de cuentas jerárquico)
    asiento.py               # Asiento + MovimientoContable (partida doble)
  schemas/
    cuenta.py                # Create/Update/Read/Tree
    asiento.py, movimiento.py  # Create (con validación de balance)/Read
    libro_mayor.py            # Respuesta del libro mayor
  crud/
    cuenta.py, asiento.py, libro_mayor.py
  api/v1/endpoints/
    cuentas.py, asientos.py, libro_mayor.py
  main.py                   # App FastAPI
alembic/                    # Migraciones (env.py conectado a app.core.config)
  versions/0001_create_cuentas.py
  versions/0002_create_asientos.py
```

## Puesta en marcha

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # ajustar DATABASE_URL

createdb contable_db   # o crear la DB manualmente en PostgreSQL

alembic upgrade head
uvicorn app.main:app --reload
```

Docs interactivas: `http://localhost:8000/docs`

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

`agregados.py` centraliza el signo por naturaleza y la consulta agregada
por cuenta (`GROUP BY`) que usan `balance_comprobacion`, `estado_resultados`
y `balance_general` — se extrajo cuando el mismo cálculo se empezó a repetir
en el tercer/cuarto reporte.
