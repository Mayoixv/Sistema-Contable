import { useState } from 'react'

/**
 * Filtro de rango de fechas. Mantiene un borrador local y solo avisa al
 * padre al aplicar: si notificara en cada tecla, cada dígito de una fecha
 * dispararía una consulta al backend.
 */
export default function FiltrosFecha({ valor, onAplicar, campos = ['desde', 'hasta'], children }) {
  const [borrador, setBorrador] = useState(valor)

  const vacio = { fecha_desde: '', fecha_hasta: '', fecha_corte: '' }
  const hayFiltro = Object.values(valor).some(Boolean)

  return (
    <form
      className="tarjeta filtros"
      onSubmit={(e) => {
        e.preventDefault()
        onAplicar(borrador)
      }}
    >
      {campos.includes('desde') && (
        <label>
          Desde
          <input
            type="date"
            value={borrador.fecha_desde ?? ''}
            onChange={(e) => setBorrador({ ...borrador, fecha_desde: e.target.value })}
          />
        </label>
      )}
      {campos.includes('hasta') && (
        <label>
          Hasta
          <input
            type="date"
            value={borrador.fecha_hasta ?? ''}
            onChange={(e) => setBorrador({ ...borrador, fecha_hasta: e.target.value })}
          />
        </label>
      )}
      {campos.includes('corte') && (
        <label>
          Fecha de corte
          <input
            type="date"
            value={borrador.fecha_corte ?? ''}
            onChange={(e) => setBorrador({ ...borrador, fecha_corte: e.target.value })}
          />
        </label>
      )}
      {children}
      <button type="submit">Aplicar</button>
      {hayFiltro && (
        <button
          type="button"
          className="secundario"
          onClick={() => {
            setBorrador(vacio)
            onAplicar(vacio)
          }}
        >
          Limpiar
        </button>
      )}
    </form>
  )
}
