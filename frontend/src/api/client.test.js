import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  ApiError,
  api,
  clearToken,
  getToken,
  onSesionExpirada,
  setToken,
} from './client'

function respuesta(cuerpo, { status = 200, tipo = 'application/json' } = {}) {
  return {
    status,
    ok: status >= 200 && status < 300,
    headers: { get: () => tipo },
    json: async () => cuerpo,
    text: async () => String(cuerpo),
  }
}

describe('token', () => {
  it('guarda, lee y borra el token', () => {
    expect(getToken()).toBeNull()
    setToken('abc123')
    expect(getToken()).toBe('abc123')
    clearToken()
    expect(getToken()).toBeNull()
  })
})

describe('request', () => {
  beforeEach(() => {
    // Cada test define su propia respuesta; onSesionExpirada es global al
    // módulo, así que se resetea para no arrastrar el callback de otro test.
    onSesionExpirada(() => {})
  })

  it('manda el header Authorization cuando hay token', async () => {
    setToken('mi-token')
    const fetchMock = vi.fn().mockResolvedValue(respuesta({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)

    await api.me()

    const [, opciones] = fetchMock.mock.calls[0]
    expect(opciones.headers.Authorization).toBe('Bearer mi-token')
  })

  it('no manda Authorization si no hay token', async () => {
    const fetchMock = vi.fn().mockResolvedValue(respuesta({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)

    await api.me()

    const [, opciones] = fetchMock.mock.calls[0]
    expect(opciones.headers.Authorization).toBeUndefined()
  })

  it('manda el login como formulario, con el email en "username"', async () => {
    const fetchMock = vi.fn().mockResolvedValue(respuesta({ access_token: 't' }))
    vi.stubGlobal('fetch', fetchMock)

    await api.login('ana@example.com', 'secreta')

    const [, opciones] = fetchMock.mock.calls[0]
    expect(opciones.headers['Content-Type']).toBe('application/x-www-form-urlencoded')
    const enviado = new URLSearchParams(opciones.body)
    expect(enviado.get('username')).toBe('ana@example.com')
    expect(enviado.get('password')).toBe('secreta')
  })

  it('ante un 401 borra el token y avisa que la sesión expiró', async () => {
    setToken('vencido')
    const alExpirar = vi.fn()
    onSesionExpirada(alExpirar)
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(respuesta({ detail: 'no' }, { status: 401 })))

    await expect(api.me()).rejects.toThrow(ApiError)

    expect(getToken()).toBeNull()
    expect(alExpirar).toHaveBeenCalled()
  })

  it('usa el "detail" del backend como mensaje de error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(respuesta({ detail: 'La cuenta es sumaria' }, { status: 400 })),
    )

    await expect(api.cuentas.listar()).rejects.toThrow('La cuenta es sumaria')
  })

  it('arma un mensaje legible con los errores de validación 422 de FastAPI', async () => {
    const detail = [
      { loc: ['body', 'movimientos'], msg: 'no está balanceado' },
      { loc: ['body', 'fecha'], msg: 'fecha inválida' },
    ]
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(respuesta({ detail }, { status: 422 })))

    // "body" se descarta del nombre del campo por ruido.
    await expect(api.asientos.crear({})).rejects.toThrow(
      'movimientos: no está balanceado · fecha: fecha inválida',
    )
  })

  it('devuelve null en un 204 sin intentar parsear el cuerpo', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(respuesta(null, { status: 204 })))

    await expect(api.cuentas.eliminar(1)).resolves.toBeNull()
  })

  it('omite de la query los params vacíos, nulos o indefinidos', async () => {
    const fetchMock = vi.fn().mockResolvedValue(respuesta([]))
    vi.stubGlobal('fetch', fetchMock)

    await api.asientos.listar({ cuenta_id: 5, fecha_desde: '', fecha_hasta: null, skip: undefined })

    const [url] = fetchMock.mock.calls[0]
    expect(url.searchParams.get('cuenta_id')).toBe('5')
    expect(url.searchParams.has('fecha_desde')).toBe(false)
    expect(url.searchParams.has('fecha_hasta')).toBe(false)
    expect(url.searchParams.has('skip')).toBe(false)
  })
})
