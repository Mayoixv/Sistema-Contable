import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api/client'
import { formatearMonto } from '../formato'

export default function LibroMayor() {
  const { cuentaId } = useParams()
  const [rango, setRango] = useState({ fecha_desde: '', fecha_hasta: '' })
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState(null)
  const [cargando, setCargando] = useState(true)

  const cargar = useCallback(async () => {
    setCargando(true)
    setError(null)
    try {
      setDatos(await api.reportes.libroMayor(cuentaId, rango))
    } catch (err) {
      setError(err.message)
      setDatos(null)
    } finally {
      setCargando(false)
    }
  }, [cuentaId, rango])

  useEffect(() => {
    cargar()
  }, [cargar])

  return (
    <section>
      <div className="encabezado-seccion">
        <div>
          <h2>Libro mayor</h2>
          {datos && (
            <p className="sutil">
              {datos.codigo} — {datos.nombre} · cuenta {datos.naturaleza}
            </p>
          )}
        </div>
        <a
          className="boton-enlace"
          href={`/api/v1/libro-mayor/${cuentaId}?formato=csv`}
          target="_blank"
          rel="noreferrer"
        >
          Descargar CSV
        </a>
      </div>

      <form
        className="tarjeta filtros"
        onSubmit={(e) => {
          e.preventDefault()
          cargar()
        }}
      >
        <label>
          Desde
          <input
            type="date"
            value={rango.fecha_desde}
            onChange={(e) => setRango({ ...rango, fecha_desde: e.target.value })}
          />
        </label>
        <label>
          Hasta
          <input
            type="date"
            value={rango.fecha_hasta}
            onChange={(e) => setRango({ ...rango, fecha_hasta: e.target.value })}
          />
        </label>
        <button type="submit">Filtrar</button>
        {(rango.fecha_desde || rango.fecha_hasta) && (
          <button
            type="button"
            className="secundario"
            onClick={() => setRango({ fecha_desde: '', fecha_hasta: '' })}
          >
            Limpiar
          </button>
        )}
      </form>

      {error && <p className="error">{error}</p>}
      {cargando && <p className="sutil">Cargando…</p>}

      {datos && !cargando && (
        <div className="tarjeta">
          <table>
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Asiento</th>
                <th>Descripción</th>
                <th className="num">Débito</th>
                <th className="num">Crédito</th>
                <th className="num">Saldo</th>
              </tr>
            </thead>
            <tbody>
              <tr className="fila-resumen">
                <td colSpan={5}>Saldo inicial</td>
                <td className="num">{formatearMonto(datos.saldo_inicial)}</td>
              </tr>
              {datos.movimientos.map((m, i) => (
                <tr key={`${m.asiento_id}-${i}`}>
                  <td>{m.fecha}</td>
                  <td>#{m.asiento_numero}</td>
                  <td>{m.descripcion}</td>
                  <td className="num">{formatearMonto(m.debito)}</td>
                  <td className="num">{formatearMonto(m.credito)}</td>
                  <td className="num">{formatearMonto(m.saldo)}</td>
                </tr>
              ))}
              {datos.movimientos.length === 0 && (
                <tr>
                  <td colSpan={6} className="sutil">
                    Sin movimientos en el período.
                  </td>
                </tr>
              )}
              <tr className="fila-resumen">
                <td colSpan={3}>Totales</td>
                <td className="num">{formatearMonto(datos.total_debitos)}</td>
                <td className="num">{formatearMonto(datos.total_creditos)}</td>
                <td className="num">{formatearMonto(datos.saldo_final)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
