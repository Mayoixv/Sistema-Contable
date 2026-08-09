import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../auth/contexto'
import { useCargar } from '../hooks/useCargar'
import { formatearMonto } from '../formato'

function FormularioCierre({ cuentasPatrimonio, onCreado, onCancelar }) {
  const [datos, setDatos] = useState({ fecha_cierre: '', cuenta_resultado_id: '' })
  const [error, setError] = useState(null)
  const [enviando, setEnviando] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setError(null)
    setEnviando(true)
    try {
      await api.cierres.crear({
        fecha_cierre: datos.fecha_cierre,
        cuenta_resultado_id: Number(datos.cuenta_resultado_id),
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
      <h3>Cerrar ejercicio</h3>
      <p className="sutil">
        Genera un asiento que salda las cuentas de ingreso, costo y gasto contra la cuenta de
        patrimonio elegida. Solo toma la actividad posterior al último cierre.
      </p>
      <div className="grilla-campos">
        <label>
          Fecha de cierre
          <input
            type="date"
            value={datos.fecha_cierre}
            onChange={(e) => setDatos({ ...datos, fecha_cierre: e.target.value })}
            required
          />
        </label>
        <label>
          Cuenta de resultado
          <select
            value={datos.cuenta_resultado_id}
            onChange={(e) => setDatos({ ...datos, cuenta_resultado_id: e.target.value })}
            required
          >
            <option value="">— elegir cuenta de patrimonio —</option>
            {cuentasPatrimonio.map((c) => (
              <option key={c.id} value={c.id}>
                {c.codigo} — {c.nombre}
              </option>
            ))}
          </select>
        </label>
      </div>
      {cuentasPatrimonio.length === 0 && (
        <p className="error">
          No hay cuentas de patrimonio de detalle activas. Creá una en el plan de cuentas antes
          de cerrar.
        </p>
      )}
      {error && <p className="error">{error}</p>}
      <div className="acciones">
        <button type="submit" disabled={enviando || cuentasPatrimonio.length === 0}>
          {enviando ? 'Cerrando…' : 'Cerrar ejercicio'}
        </button>
        <button type="button" className="secundario" onClick={onCancelar}>
          Cancelar
        </button>
      </div>
    </form>
  )
}

export default function Cierres() {
  const { esAdmin } = useAuth()
  const [cerrando, setCerrando] = useState(false)
  const [cuentas, setCuentas] = useState([])

  useEffect(() => {
    api.cuentas.listar({ limit: 500 }).then(setCuentas).catch(() => setCuentas([]))
  }, [])

  const cargador = useCallback(() => api.cierres.listar(), [])
  const { datos, error, cargando, recargar } = useCargar(cargador)

  const cuentasPatrimonio = cuentas.filter(
    (c) => c.tipo === 'patrimonio' && c.acepta_movimiento && c.activa,
  )

  return (
    <section>
      <div className="encabezado-seccion">
        <div>
          <h2>Cierre de ejercicio</h2>
          <p className="sutil">
            Traslada el resultado del período a patrimonio. Una vez hecho no se puede cerrar
            con una fecha anterior o igual.
          </p>
        </div>
        {esAdmin && !cerrando && <button onClick={() => setCerrando(true)}>Nuevo cierre</button>}
      </div>

      {cerrando && (
        <FormularioCierre
          cuentasPatrimonio={cuentasPatrimonio}
          onCancelar={() => setCerrando(false)}
          onCreado={() => {
            setCerrando(false)
            recargar()
          }}
        />
      )}

      {error && <p className="error">{error}</p>}
      {cargando && <p className="sutil">Cargando…</p>}

      {datos && !cargando && (
        <div className="tarjeta">
          <table>
            <thead>
              <tr>
                <th>Fecha de cierre</th>
                <th>Asiento</th>
                <th className="num">Utilidad neta</th>
                <th>Registrado</th>
              </tr>
            </thead>
            <tbody>
              {datos.map((c) => (
                <tr key={c.id}>
                  <td>{c.fecha_cierre}</td>
                  <td>#{c.asiento_id}</td>
                  <td className={`num ${Number(c.utilidad_neta) < 0 ? 'negativo' : ''}`}>
                    {formatearMonto(c.utilidad_neta)}
                  </td>
                  <td className="sutil">{new Date(c.created_at).toLocaleString('es-AR')}</td>
                </tr>
              ))}
              {datos.length === 0 && (
                <tr>
                  <td colSpan={4} className="sutil">
                    Todavía no se cerró ningún ejercicio.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
