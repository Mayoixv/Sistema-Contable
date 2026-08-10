# Documentación del Sistema Contable

Documentación completa de todo lo implementado: qué hace cada pieza, por qué
está hecha así, y un recorrido cuenta por cuenta.

- **Repositorio:** https://github.com/Mayoixv/Sistema-Contable
- **Stack:** FastAPI · PostgreSQL · SQLAlchemy · Alembic · React · Vite · Docker

---

## Índice

1. [Qué es el sistema](#1-qué-es-el-sistema)
2. [Cómo levantarlo](#2-cómo-levantarlo)
3. [Fundamentos contables](#3-fundamentos-contables)
4. [El plan de cuentas, cuenta por cuenta](#4-el-plan-de-cuentas-cuenta-por-cuenta)
5. [Modelo de datos, tabla por tabla](#5-modelo-de-datos-tabla-por-tabla)
6. [La API, endpoint por endpoint](#6-la-api-endpoint-por-endpoint)
7. [Cómo se calcula cada reporte](#7-cómo-se-calcula-cada-reporte)
8. [Cierre de ejercicio, paso a paso](#8-cierre-de-ejercicio-paso-a-paso)
9. [Autenticación, roles y permisos](#9-autenticación-roles-y-permisos)
10. [La interfaz web](#10-la-interfaz-web)
11. [Tests](#11-tests)
12. [Infraestructura: Docker, migraciones y CI](#12-infraestructura-docker-migraciones-y-ci)
13. [Recorrido completo con datos reales](#13-recorrido-completo-con-datos-reales)
14. [Decisiones de diseño](#14-decisiones-de-diseño)
15. [Limitaciones conocidas](#15-limitaciones-conocidas)

---

## 1. Qué es el sistema

Un sistema de contabilidad por **partida doble** completo: registra las
operaciones de un negocio y produce los estados contables clásicos.

Tiene tres partes:

| Parte | Qué es | Dónde vive |
|---|---|---|
| **API REST** | Toda la lógica contable y las validaciones | `app/` |
| **Interfaz web** | Pantallas para operar el sistema | `frontend/` |
| **Base de datos** | PostgreSQL, con migraciones versionadas | `alembic/` |

Funcionalidad implementada:

- Plan de cuentas jerárquico (árbol de cuentas, con sumarias y de detalle)
- Asientos contables con validación de partida doble en dos capas
- Reversión de asientos (no se editan: se corrigen con un contra-asiento)
- Libro mayor por cuenta, con saldo corriente
- Balance de comprobación
- Estado de resultados
- Balance general
- Exportación de los cuatro reportes a CSV
- Cierre de ejercicio
- Usuarios con roles (admin / contador / lector)
- Auditoría: cada asiento guarda quién lo cargó
- 102 tests de backend + 20 de frontend, corriendo en CI

---

## 2. Cómo levantarlo

### Con Docker (recomendado)

```bash
docker compose up -d --build
```

Un solo comando levanta todo. Entrá a **http://localhost:8001**.

Qué hace por dentro:

1. Levanta PostgreSQL 16 y espera a que pase su *healthcheck* (`pg_isready`).
   Sin esa espera, la API arrancaría antes que la base y fallaría al migrar.
2. Compila la interfaz web (etapa `node:22-slim` del `Dockerfile`).
3. Aplica las migraciones (`alembic upgrade head`).
4. Arranca `uvicorn`, que sirve la API **y** la interfaz.

| Servicio | Puerto | Nota |
|---|---|---|
| Interfaz web + API | `8001` | Se usan 8001/5433 y no 8000/5432 para no chocar con otros proyectos locales |
| PostgreSQL | `5433` | Datos en el volumen `contable_pgdata` |

```bash
docker compose logs -f api     # ver logs
docker compose down            # bajar, conservando los datos
docker compose down -v         # bajar y borrar la base
```

### Para desarrollar

```bash
# Backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload          # :8000

# Frontend (otra terminal) — requiere Node 22+
cd frontend && npm install && npm run dev   # :5173
```

### Primer uso

El primer usuario que se registre queda **admin** automáticamente. Después
de eso, el registro se cierra y solo un admin puede crear usuarios.

---

## 3. Fundamentos contables

Necesario para entender el resto del documento.

### Partida doble

Toda operación se registra en un **asiento**, compuesto por al menos dos
**movimientos** (líneas). Cada línea es un **débito** o un **crédito** sobre
una cuenta, y en cada asiento:

```
suma de débitos  =  suma de créditos
```

Ejemplo — un aporte de capital de 500.000: entra dinero a la caja (débito) y
nace una obligación con el socio (crédito).

| Cuenta | Débito | Crédito |
|---|---:|---:|
| Caja | 500.000 | |
| Capital social | | 500.000 |
| **Total** | **500.000** | **500.000** |

### Naturaleza de las cuentas

Un débito no significa "sumar" ni un crédito "restar": depende de la
naturaleza de la cuenta.

| Naturaleza | Tipos de cuenta | El saldo sube con | Baja con |
|---|---|---|---|
| **Deudora** | Activo, Gasto, Costo | Débito | Crédito |
| **Acreedora** | Pasivo, Patrimonio, Ingreso | Crédito | Débito |

En el código esto es una sola función (`app/crud/agregados.py`):

```python
def signo_naturaleza(naturaleza):
    return 1 if naturaleza == NaturalezaCuenta.DEUDORA else -1
```

y el saldo de cualquier cuenta se calcula igual para todas:
`saldo = signo × (débitos − créditos)`.

### Ecuación fundamental

```
Activo = Pasivo + Patrimonio
```

Si la contabilidad está bien registrada, esto se cumple **siempre**. El
balance general lo verifica y lo expone en el campo `balanceado`.

### Cuentas reales vs. nominales

| | Cuentas reales | Cuentas nominales |
|---|---|---|
| **Tipos** | Activo, Pasivo, Patrimonio | Ingreso, Costo, Gasto |
| **Qué miden** | Una foto: cuánto hay *hoy* | Una película: cuánto pasó *en un período* |
| **Reporte** | Balance general | Estado de resultados |
| **Al cerrar el ejercicio** | Siguen su curso | Se saldan a cero |

Esta distinción es la clave del [cierre de ejercicio](#8-cierre-de-ejercicio-paso-a-paso).

---

## 4. El plan de cuentas, cuenta por cuenta

El plan de cuentas es un **árbol**. Cada cuenta puede tener una cuenta padre
(`padre_id` → `cuentas.id`), lo que permite agrupar y totalizar.

### Sumarias vs. de detalle

| | Cuenta sumaria | Cuenta de detalle |
|---|---|---|
| Tiene hijas | Sí | No (es una hoja del árbol) |
| `acepta_movimiento` | `False` | `True` |
| Recibe asientos | **No** | Sí |
| Para qué sirve | Agrupar y totalizar | Registrar operaciones |

**Automatismo importante:** cuando una cuenta gana su primera hija, el
sistema la marca sola como sumaria (`acepta_movimiento = False`). Está en
`app/crud/cuenta.py`:

```python
if padre is not None and padre.acepta_movimiento:
    # Una cuenta que gana una hija pasa a ser "sumaria": deja de aceptar
    # movimientos directos de asientos contables.
    padre.acepta_movimiento = False
```

Sin esto, se podría cargar un movimiento en "Activo" *y* en "Caja", y los
totales quedarían inflados al sumar el padre con las hijas.

### El plan de cuentas de ejemplo

Este es el plan cargado en la demo: 20 cuentas, tres niveles.

#### 1 — Activo *(sumaria)*

Todo lo que el negocio **tiene**. Naturaleza deudora.

| Código | Nombre | Tipo | Qué representa | Cuándo se mueve |
|---|---|---|---|---|
| `1` | Activo | sumaria | Agrupa todo el activo | Nunca (es sumaria) |
| `1.1` | Activo corriente | sumaria | Bienes que se convierten en dinero en menos de un año | Nunca (es sumaria) |
| `1.1.01` | **Caja** | activo | Efectivo en el negocio | **Débito:** entra plata (cobros, ventas al contado). **Crédito:** sale (pagos) |
| `1.1.02` | **Banco** | activo | Saldo en la cuenta bancaria | **Débito:** depósitos, acreditaciones. **Crédito:** pagos con transferencia o cheque |
| `1.1.03` | **Cuentas por cobrar** | activo | Lo que los clientes deben | **Débito:** se vende a crédito. **Crédito:** el cliente paga |
| `1.1.04` | **Mercaderías** | activo | Stock disponible para vender, valuado al costo | **Débito:** se compra stock. **Crédito:** se vende (el costo sale del stock) |

> **Nota sobre Mercaderías:** el sistema usa *inventario permanente*. Comprar
> stock **no es un gasto**: es cambiar dinero por mercadería, dos activos. El
> costo recién impacta el resultado cuando la mercadería se vende, con un
> asiento aparte que acredita Mercaderías y debita Costo de mercaderías
> vendidas. Por eso cada venta genera **dos** asientos: uno por el ingreso y
> otro por el costo.

#### 2 — Pasivo *(sumaria)*

Todo lo que el negocio **debe**. Naturaleza acreedora.

| Código | Nombre | Tipo | Qué representa | Cuándo se mueve |
|---|---|---|---|---|
| `2` | Pasivo | sumaria | Agrupa todas las deudas | Nunca (es sumaria) |
| `2.1` | Pasivo corriente | sumaria | Deudas exigibles en menos de un año | Nunca (es sumaria) |
| `2.1.01` | **Proveedores** | pasivo | Deuda por mercadería comprada a crédito | **Crédito:** se compra a crédito (nace la deuda). **Débito:** se le paga (se extingue) |
| `2.1.02` | **Sueldos a pagar** | pasivo | Sueldos devengados y todavía no pagados | **Crédito:** se liquida el sueldo del mes. **Débito:** se paga al empleado |

#### 3 — Patrimonio *(sumaria)*

Lo que queda para los dueños: `Activo − Pasivo`. Naturaleza acreedora.

| Código | Nombre | Tipo | Qué representa | Cuándo se mueve |
|---|---|---|---|---|
| `3` | Patrimonio | sumaria | Agrupa el patrimonio | Nunca (es sumaria) |
| `3.1.01` | **Capital social** | patrimonio | Aportes de los socios | **Crédito:** un socio aporta. **Débito:** se retira capital. También recibe el resultado al cerrar el ejercicio |

#### 4 — Ingresos *(sumaria)*

Naturaleza acreedora. **Cuenta nominal.**

| Código | Nombre | Tipo | Qué representa | Cuándo se mueve |
|---|---|---|---|---|
| `4` | Ingresos | sumaria | Agrupa los ingresos | Nunca (es sumaria) |
| `4.1.01` | **Ventas** | ingreso | Facturación por ventas | **Crédito:** se vende. **Débito:** solo por devoluciones o al cerrar el ejercicio |

#### 5 — Costos *(sumaria)*

Naturaleza deudora. **Cuenta nominal.**

| Código | Nombre | Tipo | Qué representa | Cuándo se mueve |
|---|---|---|---|---|
| `5` | Costos | sumaria | Agrupa los costos | Nunca (es sumaria) |
| `5.1.01` | **Costo de mercaderías vendidas** | costo | Cuánto costó lo que se vendió | **Débito:** al vender, contra Mercaderías |

> **Costo vs. gasto:** el costo está atado directamente a lo que se vende (si
> no vendés, no hay costo). El gasto existe igual: el alquiler se paga
> vendas o no. Separarlos permite calcular la **utilidad bruta**
> (`ingresos − costos`), que muestra el margen del negocio antes de la
> estructura.

#### 6 — Gastos *(sumaria)*

Naturaleza deudora. **Cuenta nominal.**

| Código | Nombre | Tipo | Qué representa | Cuándo se mueve |
|---|---|---|---|---|
| `6` | Gastos | sumaria | Agrupa los gastos | Nunca (es sumaria) |
| `6.1.01` | **Sueldos** | gasto | Remuneraciones del período | **Débito:** al liquidar sueldos |
| `6.1.02` | **Alquiler** | gasto | Alquiler del local | **Débito:** al devengar el alquiler del mes |
| `6.1.03` | **Servicios** | gasto | Luz, agua, internet | **Débito:** al recibir las facturas |

### Cómo se arma el plan

El orden importa: **primero los padres**, porque el padre se vuelve sumario
al recibir la primera hija.

```bash
# 1) La raíz
POST /api/v1/cuentas/  {"codigo": "1", "nombre": "Activo", "tipo": "activo"}
# → nivel 1, acepta_movimiento: true

# 2) Una hija: el padre pasa a sumario automáticamente
POST /api/v1/cuentas/  {"codigo": "1.1", "nombre": "Activo corriente",
                        "tipo": "activo", "padre_id": 1}
# → nivel 2. La cuenta 1 queda con acepta_movimiento: false

# 3) La hoja, que sí recibe movimientos
POST /api/v1/cuentas/  {"codigo": "1.1.01", "nombre": "Caja",
                        "tipo": "activo", "padre_id": 2}
# → nivel 3, acepta_movimiento: true
```

La `naturaleza` **no hace falta enviarla**: se deduce del `tipo` mediante
`NATURALEZA_POR_TIPO` (en `app/models/cuenta.py`). Se puede sobrescribir
explícitamente para cuentas de naturaleza contraria, como *Depreciación
acumulada*: es un activo, pero de naturaleza acreedora porque resta.

### Protecciones al borrar

Borrar una cuenta se rechaza con `409` si:

1. **Tiene cuentas hijas** → `CuentaConHijasError`
2. **Tiene movimientos contables** → `CuentaConMovimientosError`

Ambas se validan en la aplicación además del `FOREIGN KEY ... RESTRICT` de
la base. El motivo está comentado en el código: SQLite (que usan los tests)
no aplica las *foreign keys* sin activar un *pragma*, y además el mensaje
propio es mucho más claro que un `IntegrityError` genérico.

---

## 5. Modelo de datos, tabla por tabla

Cinco tablas: `cuentas`, `asientos`, `movimientos_contables`, `usuarios`,
`cierres`.

```
usuarios ──< asientos ──< movimientos_contables >── cuentas
                 │                                     │
                 └──< cierres >────────────────────────┘
             (asientos.reversa_de_id → asientos.id, autorreferencia)
             (cuentas.padre_id       → cuentas.id,  autorreferencia)
```

### `cuentas` — el plan de cuentas

`app/models/cuenta.py`

| Columna | Tipo | Para qué |
|---|---|---|
| `id` | int PK | |
| `codigo` | varchar(20) **único** | Código contable (`1.1.01`) |
| `nombre` | varchar(150) | |
| `tipo` | enum | `activo`, `pasivo`, `patrimonio`, `ingreso`, `gasto`, `costo` |
| `naturaleza` | enum | `deudora` o `acreedora`; se autocompleta según el tipo |
| `nivel` | int | Profundidad en el árbol; se calcula al crear (`padre.nivel + 1`) |
| `padre_id` | int FK → `cuentas.id` | Autorreferencia. `ON DELETE RESTRICT` |
| `acepta_movimiento` | bool | `False` en las sumarias |
| `activa` | bool | Baja lógica: una cuenta inactiva no admite asientos nuevos, pero conserva su historial |
| `descripcion` | text | Opcional |
| `created_at` / `updated_at` | timestamptz | |

Restricciones: `UNIQUE(codigo)` y `CHECK (nivel >= 1)`.

Relaciones autorreferenciales, resueltas con `remote_side=[id]`:

```python
padre: Mapped["Cuenta | None"] = relationship("Cuenta", remote_side=[id], back_populates="hijas")
hijas: Mapped[list["Cuenta"]] = relationship("Cuenta", back_populates="padre", order_by="Cuenta.codigo")
```

### `asientos` — el encabezado

`app/models/asiento.py`

| Columna | Tipo | Para qué |
|---|---|---|
| `id` | int PK | |
| `numero` | int **único** | Número correlativo, `MAX(numero) + 1` |
| `fecha` | date | Fecha contable de la operación |
| `descripcion` | text | |
| `reversa_de_id` | int FK → `asientos.id` | Si este asiento *es* una reversión, apunta al original. `ON DELETE SET NULL` |
| `usuario_id` | int FK → `usuarios.id` | Quién lo cargó. `ON DELETE RESTRICT` |
| `es_cierre` | bool | Marca los asientos generados por un cierre de ejercicio |
| `created_at` / `updated_at` | timestamptz | |

Dos propiedades calculadas:

```python
@property
def reversado_por_id(self):        # el asiento que reversa a este, si existe
    return self.reversiones[0].id if self.reversiones else None

@property
def usuario_email(self):
    return self.usuario.email if self.usuario else None
```

`usuario_id` es *nullable* porque los asientos cargados antes de que
existiera la autenticación no tienen autor conocido, y no se puede inventar
uno. Los nuevos siempre lo completan.

### `movimientos_contables` — las líneas

| Columna | Tipo | Para qué |
|---|---|---|
| `id` | int PK | |
| `asiento_id` | int FK → `asientos.id` | `ON DELETE CASCADE`: las líneas no viven sin su asiento |
| `cuenta_id` | int FK → `cuentas.id` | `ON DELETE RESTRICT`: no se borra una cuenta con movimientos |
| `debito` | numeric(14,2) | |
| `credito` | numeric(14,2) | |
| `descripcion` | varchar(255) | Detalle de la línea; opcional |

Tres `CHECK` en la base, como red de seguridad ante escrituras que no pasen
por la API:

```sql
CHECK (debito >= 0 AND credito >= 0)        -- ck_movimientos_montos_no_negativos
CHECK (NOT (debito > 0 AND credito > 0))    -- ck_movimientos_no_debito_y_credito
CHECK (debito > 0 OR credito > 0)           -- ck_movimientos_monto_requerido
```

**Por qué `numeric(14,2)` y no `float`:** el punto flotante no representa
exactamente los decimales. `0.1 + 0.2` da `0.30000000000000004`, y un
asiento perfectamente balanceado quedaría descuadrado por un error de
redondeo. `numeric` es exacto.

### `usuarios`

| Columna | Tipo | Para qué |
|---|---|---|
| `id` | int PK | |
| `email` | varchar(255) **único** | Se guarda siempre en minúsculas |
| `nombre` | varchar(150) | |
| `hashed_password` | varchar(255) | Hash bcrypt (60 caracteres) |
| `rol` | enum | `admin`, `contador` o `lector` |
| `activo` | bool | Baja lógica |
| `created_at` | timestamptz | |

La relación con asientos lleva `passive_deletes="all"`, y el comentario del
código explica por qué es imprescindible:

```python
# passive_deletes="all": sin esto, al borrar un usuario SQLAlchemy pone
# usuario_id=NULL en sus asientos y el borrado "funciona", dejándolos sin
# autor. Con esto no toca las hijas y deja actuar al ON DELETE RESTRICT
# de la base, que es lo que preserva la trazabilidad.
```

### `cierres`

`app/models/cierre.py`

| Columna | Tipo | Para qué |
|---|---|---|
| `id` | int PK | |
| `fecha_cierre` | date **único** | Fecha de corte del ejercicio cerrado |
| `asiento_id` | int FK → `asientos.id` | El asiento de cierre generado. `RESTRICT` |
| `cuenta_resultado_id` | int FK → `cuentas.id` | Cuenta de patrimonio que recibió el resultado. `RESTRICT` |
| `usuario_id` | int FK → `usuarios.id` | Quién cerró. `RESTRICT` |
| `utilidad_neta` | numeric(14,2) | Resultado trasladado |
| `created_at` | timestamptz | |

Guarda el resultado en lugar de recalcularlo, para que quede auditable
exactamente qué se cerró, cuándo y por cuánto.

---

## 6. La API, endpoint por endpoint

Prefijo: `/api/v1`. Documentación interactiva en `/docs`.

Columna **Permiso**: 🔓 público · 🔑 cualquier usuario autenticado ·
✏️ admin o contador · 👑 solo admin.

### Autenticación — `/auth`

| Método | Ruta | Permiso | Qué hace |
|---|---|---|---|
| `POST` | `/auth/registrar` | 🔓/👑 | Crea un usuario. **Público solo si no existe ninguno** (crea el admin inicial); después exige admin |
| `POST` | `/auth/login` | 🔓 | Devuelve el JWT. Formulario `username` (= email) + `password` |
| `GET` | `/auth/me` | 🔑 | Datos del usuario de la sesión |

### Plan de cuentas — `/cuentas`

| Método | Ruta | Permiso | Qué hace |
|---|---|---|---|
| `POST` | `/cuentas/` | ✏️ | Crea una cuenta. `409` si el código existe; `400` si el padre no existe |
| `GET` | `/cuentas/` | 🔑 | Lista plana, con `skip`/`limit` |
| `GET` | `/cuentas/arbol` | 🔑 | Árbol jerárquico anidado |
| `GET` | `/cuentas/{id}` | 🔑 | Una cuenta |
| `PATCH` | `/cuentas/{id}` | ✏️ | Modificación parcial |
| `DELETE` | `/cuentas/{id}` | ✏️ | `409` si tiene hijas o movimientos |

### Asientos — `/asientos`

| Método | Ruta | Permiso | Qué hace |
|---|---|---|---|
| `POST` | `/asientos/` | ✏️ | Crea un asiento. `422` si no balancea; `400` si una cuenta es sumaria o está inactiva |
| `GET` | `/asientos/` | 🔑 | Lista paginada con filtros |
| `GET` | `/asientos/{id}` | 🔑 | Un asiento con sus líneas |
| `POST` | `/asientos/{id}/reversar` | ✏️ | Genera la reversión. `409` si ya fue reversado |
| `DELETE` | `/asientos/{id}` | ✏️ | Borra en cascada sus líneas. `409` si ya fue reversado |

`GET /asientos/` acepta `skip`, `limit` (máx. 500), `fecha_desde`,
`fecha_hasta` y `cuenta_id`, y responde:

```json
{ "total": 22, "skip": 0, "limit": 100, "items": [ ... ] }
```

`total` sale de un `COUNT` aparte con los mismos filtros, para que el cliente
sepa cuántas páginas hay sin traer todos los registros.

### Reportes

Los cuatro aceptan `?formato=csv` para descargar el archivo.

| Método | Ruta | Permiso | Parámetros |
|---|---|---|---|
| `GET` | `/libro-mayor/{cuenta_id}` | 🔑 | `fecha_desde`, `fecha_hasta`, `formato` |
| `GET` | `/balance-comprobacion/` | 🔑 | `fecha_desde`, `fecha_hasta`, `formato` |
| `GET` | `/estado-resultados/` | 🔑 | `fecha_desde`, `fecha_hasta`, `formato` |
| `GET` | `/balance-general/` | 🔑 | `fecha_corte`, `formato` |

### Cierre de ejercicio — `/cierres`

| Método | Ruta | Permiso | Qué hace |
|---|---|---|---|
| `POST` | `/cierres/` | 👑 | Cierra el ejercicio. `400` si la cuenta no es de patrimonio o no hay nada que cerrar; `409` si ya hay un cierre en esa fecha o posterior |
| `GET` | `/cierres/` | 🔑 | Historial de cierres |

### Usuarios — `/usuarios`

| Método | Ruta | Permiso | Qué hace |
|---|---|---|---|
| `GET` | `/usuarios/` | 👑 | Lista de usuarios |
| `PATCH` | `/usuarios/{id}` | 👑 | Cambia `rol` o `activo`. `400` si es uno mismo |
| `DELETE` | `/usuarios/{id}` | 👑 | `400` si es uno mismo; `409` si tiene asientos o cierres |

### Otros

| Método | Ruta | Permiso | Qué hace |
|---|---|---|---|
| `GET` | `/health` | 🔓 | `{"status": "ok"}` |
| `GET` | `/docs` | 🔓 | Swagger UI |

---

## 7. Cómo se calcula cada reporte

Los cuatro comparten dos ayudantes en `app/crud/agregados.py`:
`signo_naturaleza()` y `sumar_por_cuenta()`, que agrega débitos y créditos
por cuenta con un solo `GROUP BY` en SQL en lugar de iterar cuenta por
cuenta.

### Libro mayor

`app/crud/libro_mayor.py` — el detalle de una cuenta con su saldo corriendo.

1. **Saldo inicial:** si se pasa `fecha_desde`, suma todos los movimientos
   **anteriores** a esa fecha. Si no, arranca en cero.
2. **Movimientos del rango:** ordenados por fecha, número de asiento y línea.
3. **Saldo corriente:** por cada línea, `saldo += signo × (débito − crédito)`.
4. **Totales:** `total_debitos`, `total_creditos`, `saldo_final`.

### Balance de comprobación

`app/crud/balance_comprobacion.py` — una fila por cada cuenta de detalle
activa, **incluidas las que no tuvieron movimientos** (aparecen en cero).

Por cada cuenta: `saldo_inicial`, `debito` y `credito` del período, y
`saldo_final`. Al final, los totales globales y un booleano `balanceado`.

Por construcción de la partida doble, `balanceado` debería dar **siempre**
`true`: ese es justamente el propósito del reporte. Si diera `false`, sería
señal de que algo escribió en `movimientos_contables` sin pasar por la
validación de la API.

### Estado de resultados

`app/crud/estado_resultados.py` — reporte de **período**.

```
utilidad_bruta = total_ingresos − total_costos
utilidad_neta  = utilidad_bruta − total_gastos
```

Dos detalles:

- **Omite las cuentas sin actividad** en el rango, a diferencia del balance
  de comprobación. Un estado de resultados no debería listar todas las
  cuentas nominales que existen, sino la actividad real del período.
- **Excluye los asientos de cierre** (`incluir_cierres=False` por defecto).
  El asiento de cierre salda las cuentas nominales; si se contara, un
  ejercicio ya cerrado reportaría ingresos y gastos en cero.

### Balance general

`app/crud/balance_general.py` — saldos acumulados de activo, pasivo y
patrimonio a una fecha de corte.

Acá está la parte más sutil del sistema. Las cuentas nominales acumulan un
resultado que **no está reflejado en ninguna cuenta real** hasta que se
cierra el ejercicio. Sin corregir eso, el balance no cuadraría ante
cualquier venta o gasto registrado.

La solución: calcular ese resultado en vivo y sumarlo al patrimonio como
`resultado_acumulado`.

```python
resultado_acumulado = get_estado_resultados(
    db, fecha_desde=None, fecha_hasta=fecha_corte, incluir_cierres=True
)["utilidad_neta"]

total_patrimonio = total_patrimonio_cuentas + resultado_acumulado
balanceado = total_activo == total_pasivo + total_patrimonio
```

**El `incluir_cierres=True` es lo que hace que esto siga siendo correcto
después de un cierre**, y es exactamente lo contrario de lo que necesita el
estado de resultados:

| Reporte | Asientos de cierre | Si se hiciera al revés |
|---|---|---|
| Estado de resultados | **Excluidos** | Un período cerrado mostraría todo en cero |
| Balance general | **Incluidos** | La utilidad se contaría **dos veces**: una en la cuenta de patrimonio y otra en vivo |

Después de un cierre, el neto de las nominales da cero, entonces
`resultado_acumulado` pasa a `0` y la utilidad queda contada una sola vez,
en la cuenta de patrimonio. El balance sigue cuadrando.

### Exportación a CSV

`app/utils/csv_export.py`, con el módulo `csv` de la biblioteca estándar.

Se eligió CSV antes que Excel o PDF: no agrega dependencias, Excel lo abre
igual, y evita romperse por desactualización de librerías de terceros. Los
reportes con secciones (estado de resultados, balance general) se aplanan a
filas con una columna `seccion`, y llevan filas de totales al final.

Estos endpoints declaran `response_model=None` porque devuelven JSON o CSV
según el parámetro; el costo es que `/docs` no puede mostrar el esquema de
respuesta para ellos.

---

## 8. Cierre de ejercicio, paso a paso

`app/crud/cierre.py`

Cerrar el ejercicio significa **saldar a cero las cuentas nominales**
(ingreso, costo, gasto) trasladando su resultado neto a una cuenta de
patrimonio. Es lo que separa un ejercicio del siguiente: el año nuevo
arranca con las cuentas de resultado en cero.

### Qué hace, paso a paso

**1. Valida la cuenta destino.** Tiene que ser de tipo `patrimonio`, aceptar
movimientos y estar activa. El resultado del ejercicio no puede ir a un
activo o a un gasto.

**2. Verifica que no haya un cierre igual o posterior.** Si ya se cerró al
31/03, no se puede volver a cerrar en esa fecha ni antes → `409`.

**3. Calcula el saldo de cada cuenta nominal**, `incluyendo` los asientos de
cierres anteriores:

```python
sumas = sumar_por_cuenta(
    db, cuenta_ids={c.id for c in nominales}, hasta=fecha_cierre, incluir_cierres=True
)
```

Esto es lo que hace que **lo ya cerrado dé cero** y solo se cierre la
actividad posterior, sin necesidad de llevar registro del último cierre.

**4. Contra-asienta cada saldo.** Una cuenta con saldo deudor se cancela con
un crédito por el mismo importe, y viceversa. Las cuentas ya saldadas se
omiten (no se genera una línea en cero).

**5. Agrega la línea del resultado** en la cuenta de patrimonio:

```
utilidad_neta = −(débitos − créditos) de las nominales
```

Gastos y costos suman al neto deudor; los ingresos lo restan. Por eso la
utilidad es el neto deudor con el signo cambiado. Si hay **utilidad** va al
crédito de patrimonio; si hay **pérdida**, al débito.

**6. Marca el asiento con `es_cierre=True`** y guarda el registro en
`cierres`.

### El caso de la utilidad exactamente cero

Si ingresos, costos y gastos se compensan exactamente, no se agrega la línea
de resultado. El comentario del código explica por qué:

```python
# Con utilidad exactamente cero no se agrega la línea de resultado: sería
# un movimiento de 0/0 y violaría el CHECK que exige débito o crédito
# mayor a cero. El asiento igual queda balanceado, porque las líneas que
# saldan las cuentas nominales ya suman cero entre sí.
```

### Ejemplo con los datos de la demo

Al 31/03/2026: ingresos 550.000, costos 295.000, gastos 182.000 →
**utilidad 73.000**. Si se cerrara el ejercicio contra Capital social, el
asiento generado sería:

| Cuenta | Débito | Crédito | Por qué |
|---|---:|---:|---|
| `4.1.01` Ventas | 550.000 | | Salda el saldo acreedor |
| `5.1.01` Costo de mercaderías | | 295.000 | Salda el saldo deudor |
| `6.1.01` Sueldos | | 80.000 | Salda el saldo deudor |
| `6.1.02` Alquiler | | 90.000 | Salda el saldo deudor |
| `6.1.03` Servicios | | 12.000 | Salda el saldo deudor |
| `3.1.01` Capital social | | 73.000 | Recibe la utilidad |
| **Total** | **550.000** | **550.000** | Balanceado ✓ |

Después del cierre:

- Las cuentas nominales quedan en **cero**.
- Capital social pasa de 500.000 a **573.000**.
- En el balance general, `resultado_acumulado` pasa a **0** y el total de
  patrimonio no cambia (573.000): la utilidad ahora está en la cuenta real.
- El estado de resultados del período **sigue mostrando** los 550.000 de
  ingresos, porque excluye los asientos de cierre.

Solo un **admin** puede cerrar: es una operación que reescribe la lectura de
todo un período.

---

## 9. Autenticación, roles y permisos

### Cómo funciona el login

1. `POST /auth/login` con `username` (el **email**) y `password`, como
   formulario (`application/x-www-form-urlencoded`, lo exige el estándar
   OAuth2).
2. El backend verifica el hash bcrypt y devuelve un **JWT** firmado con
   `SECRET_KEY` (HS256), válido 8 horas por defecto.
3. El cliente manda ese token en cada request: `Authorization: Bearer <token>`.

> **La confusión más común:** el campo se llama `username`, pero espera el
> **email**, no el nombre del usuario. El síntoma de equivocarse es un `401`
> idéntico al de contraseña incorrecta. El `summary` del endpoint lo aclara
> en `/docs`.

El email se normaliza a minúsculas al registrar **y al buscar**, así
`Juan@x.com` y `juan@x.com` son el mismo usuario, y registrar `DUP@x.com`
cuando ya existe `dup@x.com` da `409` en lugar de crear dos cuentas.

### Los tres roles

| Rol | Leer reportes y datos | Cargar cuentas y asientos | Cerrar ejercicio | Administrar usuarios |
|---|:---:|:---:|:---:|:---:|
| **admin** | ✅ | ✅ | ✅ | ✅ |
| **contador** | ✅ | ✅ | ❌ | ❌ |
| **lector** | ✅ | ❌ | ❌ | ❌ |

En el código, `app/models/usuario.py` y `app/api/deps.py`:

```python
ROLES_ESCRITURA = (RolUsuario.ADMIN, RolUsuario.CONTADOR)

requiere_escritura = requiere_rol(ROLES_ESCRITURA)   # cuentas, asientos
requiere_admin     = requiere_rol([RolUsuario.ADMIN]) # cierres, usuarios
```

Un usuario autenticado pero sin permiso recibe **`403`**, no `401`: son cosas
distintas y conviene distinguirlas ("no iniciaste sesión" vs. "tu rol no
alcanza").

### El arranque del sistema (*bootstrap*)

Hay un problema circular: crear usuarios requiere ser admin, pero al
principio no hay ningún usuario. La solución:

```python
es_bootstrap = crud.usuario.sistema_sin_usuarios(db)
...
# En el bootstrap se ignora el rol pedido: si el primer usuario pudiera
# crearse como 'lector', el sistema quedaría sin ningún admin y sin
# forma de crear uno.
rol = RolUsuario.ADMIN if es_bootstrap else usuario_in.rol
```

Mientras no exista ningún usuario, `/auth/registrar` es público y crea un
**admin** (incluso si se pide otro rol). Desde el segundo usuario, exige un
admin autenticado.

### El sistema nunca se queda sin admin

Está garantizado sin necesidad de contar admins: `requiere_admin` asegura
que quien ejecuta la acción es un admin activo, y un admin **no puede
degradarse, desactivarse ni eliminarse a sí mismo**. Como el objetivo
siempre es otro usuario, después de cualquier operación queda en pie al
menos quien la ejecutó.

Importa porque no habría forma de recuperarse: sin admins nadie puede crear
usuarios, y el registro público solo se reabre si no queda **ningún**
usuario.

### Borrar vs. desactivar

Un usuario con asientos o cierres a su nombre **no se puede borrar**
(`409`): se perdería la trazabilidad de quién cargó qué. En ese caso se lo
**desactiva** (`activo = false`): no puede entrar más, pero su historial
queda intacto.

### Los dos esquemas de `/docs`

El botón **Authorize** ofrece dos formas, ambas sobre el mismo header:

- **OAuth2PasswordBearer** — email + contraseña; Swagger hace el login solo.
- **HTTPBearer** — pegar un token ya obtenido, sin re-tipear credenciales.

Los dos se declaran con `auto_error=False` para que fallar uno no corte la
petición que el otro resolvió; el `401` lo emite `get_current_user`.

### `SECRET_KEY` en producción

El valor por defecto **está publicado en el repositorio**: sirve para
desarrollo, pero con él cualquiera que haya visto el código podría firmarse
un token de admin. Por eso, con `ENTORNO=produccion` la app **se niega a
arrancar** si `SECRET_KEY` sigue siendo el de ejemplo:

```bash
ENTORNO=produccion SECRET_KEY=$(openssl rand -hex 32) docker compose up -d
```

Es preferible que el proceso no levante a que levante inseguro y nadie lo
note.

---

## 10. La interfaz web

React 19 + Vite, en `frontend/`.

### Pantallas

| Ruta | Archivo | Qué hace |
|---|---|---|
| `/cuentas` | `PlanCuentas.jsx` | Árbol del plan de cuentas; alta, edición y baja |
| `/libro-mayor/:cuentaId` | `LibroMayor.jsx` | Movimientos de una cuenta con saldo corriente |
| `/asientos` | `Asientos.jsx` | Listado con filtros, reversión y borrado |
| — | `AsientoNuevo.jsx` | Formulario de carga con validación en vivo |
| `/balance-comprobacion` | `BalanceComprobacion.jsx` | Reporte + descarga CSV |
| `/estado-resultados` | `EstadoResultados.jsx` | Reporte + descarga CSV |
| `/balance-general` | `BalanceGeneral.jsx` | Reporte + descarga CSV |
| `/cierres` | `Cierres.jsx` | Historial y ejecución del cierre |
| `/usuarios` | `Usuarios.jsx` | Administración de usuarios (solo admin) |
| — | `Login.jsx` | Pantalla de ingreso |

### El cliente de API

`frontend/src/api/client.js` centraliza todas las llamadas:

- Agrega el header `Authorization` si hay token guardado.
- **Maneja el 401 en un solo lugar:** borra el token y avisa a la app para
  que cierre la sesión, en vez de que cada pantalla tenga que manejarlo.
- Traduce los errores `422` de FastAPI (que vienen como lista de errores de
  validación) a un mensaje legible.
- Descarta de la *query string* los parámetros vacíos, nulos o indefinidos.

**La descarga de CSV no puede ser un `<a href>` común:** la API exige el
header `Authorization`, que el navegador no manda en una navegación normal
(daría 401). Se pide con `fetch` y se dispara la descarga desde un *blob*.

### Validación en vivo al cargar asientos

`AsientoNuevo.jsx` valida antes de enviar, replicando las reglas del
backend: muestra si el asiento está balanceado o la diferencia que falta,
impide que una línea tenga débito y crédito a la vez (escribir en uno limpia
el otro), y mantiene el botón deshabilitado hasta que todo esté correcto.

Los montos se comparan **en centavos (enteros)**:

```js
// Los montos se comparan en centavos (enteros) y no en float: sumar 0.1 + 0.2
// en punto flotante da 0.30000000000000004, y un asiento perfectamente
// balanceado podría marcarse como descuadrado.
function aCentavos(valor) { ... Math.round(numero * 100) }
```

### Sin CORS

El cliente arma las URLs con `window.location.origin`, o sea que llama al
mismo origen desde el que se sirvió la página. Por eso no hay configuración
de CORS en ningún lado:

- **En desarrollo:** el dev server de Vite proxea `/api` y `/health` al
  backend (`vite.config.js`).
- **En producción:** FastAPI sirve el bundle compilado, así que es
  literalmente el mismo origen.

### El fallback de la SPA

Como el ruteo es del lado del cliente (`BrowserRouter`), al recargar
`/asientos` el backend tiene que devolver el `index.html` y dejar que React
resuelva la ruta. Eso está en `app/main.py`, con dos precauciones:

```python
# Sin este corte, una ruta /api inexistente devolvería el index.html
# con 200 en vez de un 404, y el cliente recibiría HTML donde espera
# JSON — un error mucho más difícil de diagnosticar.
if ruta.startswith("api/"):
    raise HTTPException(status_code=404, detail="Not Found")

archivo = (FRONTEND_DIST / ruta).resolve()
# is_relative_to corta el path traversal (?ruta=../../etc/passwd).
if ruta and archivo.is_file() and archivo.is_relative_to(FRONTEND_DIST):
    return FileResponse(archivo)
```

Si no existe el bundle (desarrollo con Vite, o CI que solo corre el
backend), la app funciona igual, sin servir la interfaz.

---

## 11. Tests

**102 tests de backend** (pytest) y **20 de frontend** (Vitest), todos en CI.
Son 100 funciones `def test_`; `pytest` reporta 102 porque una está
parametrizada con tres casos.

### Backend

```bash
pytest
```

Corren contra **SQLite en memoria**, sin necesidad de Docker ni PostgreSQL
levantado, usando un `TestClient` de FastAPI con `get_db` sobrescrito por
sesión de test: cada test parte de una base vacía.

| Archivo | Tests | Qué cubre |
|---|---:|---|
| `test_asientos.py` | 19 | Partida doble, cuentas sumarias/inactivas, numeración, reversión completa, filtros y paginación |
| `test_roles.py` | 14 | El primer usuario es admin aunque pida otro rol, el registro se cierra, y qué puede hacer cada rol |
| `test_auth.py` | 13 | Registro/login, email insensible a mayúsculas, los dos esquemas de `/docs` |
| `test_cierre.py` | 12 | Que el balance siga cuadrando después de cerrar, que el estado de resultados siga mostrando el período, segundo cierre, pérdida y utilidad cero |
| `test_usuarios.py` | 9 | Administración, bloqueo de auto-modificación, borrado con historial |
| `test_cuentas.py` | 7 | Jerarquía, el auto-marcado de sumaria, bloqueos de borrado |
| `test_libro_mayor.py` | 6 | Saldo corriente según naturaleza, saldo inicial |
| `test_spa.py` | 5 | Servido del bundle, fallback, 404 de `/api`, path traversal |
| `test_balance_comprobacion.py` | 4 | Cuentas sin movimientos, `balanceado`, el cero negativo |
| `test_estado_resultados.py` | 4 | Utilidad bruta/neta, omisión de cuentas sin actividad |
| `test_config.py` | 4 | Que producción rechace la `SECRET_KEY` de ejemplo |
| `test_balance_general.py` | 3 | Escenario completo donde `activo = pasivo + patrimonio` |

`tests/conftest.py::plan_cuentas` arma un plan mínimo con los seis tipos de
cuenta, reutilizado por los módulos de reportes.

### Frontend

```bash
cd frontend && npm test
```

| Archivo | Qué cubre |
|---|---|
| `client.test.js` | Header `Authorization`, login como formulario, el 401 que cierra sesión, mensajes de error 422, descarte de params vacíos |
| `AsientoNuevo.test.jsx` | Detección de balance, exclusión débito/crédito, que no descuadre por `0.1 + 0.2`, que solo viajen las líneas con datos |
| `Login.test.jsx` | Login exitoso guardando el token, error sin dejar la sesión a medias |

**Requiere Node 22+.** jsdom 30 usa APIs de undici que no existen en Node 20
(`webidl.util.markAsUncloneable`) y los tests no arrancan; está declarado en
`engines` de `package.json`.

`src/test/setup.js` instala un **`localStorage` propio en memoria** en lugar
de usar el de jsdom. Node 26 expone un `localStorage` nativo experimental
que queda deshabilitado sin `--localstorage-file` y termina tapando al de
jsdom. Sin esta implementación propia, los tests pasarían en CI (Node 22) y
fallarían en una máquina con Node 26.

---

## 12. Infraestructura: Docker, migraciones y CI

### Migraciones

Siete migraciones de Alembic, aplicadas en orden por el contenedor al
arrancar:

| Revisión | Qué hace |
|---|---|
| `0001` | Crea `cuentas` |
| `0002` | Crea `asientos` y `movimientos_contables` |
| `0003` | Agrega `reversa_de_id` a `asientos` (reversión) |
| `0004` | Crea `usuarios` |
| `0005` | Agrega `usuario_id` a `asientos` (auditoría) |
| `0006` | Agrega `rol` a `usuarios` |
| `0007` | Crea `cierres` y agrega `es_cierre` a `asientos` |

**Una trampa que dejó comentario en `0006`:** SQLAlchemy guarda el *nombre*
del miembro del enum (`'CONTADOR'`), no su valor (`'contador'`). Escribir el
valor en minúscula inserta datos que el ORM después no puede leer
(`"'admin' is not among the defined enum values"`). Hay un test específico
que valida esos literales, porque la suite no ejecuta las migraciones.

Esa misma migración promueve a **admin** a los usuarios que ya existían: si
quedaran como contador, nadie podría dar de alta a nadie y el sistema
quedaría sin administración.

### Docker

`Dockerfile` **multi-etapa**:

1. `node:22-slim` — instala dependencias y compila el frontend.
2. `python:3.12-slim` — instala las dependencias de Python, copia el código
   y trae el `dist` de la etapa anterior.

El `dist` se toma de la etapa de build y **no del host**, así el build no
depende de que alguien haya corrido `npm run build` localmente ni de que su
`dist` esté actualizado.

No hay un servicio nginx aparte: como el cliente necesita el mismo origen
que la API, un nginx habría significado un contenedor más y configurar CORS
o un proxy, sin ganar nada a esta escala.

### CI

`.github/workflows/ci.yml`, en cada push y PR a `main`:

| Job | Pasos |
|---|---|
| **Backend** | `pip install` → `pytest` sobre Python 3.12, la misma versión del Dockerfile |
| **Frontend** | `npm ci` → `lint` (oxlint) → `test` (Vitest) → `build` sobre Node 22 |

No hace falta levantar PostgreSQL como *service*: la suite usa SQLite en
memoria.

---

## 13. Recorrido completo con datos reales

Este es el estado del sistema con los datos de demostración cargados:
**22 asientos** de un negocio chico entre enero y marzo de 2026.

### Las operaciones registradas

| Fecha | Operación | Débito | Crédito | Importe |
|---|---|---|---|---:|
| 02/01 | Aporte de capital inicial | Caja | Capital social | 500.000 |
| 05/01 | Depósito en cuenta bancaria | Banco | Caja | 300.000 |
| 10/01 | Compra de mercaderías a crédito | Mercaderías | Proveedores | 180.000 |
| 15/01 | Venta al contado | Caja | Ventas | 120.000 |
| 15/01 | Costo de esa venta | Costo mercaderías | Mercaderías | 70.000 |
| 20/01 | Venta a crédito | Cuentas por cobrar | Ventas | 95.000 |
| 20/01 | Costo de esa venta | Costo mercaderías | Mercaderías | 55.000 |
| 25/01 | Alquiler de enero | Alquiler | Banco | 45.000 |
| 31/01 | Sueldos de enero | Sueldos | Sueldos a pagar | 80.000 |
| 05/02 | Pago parcial a proveedores | Proveedores | Banco | 100.000 |
| 08/02 | Compra de mercaderías a crédito | Mercaderías | Proveedores | 150.000 |
| 10/02 | Cobro a cliente | Caja | Cuentas por cobrar | 50.000 |
| 15/02 | Luz, agua e internet | Servicios | Caja | 12.000 |
| 18/02 | **Venta cargada por error** | Caja | Ventas | 99.999 |
| 19/02 | **Reversión del error** | Ventas | Caja | 99.999 |
| 02/03 | Compra de mercaderías al contado | Mercaderías | Caja | 120.000 |
| 05/03 | Venta al contado | Caja | Ventas | 190.000 |
| 05/03 | Costo de esa venta | Costo mercaderías | Mercaderías | 98.000 |
| 12/03 | Venta a crédito | Cuentas por cobrar | Ventas | 145.000 |
| 12/03 | Costo de esa venta | Costo mercaderías | Mercaderías | 72.000 |
| 20/03 | Pago de sueldos de enero | Sueldos a pagar | Banco | 80.000 |
| 25/03 | Alquiler de marzo | Alquiler | Caja | 45.000 |

Notá el par 18/02 y 19/02: el asiento erróneo **no se borró ni se editó**.
Se generó una reversión con los importes invertidos, y los dos quedan
visibles en el libro mayor. Eso es auditoría: se ve el error *y* su
corrección.

### Estado de resultados (todo el período)

| Concepto | Importe |
|---|---:|
| Ventas | 550.000 |
| **Total ingresos** | **550.000** |
| Costo de mercaderías vendidas | 295.000 |
| **Utilidad bruta** | **255.000** |
| Sueldos | 80.000 |
| Alquiler | 90.000 |
| Servicios | 12.000 |
| **Total gastos** | **182.000** |
| **Utilidad neta** | **73.000** |

Los 550.000 de ventas son 120.000 + 95.000 + 190.000 + 145.000. La venta
errónea de 99.999 **no aparece**: su reversión la cancela exactamente.

### Balance general

| Activo | Importe | | Pasivo y Patrimonio | Importe |
|---|---:|---|---|---:|
| Caja | 383.000 | | Proveedores | 230.000 |
| Banco | 75.000 | | Sueldos a pagar | 0 |
| Cuentas por cobrar | 190.000 | | **Total pasivo** | **230.000** |
| Mercaderías | 155.000 | | Capital social | 500.000 |
| | | | Resultado acumulado | 73.000 |
| | | | **Total patrimonio** | **573.000** |
| **Total activo** | **803.000** | | **Total pasivo + patrimonio** | **803.000** |

`balanceado: true` — la ecuación fundamental se cumple.

Fijate en **Resultado acumulado: 73.000**. No es una cuenta del plan: es el
resultado de las cuentas nominales, calculado en vivo, porque el ejercicio
todavía no se cerró. Coincide exactamente con la utilidad neta del estado de
resultados. Si se cerrara el ejercicio contra Capital social, esa línea
pasaría a 0 y Capital social pasaría a 573.000 — el total no cambia.

### Un detalle contable que vale la pena

Las compras de mercadería (180.000 + 150.000 + 120.000 = 450.000) **no
afectan la utilidad**. Comprar stock es cambiar un activo por otro, no un
gasto. Lo que impacta el resultado es el **costo de lo vendido** (295.000),
registrado en asientos aparte al momento de cada venta. La diferencia,
155.000, es el stock que quedó en el activo.

---

## 14. Decisiones de diseño

Las decisiones no obvias, con su motivo.

### Los asientos no se editan: se reversan

No hay `PATCH /asientos`. Un asiento mal cargado se corrige con un
contra-asiento que invierte débitos y créditos. El saldo neto vuelve a cero,
pero **los dos movimientos quedan visibles** en el libro mayor: se ve el
error original y su corrección, no se lo esconde. Es la práctica contable
estándar y da auditoría completa.

Reglas: un asiento se reversa **una sola vez** (`409` si ya tiene reversión),
se revalidan las cuentas involucradas (por si alguna se desactivó), y un
asiento ya reversado **no se puede borrar**.

### Validación de partida doble en dos capas

1. **En el esquema Pydantic** (`AsientoCreate`): mínimo 2 movimientos, cada
   uno con débito **o** crédito, y `sum(débitos) == sum(créditos)`. Devuelve
   `422` con un mensaje claro.
2. **En la base de datos** (`CHECK` constraints): montos no negativos, no
   ambos lados en una línea, al menos uno mayor a cero.

La segunda capa es defensa ante escrituras que no pasen por la API.

### `Decimal` y el cero negativo

`Decimal` conserva el signo al multiplicar por −1: `-1 * Decimal("0")` da
`Decimal("-0")`. Eso hacía que una cuenta acreedora con saldo neto cero
apareciera como `"-0"` en los reportes. La solución:

```python
def sin_cero_negativo(valor):
    return valor + Decimal("0")   # Decimal('-0') + Decimal('0') == Decimal('0')
```

### Un solo `GROUP BY` en lugar de iterar

`sumar_por_cuenta()` agrega débitos y créditos de todas las cuentas con una
sola consulta SQL. Se extrajo a `agregados.py` cuando el mismo cálculo
empezó a repetirse en el tercer y cuarto reporte.

### `es_cierre`: el mismo dato, dos lecturas

El mismo asiento de cierre se **excluye** del estado de resultados y se
**incluye** en el balance general. No es una inconsistencia: son dos
preguntas distintas ("qué pasó en el período" vs. "cuánto hay hoy"), y cada
reporte necesita lo contrario del otro. Está documentado en el propio modelo
para que nadie lo "arregle" por error.

### Baja lógica, no borrado

Cuentas y usuarios tienen `activa`/`activo`. Una cuenta inactiva no admite
asientos nuevos pero conserva su historial; un usuario inactivo no puede
entrar pero sus asientos siguen atribuidos. Borrar de verdad solo se permite
cuando no hay historial que perder.

### Errores del dominio como excepciones propias

El CRUD levanta `CuentaConHijasError`, `AsientoYaReversadoError`,
`PeriodoYaCerradoError`, etc., y la capa HTTP las traduce a códigos. Así la
lógica contable no depende de FastAPI y se puede testear sola.

---

## 15. Limitaciones conocidas

Honestidad sobre lo que **no** está resuelto.

### Numeración de asientos bajo concurrencia

El número se calcula como `MAX(numero) + 1` dentro de la transacción. Con
dos escrituras simultáneas pueden colisionar: el `UNIQUE` lo evita pasar
silenciosamente, pero haría fallar la transacción. Para producción con
varios escritores conviene una secuencia de base de datos o
`SELECT ... FOR UPDATE`.

### No se puede cambiar la contraseña

No hay endpoint de cambio ni de recuperación, y un admin tampoco puede
resetearla (solo puede cambiar `rol` y `activo`). Si un usuario olvida su
contraseña, la única salida es borrarlo y crearlo de nuevo — y eso no se
puede si ya cargó asientos. **Es el hueco operativo más importante.**

### Sin auxiliares por tercero

Las cuentas por cobrar y proveedores son cuentas globales: no se puede saber
cuánto debe *cada* cliente. Haría falta un subsistema de auxiliares.

### Un solo ejercicio, una sola empresa, una sola moneda

No hay separación por empresa, ni manejo de moneda extranjera, ni
ejercicios contables como entidad (el cierre es un evento con fecha, no un
período con apertura y cierre formales).

### Sin backups ni deploy

No hay scripts de respaldo de la base ni configuración para ningún hosting.
El sistema corre en local con Docker.

### El árbol de cuentas se arma con *lazy loading*

`GET /cuentas/arbol` carga las hijas nodo por nodo a través de la relación
ORM. Para un plan de cuentas muy grande conviene reemplazarlo por una
consulta recursiva (CTE); está anotado en el código.

---

*Documentación generada a partir del código en `main`. Los importes y
saldos del recorrido salen del sistema corriendo con los datos de
demostración.*
