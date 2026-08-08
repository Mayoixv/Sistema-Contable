// Los montos viajan como string desde el backend (Decimal serializado) para
// no perder precisión; se formatean solo para mostrarlos.
const formateador = new Intl.NumberFormat('es-AR', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

export function formatearMonto(valor) {
  if (valor === null || valor === undefined || valor === '') return '—'
  const numero = Number(valor)
  if (Number.isNaN(numero)) return String(valor)
  if (numero === 0) return '—'
  return formateador.format(numero)
}
