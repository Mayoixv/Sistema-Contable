import { useCallback, useEffect, useState } from 'react'

/**
 * Carga datos de la API manejando estados de carga y error.
 *
 * `cargador` debe venir memorizado con useCallback en el llamador, porque es
 * lo que dispara la recarga: si se recrea en cada render, esto entraría en
 * un bucle infinito.
 */
export function useCargar(cargador) {
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState(null)
  const [cargando, setCargando] = useState(true)

  const recargar = useCallback(async () => {
    setCargando(true)
    setError(null)
    try {
      setDatos(await cargador())
    } catch (err) {
      setError(err.message)
      setDatos(null)
    } finally {
      setCargando(false)
    }
  }, [cargador])

  useEffect(() => {
    recargar()
  }, [recargar])

  return { datos, error, cargando, recargar }
}
