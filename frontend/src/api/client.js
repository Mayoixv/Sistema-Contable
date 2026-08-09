const TOKEN_KEY = 'sistema-contable:token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export class ApiError extends Error {
  constructor(mensaje, status) {
    super(mensaje)
    this.status = status
  }
}

// Se avisa a la app cuando el backend rechaza el token (expiró, o el usuario
// fue desactivado) para que cierre la sesión desde un solo lugar, en vez de
// que cada pantalla tenga que manejar el 401.
let alRecibir401 = () => {}
export function onSesionExpirada(callback) {
  alRecibir401 = callback
}

function mensajeDeError(cuerpo, status) {
  const detail = cuerpo?.detail
  if (typeof detail === 'string') return detail
  // Los 422 de FastAPI traen una lista de errores de validación.
  if (Array.isArray(detail)) {
    return detail
      .map((e) => {
        const campo = (e.loc ?? []).filter((p) => p !== 'body').join('.')
        return campo ? `${campo}: ${e.msg}` : e.msg
      })
      .join(' · ')
  }
  return `Error ${status}`
}

async function request(path, { method = 'GET', body, params, form } = {}) {
  const url = new URL(path, window.location.origin)
  for (const [clave, valor] of Object.entries(params ?? {})) {
    if (valor !== undefined && valor !== null && valor !== '') {
      url.searchParams.set(clave, valor)
    }
  }

  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  let payload
  if (form) {
    headers['Content-Type'] = 'application/x-www-form-urlencoded'
    payload = new URLSearchParams(form).toString()
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }

  const res = await fetch(url, { method, headers, body: payload })

  if (res.status === 401) {
    clearToken()
    alRecibir401()
  }

  if (res.status === 204) return null

  const esJson = res.headers.get('content-type')?.includes('application/json')
  const cuerpo = esJson ? await res.json() : await res.text()

  if (!res.ok) {
    throw new ApiError(mensajeDeError(cuerpo, res.status), res.status)
  }
  return cuerpo
}

/**
 * Descarga un reporte en CSV.
 *
 * No se puede usar un `<a href>` común: la API exige el header
 * `Authorization`, que el navegador no manda en una navegación normal (daría
 * 401). Se pide con fetch y se dispara la descarga desde un blob.
 */
export async function descargarCsv(path, { params, nombreArchivo } = {}) {
  const url = new URL(path, window.location.origin)
  for (const [clave, valor] of Object.entries(params ?? {})) {
    if (valor !== undefined && valor !== null && valor !== '') {
      url.searchParams.set(clave, valor)
    }
  }
  url.searchParams.set('formato', 'csv')

  const token = getToken()
  const res = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (res.status === 401) {
    clearToken()
    alRecibir401()
  }
  if (!res.ok) throw new ApiError(`No se pudo descargar el CSV (${res.status})`, res.status)

  const blob = await res.blob()
  const objectUrl = URL.createObjectURL(blob)
  const enlace = document.createElement('a')
  enlace.href = objectUrl
  enlace.download = nombreArchivo
  document.body.appendChild(enlace)
  enlace.click()
  enlace.remove()
  URL.revokeObjectURL(objectUrl)
}

export const api = {
  // El backend usa OAuth2PasswordRequestForm: el login va como formulario
  // (no JSON) y el campo se llama "username" aunque lleve el email.
  login: (email, password) =>
    request('/api/v1/auth/login', {
      method: 'POST',
      form: { username: email, password },
    }),
  me: () => request('/api/v1/auth/me'),
  registrar: (datos) => request('/api/v1/auth/registrar', { method: 'POST', body: datos }),

  cuentas: {
    listar: (params) => request('/api/v1/cuentas/', { params }),
    arbol: () => request('/api/v1/cuentas/arbol'),
    crear: (datos) => request('/api/v1/cuentas/', { method: 'POST', body: datos }),
    actualizar: (id, datos) =>
      request(`/api/v1/cuentas/${id}`, { method: 'PATCH', body: datos }),
    eliminar: (id) => request(`/api/v1/cuentas/${id}`, { method: 'DELETE' }),
  },

  asientos: {
    listar: (params) => request('/api/v1/asientos/', { params }),
    obtener: (id) => request(`/api/v1/asientos/${id}`),
    crear: (datos) => request('/api/v1/asientos/', { method: 'POST', body: datos }),
    reversar: (id, fecha) =>
      request(`/api/v1/asientos/${id}/reversar`, { method: 'POST', params: { fecha } }),
    eliminar: (id) => request(`/api/v1/asientos/${id}`, { method: 'DELETE' }),
  },

  reportes: {
    libroMayor: (cuentaId, params) => request(`/api/v1/libro-mayor/${cuentaId}`, { params }),
    balanceComprobacion: (params) => request('/api/v1/balance-comprobacion/', { params }),
    estadoResultados: (params) => request('/api/v1/estado-resultados/', { params }),
    balanceGeneral: (params) => request('/api/v1/balance-general/', { params }),
  },

  cierres: {
    listar: () => request('/api/v1/cierres/'),
    crear: (datos) => request('/api/v1/cierres/', { method: 'POST', body: datos }),
  },
}
