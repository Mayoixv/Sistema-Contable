import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { api, getToken } from '../api/client'
import { AuthProvider } from '../auth/AuthContext'
import { useAuth } from '../auth/contexto'
import Login from './Login'

/** Muestra el email del usuario logueado, para observar el estado del contexto. */
function Sesion() {
  const { usuario } = useAuth()
  return usuario ? <p>Sesión de {usuario.email}</p> : <Login />
}

function montar() {
  render(
    <AuthProvider>
      <Sesion />
    </AuthProvider>,
  )
}

async function completarLogin(usuario, email = 'ana@example.com', password = 'secreta') {
  await usuario.type(screen.getByLabelText(/email/i), email)
  await usuario.type(screen.getByLabelText(/contraseña/i), password)
  await usuario.click(screen.getByRole('button', { name: /entrar/i }))
}

describe('Login', () => {
  it('con credenciales válidas guarda el token y deja la sesión iniciada', async () => {
    const usuario = userEvent.setup()
    vi.spyOn(api, 'login').mockResolvedValue({ access_token: 'token-nuevo' })
    vi.spyOn(api, 'me').mockResolvedValue({ email: 'ana@example.com', rol: 'contador' })
    montar()

    await completarLogin(usuario)

    expect(await screen.findByText(/sesión de ana@example.com/i)).toBeInTheDocument()
    expect(api.login).toHaveBeenCalledWith('ana@example.com', 'secreta')
    expect(getToken()).toBe('token-nuevo')
  })

  it('muestra el mensaje del backend si las credenciales son incorrectas', async () => {
    const usuario = userEvent.setup()
    vi.spyOn(api, 'login').mockRejectedValue(new Error('Email o contraseña incorrectos'))
    montar()

    await completarLogin(usuario, 'ana@example.com', 'mala')

    expect(await screen.findByText(/email o contraseña incorrectos/i)).toBeInTheDocument()
    // Sin token guardado: la sesión no debe quedar a medias.
    expect(getToken()).toBeNull()
    expect(screen.getByRole('button', { name: /entrar/i })).toBeInTheDocument()
  })

  it('vuelve a habilitar el botón después de un error, para poder reintentar', async () => {
    const usuario = userEvent.setup()
    vi.spyOn(api, 'login').mockRejectedValue(new Error('Email o contraseña incorrectos'))
    montar()

    await completarLogin(usuario, 'ana@example.com', 'mala')

    expect(await screen.findByRole('button', { name: /entrar/i })).toBeEnabled()
  })
})
