import { useCallback, useState } from 'react'
import { api, descargarCsv } from '../api/client'
import FiltrosFecha from '../components/FiltrosFecha'
import { useCargar } from '../hooks/useCargar'
import { formatearMonto } from '../formato'

function Seccion({ titulo, filas, total }) {
  if (filas.length === 0) {
    return (
      <tr>
        <td colSpan={2} className="sutil">
          {titulo}: sin actividad en el período
        </td>
      </tr>
    )
  }
  return (
    <>
      <tr className="fila-seccion">
        <td colSpan={2}>{titulo}</td>
      </tr>
      {filas.map((f) => (
        <tr key={f.cuenta_id}>
          <td>
            {f.codigo} — {f.nombre}
          </td>
          <td className="num">{formatearMonto(f.monto)}</td>
        </tr>
      ))}
      <tr className="fila-subtotal">
        <td>Total {titulo.toLowerCase()}</td>
        <td className="num">{formatearMonto(total)}</td>
      </tr>
    </>
  )
}

export default function EstadoResultados() {
  const [filtros, setFiltros] = useState({ fecha_desde: '', fecha_hasta: '' })
  const cargador = useCallback(() => api.reportes.estadoResultados(filtros), [filtros])
  const { datos, error, cargando } = useCargar(cargador)

  return (
    <section>
      <div className="encabezado-seccion">
        <div>
          <h2>Estado de resultados</h2>
          <p className="sutil">
            Reporte del período. Ignora los asientos de cierre, así un ejercicio ya cerrado
            sigue mostrando su actividad real.
          </p>
        </div>
        <button
          className="secundario"
          onClick={() =>
            descargarCsv('/api/v1/estado-resultados/', {
              params: filtros,
              nombreArchivo: 'estado_resultados.csv',
            })
          }
        >
          Descargar CSV
        </button>
      </div>

      <FiltrosFecha valor={filtros} onAplicar={setFiltros} />

      {error && <p className="error">{error}</p>}
      {cargando && <p className="sutil">Cargando…</p>}

      {datos && !cargando && (
        <div className="tarjeta">
          <table>
            <tbody>
              <Seccion titulo="Ingresos" filas={datos.ingresos} total={datos.total_ingresos} />
              <Seccion titulo="Costos" filas={datos.costos} total={datos.total_costos} />
              <tr className="fila-resumen">
                <td>Utilidad bruta</td>
                <td className="num">{formatearMonto(datos.utilidad_bruta)}</td>
              </tr>
              <Seccion titulo="Gastos" filas={datos.gastos} total={datos.total_gastos} />
              <tr className="fila-resumen fila-destacada">
                <td>Utilidad neta</td>
                <td className={`num ${Number(datos.utilidad_neta) < 0 ? 'negativo' : ''}`}>
                  {formatearMonto(datos.utilidad_neta)}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
