import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'

const TIPOS = ['activo', 'pasivo', 'patrimonio', 'ingreso', 'costo', 'gasto']

function FilaCuenta({ cuenta, nivel, onSeleccionar, seleccionada }) {
  const [abierta, setAbierta] = useState(true)
  const tieneHijas = cuenta.hijas?.length > 0

  return (
    <>
      <tr className={seleccionada === cuenta.id ? 'fila-activa' : undefined}>
        <td>
          <span style={{ paddingLeft: `${nivel * 1.25}rem` }}>
            {tieneHijas ? (
              <button className="chevron" onClick={() => setAbierta(!abierta)}>
                {abierta ? '▾' : '▸'}
              </button>
            ) : (
              <span className="chevron-vacio" />
            )}
            <strong>{cuenta.codigo}</strong> {cuenta.nombre}
          </span>
        </td>
        <td>
          <span className={`etiqueta etiqueta-${cuenta.tipo}`}>{cuenta.tipo}</span>
        </td>
        <td>{cuenta.naturaleza}</td>
        <td>
          {cuenta.acepta_movimiento ? (
            <span className="sutil">detalle</span>
          ) : (
            <span className="sutil">sumaria</span>
          )}
          {!cuenta.activa && <span className="etiqueta etiqueta-inactiva">inactiva</span>}
        </td>
        <td>
          {cuenta.acepta_movimiento && (
            <button className="enlace" onClick={() => onSeleccionar(cuenta)}>
              Ver mayor
            </button>
          )}
        </td>
      </tr>
      {abierta &&
        cuenta.hijas?.map((hija) => (
          <FilaCuenta
            key={hija.id}
            cuenta={hija}
            nivel={nivel + 1}
            onSeleccionar={onSeleccionar}
            seleccionada={seleccionada}
          />
        ))}
    </>
  )
}

function FormularioCuenta({ cuentasPlanas, onCreada, onCancelar }) {
  const [datos, setDatos] = useState({
    codigo: '',
    nombre: '',
    tipo: 'activo',
    padre_id: '',
  })
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
      await api.cuentas.crear({
        codigo: datos.codigo,
        nombre: datos.nombre,
        tipo: datos.tipo,
        padre_id: datos.padre_id ? Number(datos.padre_id) : null,
      })
      onCreada()
    } catch (err) {
      setError(err.message)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form className="tarjeta formulario-inline" onSubmit={onSubmit}>
      <h3>Nueva cuenta</h3>
      <div className="grilla-campos">
        <label>
          Código
          <input {...campo('codigo')} required placeholder="1.1.01" />
        </label>
        <label>
          Nombre
          <input {...campo('nombre')} required placeholder="Caja" />
        </label>
        <label>
          Tipo
          <select {...campo('tipo')}>
            {TIPOS.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <label>
          Cuenta padre
          <select {...campo('padre_id')}>
            <option value="">(cuenta raíz)</option>
            {cuentasPlanas.map((c) => (
              <option key={c.id} value={c.id}>
                {c.codigo} — {c.nombre}
              </option>
            ))}
          </select>
        </label>
      </div>
      <p className="sutil">
        La naturaleza se completa sola según el tipo. Si elegís una cuenta padre que hoy
        acepta movimientos, pasa a ser sumaria automáticamente.
      </p>
      {error && <p className="error">{error}</p>}
      <div className="acciones">
        <button type="submit" disabled={enviando}>
          {enviando ? 'Creando…' : 'Crear cuenta'}
        </button>
        <button type="button" className="secundario" onClick={onCancelar}>
          Cancelar
        </button>
      </div>
    </form>
  )
}

export default function PlanCuentas({ onVerMayor }) {
  const { puedeEscribir } = useAuth()
  const [arbol, setArbol] = useState([])
  const [planas, setPlanas] = useState([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState(null)
  const [creando, setCreando] = useState(false)

  const cargar = useCallback(async () => {
    setCargando(true)
    setError(null)
    try {
      const [arbolResp, planasResp] = await Promise.all([
        api.cuentas.arbol(),
        api.cuentas.listar({ limit: 500 }),
      ])
      setArbol(arbolResp)
      setPlanas(planasResp)
    } catch (err) {
      setError(err.message)
    } finally {
      setCargando(false)
    }
  }, [])

  useEffect(() => {
    cargar()
  }, [cargar])

  return (
    <section>
      <div className="encabezado-seccion">
        <div>
          <h2>Plan de cuentas</h2>
          <p className="sutil">
            Solo las cuentas de detalle (hojas) reciben asientos; las sumarias agrupan saldos.
          </p>
        </div>
        {puedeEscribir && !creando && (
          <button onClick={() => setCreando(true)}>Nueva cuenta</button>
        )}
      </div>

      {creando && (
        <FormularioCuenta
          cuentasPlanas={planas}
          onCancelar={() => setCreando(false)}
          onCreada={() => {
            setCreando(false)
            cargar()
          }}
        />
      )}

      {error && <p className="error">{error}</p>}
      {cargando ? (
        <p className="sutil">Cargando…</p>
      ) : arbol.length === 0 ? (
        <p className="sutil">Todavía no hay cuentas cargadas.</p>
      ) : (
        <div className="tarjeta">
          <table>
            <thead>
              <tr>
                <th>Cuenta</th>
                <th>Tipo</th>
                <th>Naturaleza</th>
                <th>Uso</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {arbol.map((cuenta) => (
                <FilaCuenta
                  key={cuenta.id}
                  cuenta={cuenta}
                  nivel={0}
                  onSeleccionar={onVerMayor}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
