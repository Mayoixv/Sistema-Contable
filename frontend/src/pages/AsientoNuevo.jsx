import { useMemo, useState } from 'react'
import { api } from '../api/client'
import { formatearMonto } from '../formato'

// Los montos se comparan en centavos (enteros) y no en float: sumar 0.1 + 0.2
// en punto flotante da 0.30000000000000004, y un asiento perfectamente
// balanceado podría marcarse como descuadrado.
function aCentavos(valor) {
  const numero = Number(valor)
  if (!valor || Number.isNaN(numero)) return 0
  return Math.round(numero * 100)
}

const lineaVacia = () => ({ cuenta_id: '', debito: '', credito: '', descripcion: '' })

export default function AsientoNuevo({ cuentas, onCreado, onCancelar }) {
  const hoy = new Date().toISOString().slice(0, 10)
  const [fecha, setFecha] = useState(hoy)
  const [descripcion, setDescripcion] = useState('')
  const [lineas, setLineas] = useState([lineaVacia(), lineaVacia()])
  const [error, setError] = useState(null)
  const [enviando, setEnviando] = useState(false)

  const totales = useMemo(() => {
    const debitos = lineas.reduce((acc, l) => acc + aCentavos(l.debito), 0)
    const creditos = lineas.reduce((acc, l) => acc + aCentavos(l.credito), 0)
    return { debitos, creditos, diferencia: debitos - creditos }
  }, [lineas])

  const lineasConDatos = lineas.filter(
    (l) => l.cuenta_id && (aCentavos(l.debito) > 0 || aCentavos(l.credito) > 0),
  )
  const hayAmbosLados = lineas.some(
    (l) => aCentavos(l.debito) > 0 && aCentavos(l.credito) > 0,
  )
  const balanceado = totales.diferencia === 0 && totales.debitos > 0
  const puedeEnviar =
    balanceado && lineasConDatos.length >= 2 && !hayAmbosLados && descripcion.trim() && fecha

  function actualizarLinea(indice, cambios) {
    setLineas(lineas.map((l, i) => (i === indice ? { ...l, ...cambios } : l)))
  }

  // Débito y crédito son excluyentes en una misma línea: escribir en uno
  // limpia el otro, que es la misma regla que valida el backend.
  function onMonto(indice, lado, valor) {
    actualizarLinea(indice, {
      [lado]: valor,
      [lado === 'debito' ? 'credito' : 'debito']: '',
    })
  }

  async function onSubmit(e) {
    e.preventDefault()
    setError(null)
    setEnviando(true)
    try {
      await api.asientos.crear({
        fecha,
        descripcion: descripcion.trim(),
        movimientos: lineasConDatos.map((l) => ({
          cuenta_id: Number(l.cuenta_id),
          debito: l.debito || '0',
          credito: l.credito || '0',
          descripcion: l.descripcion.trim() || null,
        })),
      })
      onCreado()
    } catch (err) {
      setError(err.message)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form className="tarjeta" onSubmit={onSubmit}>
      <h3>Nuevo asiento</h3>

      <div className="grilla-campos">
        <label>
          Fecha
          <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} required />
        </label>
        <label style={{ gridColumn: 'span 2' }}>
          Descripción
          <input
            value={descripcion}
            onChange={(e) => setDescripcion(e.target.value)}
            required
            placeholder="Venta al contado"
          />
        </label>
      </div>

      <table className="tabla-lineas">
        <thead>
          <tr>
            <th>Cuenta</th>
            <th className="num">Débito</th>
            <th className="num">Crédito</th>
            <th>Detalle</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {lineas.map((linea, i) => {
            const ambos = aCentavos(linea.debito) > 0 && aCentavos(linea.credito) > 0
            return (
              <tr key={i} className={ambos ? 'linea-invalida' : undefined}>
                <td>
                  <select
                    value={linea.cuenta_id}
                    onChange={(e) => actualizarLinea(i, { cuenta_id: e.target.value })}
                  >
                    <option value="">— elegir cuenta —</option>
                    {cuentas.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.codigo} — {c.nombre}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    className="num"
                    value={linea.debito}
                    onChange={(e) => onMonto(i, 'debito', e.target.value)}
                    placeholder="0.00"
                  />
                </td>
                <td>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    className="num"
                    value={linea.credito}
                    onChange={(e) => onMonto(i, 'credito', e.target.value)}
                    placeholder="0.00"
                  />
                </td>
                <td>
                  <input
                    value={linea.descripcion}
                    onChange={(e) => actualizarLinea(i, { descripcion: e.target.value })}
                    placeholder="(opcional)"
                  />
                </td>
                <td>
                  {lineas.length > 2 && (
                    <button
                      type="button"
                      className="enlace"
                      onClick={() => setLineas(lineas.filter((_, j) => j !== i))}
                      aria-label="Quitar línea"
                    >
                      ✕
                    </button>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
        <tfoot>
          <tr className="fila-resumen">
            <td>Totales</td>
            <td className="num">{formatearMonto(totales.debitos / 100)}</td>
            <td className="num">{formatearMonto(totales.creditos / 100)}</td>
            <td colSpan={2}>
              {totales.debitos === 0 && totales.creditos === 0 ? (
                <span className="sutil">Sin importes cargados</span>
              ) : balanceado ? (
                <span className="ok">✓ Asiento balanceado</span>
              ) : (
                <span className="desbalance">
                  Diferencia: {formatearMonto(Math.abs(totales.diferencia) / 100)}{' '}
                  {totales.diferencia > 0 ? '(faltan créditos)' : '(faltan débitos)'}
                </span>
              )}
            </td>
          </tr>
        </tfoot>
      </table>

      <button
        type="button"
        className="secundario"
        onClick={() => setLineas([...lineas, lineaVacia()])}
      >
        + Agregar línea
      </button>

      {hayAmbosLados && (
        <p className="error">
          Una línea no puede tener débito y crédito a la vez. Usá dos líneas.
        </p>
      )}
      {error && <p className="error">{error}</p>}

      <div className="acciones">
        <button type="submit" disabled={!puedeEnviar || enviando}>
          {enviando ? 'Guardando…' : 'Guardar asiento'}
        </button>
        <button type="button" className="secundario" onClick={onCancelar}>
          Cancelar
        </button>
      </div>
    </form>
  )
}
