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
  const [accionError, setAccionError] = useState(null)
  const cargador = useCallback(() => api.usuarios.listar(), [])
  const { datos, error, cargando, recargar } = useCargar(cargador)

  async function accion(fn, confirmacion) {
    if (confirmacion && !window.confirm(confirmacion)) return
    setAccionError(null)
    try {
      await fn()
      recargar()
    } catch (err) {
      setAccionError(err.message)
    }
  }

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
      {accionError && <p className="error">{accionError}</p>}
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
                <th />
              </tr>
            </thead>
            <tbody>
              {datos.map((u) => {
                const esUnoMismo = u.id === actual.id
                return (
                  <tr key={u.id}>
                    <td>
                      {u.email}
                      {esUnoMismo && <span className="etiqueta">vos</span>}
                    </td>
                    <td>{u.nombre}</td>
                    <td>
                      {esUnoMismo ? (
                        <span className={`etiqueta rol-${u.rol}`}>{u.rol}</span>
                      ) : (
                        <select
                          value={u.rol}
                          onChange={(e) =>
                            accion(() => api.usuarios.actualizar(u.id, { rol: e.target.value }))
                          }
                        >
                          {ROLES.map((r) => (
                            <option key={r.valor} value={r.valor}>
                              {r.valor}
                            </option>
                          ))}
                        </select>
                      )}
                    </td>
                    <td>
                      {u.activo ? (
                        <span className="sutil">activo</span>
                      ) : (
                        <span className="etiqueta etiqueta-inactiva">inactivo</span>
                      )}
                    </td>
                    <td className="acciones-fila">
                      {esUnoMismo ? (
                        <span className="sutil">— tu propio usuario —</span>
                      ) : (
                        <>
                          <button
                            className="enlace"
                            onClick={() =>
                              accion(() =>
                                api.usuarios.actualizar(u.id, { activo: !u.activo }),
                              )
                            }
                          >
                            {u.activo ? 'Desactivar' : 'Activar'}
                          </button>
                          <button
                            className="enlace peligro"
                            onClick={() =>
                              accion(
                                () => api.usuarios.eliminar(u.id),
                                `¿Eliminar a ${u.email}?\n\nSi cargó asientos o hizo cierres no se podrá borrar, para no perder la trazabilidad: en ese caso desactivalo.`,
                              )
                            }
                          >
                            Eliminar
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          <p className="sutil">
            Sobre tu propio usuario no podés actuar: es la única forma de garantizar que
            siempre quede un admin activo, y no habría manera de recuperar el acceso si el
            sistema se quedara sin ninguno.
          </p>
        </div>
      )}
    </section>
  )
}
