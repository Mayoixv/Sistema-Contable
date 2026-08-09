import { useCallback, useEffect, useState } from 'react'
import { api, clearToken, getToken, onSesionExpirada, setToken } from '../api/client'
import { AuthContext } from './contexto'

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null)
  // "cargando" evita el parpadeo de la pantalla de login al recargar la
  // página: hay token guardado, pero todavía no sabemos si sigue siendo
  // válido hasta que responda /auth/me.
  const [cargando, setCargando] = useState(Boolean(getToken()))

  const logout = useCallback(() => {
    clearToken()
    setUsuario(null)
  }, [])

  useEffect(() => {
    onSesionExpirada(() => setUsuario(null))
  }, [])

  useEffect(() => {
    if (!getToken()) return
    api
      .me()
      .then(setUsuario)
      .catch(() => clearToken())
      .finally(() => setCargando(false))
  }, [])

  const login = useCallback(async (email, password) => {
    const { access_token: token } = await api.login(email, password)
    setToken(token)
    setUsuario(await api.me())
  }, [])

  const puedeEscribir = usuario?.rol === 'admin' || usuario?.rol === 'contador'
  const esAdmin = usuario?.rol === 'admin'

  return (
    <AuthContext.Provider value={{ usuario, cargando, login, logout, puedeEscribir, esAdmin }}>
      {children}
    </AuthContext.Provider>
  )
}
