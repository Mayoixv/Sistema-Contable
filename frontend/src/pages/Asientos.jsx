import { Fragment, useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../auth/contexto'
import { useCargar } from '../hooks/useCargar'
import { formatearMonto } from '../formato'
import AsientoNuevo from './AsientoNuevo'

const POR_PAGINA = 20

function DetalleAsiento({ asiento, cuentasPorId }) {
  return (
    <tr className="fila-detalle">
      <td colSpan={7}>
        <table className="tabla-anidada">
          <tbody>
            {asiento.movimientos.map((m) => {
              const cuenta = cuentasPorId[m.cuenta_id]
              return (
                <tr key={m.id}>
                  <td>{cuenta ? `${cuenta.codigo} — ${cuenta.nombre}` : `Cuenta #${m.cuenta_id}`}</td>
                  <td className="sutil">{m.descripcion}</td>
                  <td className="num">{formatearMonto(m.debito)}</td>
                  <td className="num">{formatearMonto(m.credito)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </td>
    </tr>
  )
}

export default function Asientos() {
  const { puedeEscribir } = useAuth()
  const [filtros, setFiltros] = useState({ fecha_desde: '', fecha_hasta: '', cuenta_id: '' })
  const [borrador, setBorrador] = useState(filtros)
  const [pagina, setPagina] = useState(0)
  const [creando, setCreando] = useState(false)
  const [expandido, setExpandido] = useState(null)
  const [cuentas, setCuentas] = useState([])
  const [accionError, setAccionError] = useState(null)

  useEffect(() => {
    api.cuentas.listar({ limit: 500 }).then(setCuentas).catch(() => setCuentas([]))
  }, [])

  const cargador = useCallback(
    () => api.asientos.listar({ ...filtros, skip: pagina * POR_PAGINA, limit: POR_PAGINA }),
    [filtros, pagina],
  )
  const { datos, error, cargando, recargar } = useCargar(cargador)

  const cuentasDetalle = cuentas.filter((c) => c.acepta_movimiento && c.activa)
  const cuentasPorId = Object.fromEntries(cuentas.map((c) => [c.id, c]))
  const total = datos?.total ?? 0
  const ultimaPagina = Math.max(0, Math.ceil(total / POR_PAGINA) - 1)

  async function accion(fn, confirmacion) {
    if (!window.confirm(confirmacion)) return
    setAccionError(null)
    try {
      await fn()
      recargar()
    } catch (err) {
      setAccionError(err.message)
    }
  }

  function aplicarFiltros(e) {
    e.preventDefault()
    setPagina(0)
    setFiltros(borrador)
  }

  return (
    <section>
      <div className="encabezado-seccion">
        <div>
          <h2>Asientos contables</h2>
          <p className="sutil">
            Un asiento no se edita: se reversa, generando uno nuevo con los importes invertidos.
          </p>
        </div>
        {puedeEscribir && !creando && (
          <button onClick={() => setCreando(true)}>Nuevo asiento</button>
        )}
      </div>

      {creando && (
        <AsientoNuevo
          cuentas={cuentasDetalle}
          onCancelar={() => setCreando(false)}
          onCreado={() => {
            setCreando(false)
            setPagina(0)
            recargar()
          }}
        />
      )}

      <form className="tarjeta filtros" onSubmit={aplicarFiltros}>
        <label>
          Desde
          <input
            type="date"
            value={borrador.fecha_desde}
            onChange={(e) => setBorrador({ ...borrador, fecha_desde: e.target.value })}
          />
        </label>
        <label>
          Hasta
          <input
            type="date"
            value={borrador.fecha_hasta}
            onChange={(e) => setBorrador({ ...borrador, fecha_hasta: e.target.value })}
          />
        </label>
        <label>
          Cuenta
          <select
            value={borrador.cuenta_id}
            onChange={(e) => setBorrador({ ...borrador, cuenta_id: e.target.value })}
          >
            <option value="">(todas)</option>
            {cuentasDetalle.map((c) => (
              <option key={c.id} value={c.id}>
                {c.codigo} — {c.nombre}
              </option>
            ))}
          </select>
        </label>
        <button type="submit">Aplicar</button>
        {Object.values(filtros).some(Boolean) && (
          <button
            type="button"
            className="secundario"
            onClick={() => {
              const vacio = { fecha_desde: '', fecha_hasta: '', cuenta_id: '' }
              setBorrador(vacio)
              setFiltros(vacio)
              setPagina(0)
            }}
          >
            Limpiar
          </button>
        )}
      </form>

      {error && <p className="error">{error}</p>}
      {accionError && <p className="error">{accionError}</p>}
      {cargando && <p className="sutil">Cargando…</p>}

      {datos && !cargando && (
        <>
          <div className="tarjeta">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Fecha</th>
                  <th>Descripción</th>
                  <th className="num">Importe</th>
                  <th>Autor</th>
                  <th>Estado</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {datos.items.map((a) => {
                  const importe = a.movimientos.reduce((acc, m) => acc + Number(m.debito), 0)
                  const abierto = expandido === a.id
                  return (
                    <Fragment key={a.id}>
                      <tr>
                        <td>
                          <button
                            className="enlace"
                            onClick={() => setExpandido(abierto ? null : a.id)}
                          >
                            {abierto ? '▾' : '▸'} {a.numero}
                          </button>
                        </td>
                        <td>{a.fecha}</td>
                        <td>{a.descripcion}</td>
                        <td className="num">{formatearMonto(importe)}</td>
                        <td className="sutil">{a.usuario_email ?? '—'}</td>
                        <td>
                          {a.reversado_por_id && (
                            <span className="etiqueta etiqueta-inactiva">reversado</span>
                          )}
                          {a.reversa_de_id && (
                            <span className="etiqueta">reversión</span>
                          )}
                        </td>
                        <td className="acciones-fila">
                          {puedeEscribir && !a.reversado_por_id && (
                            <>
                              <button
                                className="enlace"
                                onClick={() =>
                                  accion(
                                    () => api.asientos.reversar(a.id),
                                    `¿Reversar el asiento #${a.numero}? Se creará un asiento nuevo con los importes invertidos.`,
                                  )
                                }
                              >
                                Reversar
                              </button>
                              <button
                                className="enlace peligro"
                                onClick={() =>
                                  accion(
                                    () => api.asientos.eliminar(a.id),
                                    `¿Eliminar el asiento #${a.numero}? Esta acción no se puede deshacer.`,
                                  )
                                }
                              >
                                Eliminar
                              </button>
                            </>
                          )}
                        </td>
                      </tr>
                      {abierto && (
                        <DetalleAsiento asiento={a} cuentasPorId={cuentasPorId} />
                      )}
                    </Fragment>
                  )
                })}
                {datos.items.length === 0 && (
                  <tr>
                    <td colSpan={7} className="sutil">
                      No hay asientos que coincidan con el filtro.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="paginacion">
            <span className="sutil">
              {total} asiento{total === 1 ? '' : 's'}
              {total > 0 && ` · página ${pagina + 1} de ${ultimaPagina + 1}`}
            </span>
            <div>
              <button
                className="secundario"
                disabled={pagina === 0}
                onClick={() => setPagina(pagina - 1)}
              >
                Anterior
              </button>
              <button
                className="secundario"
                disabled={pagina >= ultimaPagina}
                onClick={() => setPagina(pagina + 1)}
              >
                Siguiente
              </button>
            </div>
          </div>
        </>
      )}
    </section>
  )
}
