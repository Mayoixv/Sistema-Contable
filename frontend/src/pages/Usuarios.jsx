import { useCallback, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../auth/contexto'
import { useCargar } from '../hooks/useCargar'

const ROLES = [
  { valor: 'contador', texto: 'Contador — carga cuentas y asientos' },
  { valor: 'lector', texto: 'Lector — solo consulta' },
  { valor: 'admin', texto: 'Admin — todo, incluido crear usuarios y cerrar ejercicios' },
]

function FormularioUsuario({ onCreado, onCancelar }) {
  const [datos, setDatos] = useState({ email: '', nombre: '', password: '', rol: 'contador' })
  const [error, setError] = useState(null)
  const [enviando, setEnviando] = useState(false)

  function campo(nombre) {
    return {
      value: datos[nombre],
      onChange: (e) => setDatos({ ...datos, [nombre]: e.target.value }),
    }
  }

  async function onSubmit(e) {
    e.preventDefault()
    setError(null)
    setEnviando(true)
    try {
      await api.registrar(datos)
      onCreado()
    } catch (err) {
      setError(err.message)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form className="tarjeta" onSubmit={onSubmit}>
      <h3>Nuevo usuario</h3>
      <div className="grilla-campos">
        <label>
          Email
          <input type="email" {...campo('email')} required placeholder="persona@empresa.com" />
        </label>
        <label>
          Nombre
          <input {...campo('nombre')} required />
        </label>
        <label>
          Contraseña
          <input
            type="password"
            {...campo('password')}
            required
            minLength={8}
            maxLength={72}
            autoComplete="new-password"
          />
        </label>
        <label>
          Rol
          <select {...campo('rol')}>
            {ROLES.map((r) => (
              <option key={r.valor} value={r.valor}>
                {r.texto}
              </option>
            ))}
          </select>
        </label>
      </div>
      <p className="sutil">
        Mínimo 8 caracteres y máximo 72 (el límite es de bcrypt). No hay recuperación de
        contraseña: si se pierde, hay que crear otro usuario.
      </p>
      {error && <p className="error">{error}</p>}
      <div className="acciones">
        <button type="submit" disabled={enviando}>
          {enviando ? 'Creando…' : 'Crear usuario'}
        </button>
        <button type="button" className="secundario" onClick={onCancelar}>
          Cancelar
        </button>
      </div>
    </form>
  )
}

export default function Usuarios() {
  const { usuario: actual } = useAuth()
  const [creando, setCreando] = useState(false)
  const cargador = useCallback(() => api.usuarios.listar(), [])
  const { datos, error, cargando, recargar } = useCargar(cargador)

  return (
    <section>
      <div className="encabezado-seccion">
        <div>
          <h2>Usuarios</h2>
          <p className="sutil">
            El registro público está cerrado: solo un admin da de alta usuarios.
          </p>
        </div>
        {!creando && <button onClick={() => setCreando(true)}>Nuevo usuario</button>}
      </div>

      {creando && (
        <FormularioUsuario
          onCancelar={() => setCreando(false)}
          onCreado={() => {
            setCreando(false)
            recargar()
          }}
        />
      )}

      {error && <p className="error">{error}</p>}
      {cargando && <p className="sutil">Cargando…</p>}

      {datos && !cargando && (
        <div className="tarjeta">
          <table>
            <thead>
              <tr>
                <th>Email</th>
                <th>Nombre</th>
                <th>Rol</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {datos.map((u) => (
                <tr key={u.id}>
                  <td>
                    {u.email}
                    {u.id === actual.id && <span className="etiqueta">vos</span>}
                  </td>
                  <td>{u.nombre}</td>
                  <td>
                    <span className={`etiqueta rol-${u.rol}`}>{u.rol}</span>
                  </td>
                  <td>
                    {u.activo ? (
                      <span className="sutil">activo</span>
                    ) : (
                      <span className="etiqueta etiqueta-inactiva">inactivo</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
