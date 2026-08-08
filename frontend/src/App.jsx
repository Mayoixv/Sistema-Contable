import { NavLink, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { useAuth } from './auth/AuthContext'
import Login from './pages/Login'
import PlanCuentas from './pages/PlanCuentas'
import LibroMayor from './pages/LibroMayor'

function Layout({ children }) {
  const { usuario, logout } = useAuth()

  return (
    <div className="app">
      <header>
        <div className="marca">Sistema Contable</div>
        <nav>
          <NavLink to="/cuentas">Plan de cuentas</NavLink>
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
        <Route path="/cuentas" element={<PlanCuentas onVerMayor={(c) => navigate(`/libro-mayor/${c.id}`)} />} />
        <Route path="/libro-mayor/:cuentaId" element={<LibroMayor />} />
        <Route path="*" element={<Navigate to="/cuentas" replace />} />
      </Routes>
    </Layout>
  )
}
