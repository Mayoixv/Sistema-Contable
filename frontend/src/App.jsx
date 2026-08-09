import { NavLink, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { useAuth } from './auth/contexto'
import Login from './pages/Login'
import PlanCuentas from './pages/PlanCuentas'
import LibroMayor from './pages/LibroMayor'
import Asientos from './pages/Asientos'
import BalanceComprobacion from './pages/BalanceComprobacion'
import EstadoResultados from './pages/EstadoResultados'
import BalanceGeneral from './pages/BalanceGeneral'
import Cierres from './pages/Cierres'
import Usuarios from './pages/Usuarios'

const SECCIONES = [
  { to: '/cuentas', texto: 'Plan de cuentas' },
  { to: '/asientos', texto: 'Asientos' },
  { to: '/balance-comprobacion', texto: 'Comprobación' },
  { to: '/estado-resultados', texto: 'Resultados' },
  { to: '/balance-general', texto: 'Balance general' },
  { to: '/cierres', texto: 'Cierres' },
  { to: '/usuarios', texto: 'Usuarios', soloAdmin: true },
]

function Layout({ children }) {
  const { usuario, logout, esAdmin } = useAuth()
  const secciones = SECCIONES.filter((s) => !s.soloAdmin || esAdmin)

  return (
    <div className="app">
      <header>
        <div className="marca">Sistema Contable</div>
        <nav>
          {secciones.map((s) => (
            <NavLink key={s.to} to={s.to}>
              {s.texto}
            </NavLink>
          ))}
        </nav>
        <div className="usuario">
          <span>
            {usuario.nombre} <span className={`etiqueta rol-${usuario.rol}`}>{usuario.rol}</span>
          </span>
          <button className="secundario" onClick={logout}>
            Salir
          </button>
        </div>
      </header>
      <main>{children}</main>
    </div>
  )
}

export default function App() {
  const { usuario, cargando } = useAuth()
  const navigate = useNavigate()

  if (cargando) return <div className="login-pantalla sutil">Cargando…</div>
  if (!usuario) return <Login />

  return (
    <Layout>
      <Routes>
        <Route
          path="/cuentas"
          element={<PlanCuentas onVerMayor={(c) => navigate(`/libro-mayor/${c.id}`)} />}
        />
        <Route path="/libro-mayor/:cuentaId" element={<LibroMayor />} />
        <Route path="/asientos" element={<Asientos />} />
        <Route path="/balance-comprobacion" element={<BalanceComprobacion />} />
        <Route path="/estado-resultados" element={<EstadoResultados />} />
        <Route path="/balance-general" element={<BalanceGeneral />} />
        <Route path="/cierres" element={<Cierres />} />
        <Route path="/usuarios" element={<Usuarios />} />
        <Route path="*" element={<Navigate to="/cuentas" replace />} />
      </Routes>
    </Layout>
  )
}
