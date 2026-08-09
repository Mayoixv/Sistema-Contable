import { useCallback, useState } from 'react'
import { api, descargarCsv } from '../api/client'
import FiltrosFecha from '../components/FiltrosFecha'
import { useCargar } from '../hooks/useCargar'
import { formatearMonto } from '../formato'

function Bloque({ titulo, filas, total, extra }) {
  return (
    <div className="tarjeta">
      <h3>{titulo}</h3>
      <table>
        <tbody>
          {filas.map((f) => (
            <tr key={f.cuenta_id}>
              <td>
                {f.codigo} — {f.nombre}
              </td>
              <td className="num">{formatearMonto(f.saldo)}</td>
            </tr>
          ))}
          {extra}
          {filas.length === 0 && !extra && (
            <tr>
              <td className="sutil">Sin saldos</td>
              <td />
            </tr>
          )}
          <tr className="fila-resumen">
            <td>Total</td>
            <td className="num">{formatearMonto(total)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}

export default function BalanceGeneral() {
  const [filtros, setFiltros] = useState({ fecha_corte: '' })
  const cargador = useCallback(() => api.reportes.balanceGeneral(filtros), [filtros])
  const { datos, error, cargando } = useCargar(cargador)

  return (
    <section>
      <div className="encabezado-seccion">
        <div>
          <h2>Balance general</h2>
          <p className="sutil">Saldos acumulados a la fecha de corte.</p>
        </div>
        <button
          className="secundario"
          onClick={() =>
            descargarCsv('/api/v1/balance-general/', {
              params: filtros,
              nombreArchivo: 'balance_general.csv',
            })
          }
        >
          Descargar CSV
        </button>
      </div>

      <FiltrosFecha valor={filtros} onAplicar={setFiltros} campos={['corte']} />

      {error && <p className="error">{error}</p>}
      {cargando && <p className="sutil">Cargando…</p>}

      {datos && !cargando && (
        <>
          <div className={`tarjeta banda ${datos.balanceado ? 'banda-ok' : 'banda-error'}`}>
            {datos.balanceado
              ? `✓ Activo (${formatearMonto(datos.total_activo)}) = Pasivo + Patrimonio (${formatearMonto(datos.total_pasivo_mas_patrimonio)})`
              : '⚠ El balance no cuadra.'}
          </div>

          <div className="dos-columnas">
            <Bloque titulo="Activo" filas={datos.activos} total={datos.total_activo} />
            <div>
              <Bloque titulo="Pasivo" filas={datos.pasivos} total={datos.total_pasivo} />
              <Bloque
                titulo="Patrimonio"
                filas={datos.patrimonio}
                total={datos.total_patrimonio}
                extra={
                  Number(datos.resultado_acumulado) !== 0 ? (
                    <tr>
                      <td>
                        Resultado acumulado
                        <br />
                        <span className="sutil">
                          Utilidad todavía no trasladada por un cierre de ejercicio
                        </span>
                      </td>
                      <td className="num">{formatearMonto(datos.resultado_acumulado)}</td>
                    </tr>
                  ) : null
                }
              />
            </div>
          </div>
        </>
      )}
    </section>
  )
}
