import { useCallback, useState } from 'react'
import { api, descargarCsv } from '../api/client'
import FiltrosFecha from '../components/FiltrosFecha'
import { useCargar } from '../hooks/useCargar'
import { formatearMonto } from '../formato'

export default function BalanceComprobacion() {
  const [filtros, setFiltros] = useState({ fecha_desde: '', fecha_hasta: '' })
  const cargador = useCallback(() => api.reportes.balanceComprobacion(filtros), [filtros])
  const { datos, error, cargando } = useCargar(cargador)

  return (
    <section>
      <div className="encabezado-seccion">
        <div>
          <h2>Balance de comprobación</h2>
          <p className="sutil">
            Una fila por cuenta de detalle activa, incluidas las que no tuvieron movimientos.
          </p>
        </div>
        <button
          className="secundario"
          onClick={() =>
            descargarCsv('/api/v1/balance-comprobacion/', {
              params: filtros,
              nombreArchivo: 'balance_comprobacion.csv',
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
        <>
          <div
            className={`tarjeta banda ${datos.balanceado ? 'banda-ok' : 'banda-error'}`}
          >
            {datos.balanceado
              ? '✓ La contabilidad está balanceada: los débitos igualan a los créditos.'
              : '⚠ El balance no cuadra. Algo escribió en la base sin pasar por la validación de la API.'}
          </div>

          <div className="tarjeta">
            <table>
              <thead>
                <tr>
                  <th>Código</th>
                  <th>Cuenta</th>
                  <th className="num">Saldo inicial</th>
                  <th className="num">Débito</th>
                  <th className="num">Crédito</th>
                  <th className="num">Saldo final</th>
                </tr>
              </thead>
              <tbody>
                {datos.cuentas.map((c) => (
                  <tr key={c.cuenta_id}>
                    <td>{c.codigo}</td>
                    <td>{c.nombre}</td>
                    <td className="num">{formatearMonto(c.saldo_inicial)}</td>
                    <td className="num">{formatearMonto(c.debito)}</td>
                    <td className="num">{formatearMonto(c.credito)}</td>
                    <td className="num">{formatearMonto(c.saldo_final)}</td>
                  </tr>
                ))}
                <tr className="fila-resumen">
                  <td colSpan={3}>Totales</td>
                  <td className="num">{formatearMonto(datos.total_debitos)}</td>
                  <td className="num">{formatearMonto(datos.total_creditos)}</td>
                  <td />
                </tr>
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  )
}
