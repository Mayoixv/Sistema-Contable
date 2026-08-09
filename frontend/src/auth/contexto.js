import { createContext, useContext } from 'react'

// El contexto y el hook viven acá, separados del componente `AuthProvider`:
// un archivo que exporta componentes y no-componentes a la vez rompe el Fast
// Refresh de Vite (al editarlo recarga la página entera en vez de conservar
// el estado).
export const AuthContext = createContext(null)

export function useAuth() {
  const contexto = useContext(AuthContext)
  if (!contexto) throw new Error('useAuth debe usarse dentro de <AuthProvider>')
  return contexto
}
