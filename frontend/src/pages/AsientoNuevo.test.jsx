import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../api/client'
import AsientoNuevo from './AsientoNuevo'

const CUENTAS = [
  { id: 1, codigo: '1.1.01', nombre: 'Caja' },
  { id: 2, codigo: '3.1.01', nombre: 'Capital' },
]

function montar(props = {}) {
  const onCreado = vi.fn()
  const onCancelar = vi.fn()
  render(
    <AsientoNuevo cuentas={CUENTAS} onCreado={onCreado} onCancelar={onCancelar} {...props} />,
  )
  return { onCreado, onCancelar }
}

const guardar = () => screen.getByRole('button', { name: /guardar asiento/i })
const filas = () => screen.getAllByRole('row').filter((f) => f.querySelector('select'))

/** Completa una línea del asiento: cuenta + importe de un solo lado. */
async function cargarLinea(usuario, indice, { cuenta, debito, credito }) {
  const fila = filas()[indice]
  await usuario.selectOptions(fila.querySelector('select'), String(cuenta))
  const [inputDebito, inputCredito] = fila.querySelectorAll('input[type="number"]')
  if (debito !== undefined) await usuario.type(inputDebito, debito)
  if (credito !== undefined) await usuario.type(inputCredito, credito)
}

describe('AsientoNuevo', () => {
  beforeEach(() => {
    vi.spyOn(api.asientos, 'crear').mockResolvedValue({ id: 1 })
  })

  it('arranca con dos líneas y el botón deshabilitado', () => {
    montar()
    expect(filas()).toHaveLength(2)
    expect(guardar()).toBeDisabled()
    expect(screen.getByText(/sin importes cargados/i)).toBeInTheDocument()
  })

  it('marca el asiento como balanceado cuando débitos = créditos', async () => {
    const usuario = userEvent.setup()
    montar()

    await usuario.type(screen.getByPlaceholderText(/venta al contado/i), 'Aporte')
    await cargarLinea(usuario, 0, { cuenta: 1, debito: '1000' })
    await cargarLinea(usuario, 1, { cuenta: 2, credito: '1000' })

    expect(screen.getByText(/asiento balanceado/i)).toBeInTheDocument()
    expect(guardar()).toBeEnabled()
  })

  it('muestra la diferencia y no deja guardar si está descuadrado', async () => {
    const usuario = userEvent.setup()
    montar()

    await cargarLinea(usuario, 0, { cuenta: 1, debito: '1000' })
    await cargarLinea(usuario, 1, { cuenta: 2, credito: '600' })

    expect(screen.getByText(/diferencia/i)).toHaveTextContent('faltan créditos')
    expect(guardar()).toBeDisabled()
  })

  it('escribir en un lado limpia el otro: débito y crédito son excluyentes', async () => {
    const usuario = userEvent.setup()
    montar()

    const fila = filas()[0]
    const [inputDebito, inputCredito] = fila.querySelectorAll('input[type="number"]')
    await usuario.type(inputDebito, '500')
    expect(inputDebito).toHaveValue(500)

    await usuario.type(inputCredito, '300')
    expect(inputCredito).toHaveValue(300)
    expect(inputDebito).toHaveValue(null) // se limpió
  })

  it('no descuadra por redondeo de punto flotante (0.1 + 0.2)', async () => {
    const usuario = userEvent.setup()
    montar()

    await usuario.type(screen.getByPlaceholderText(/venta al contado/i), 'Centavos')
    // Con floats, 0.1 + 0.2 === 0.30000000000000004 y esto se marcaría como
    // descuadrado; el componente compara en centavos para evitarlo.
    await cargarLinea(usuario, 0, { cuenta: 1, debito: '0.1' })
    await cargarLinea(usuario, 1, { cuenta: 2, debito: '0.2' })
    await usuario.click(screen.getByRole('button', { name: /agregar línea/i }))
    await cargarLinea(usuario, 2, { cuenta: 2, credito: '0.3' })

    expect(screen.getByText(/asiento balanceado/i)).toBeInTheDocument()
    expect(guardar()).toBeEnabled()
  })

  it('envía solo las líneas con datos y avisa al padre', async () => {
    const usuario = userEvent.setup()
    const { onCreado } = montar()

    await usuario.type(screen.getByPlaceholderText(/venta al contado/i), 'Aporte inicial')
    await cargarLinea(usuario, 0, { cuenta: 1, debito: '1000' })
    await cargarLinea(usuario, 1, { cuenta: 2, credito: '1000' })
    // Una tercera línea vacía no debe viajar al backend.
    await usuario.click(screen.getByRole('button', { name: /agregar línea/i }))

    await usuario.click(guardar())

    expect(api.asientos.crear).toHaveBeenCalledOnce()
    const enviado = api.asientos.crear.mock.calls[0][0]
    expect(enviado.descripcion).toBe('Aporte inicial')
    expect(enviado.movimientos).toEqual([
      { cuenta_id: 1, debito: '1000', credito: '0', descripcion: null },
      { cuenta_id: 2, debito: '0', credito: '1000', descripcion: null },
    ])
    expect(onCreado).toHaveBeenCalled()
  })

  it('muestra el error del backend y no avisa al padre', async () => {
    const usuario = userEvent.setup()
    api.asientos.crear.mockRejectedValue(new Error('La cuenta es sumaria'))
    const { onCreado } = montar()

    await usuario.type(screen.getByPlaceholderText(/venta al contado/i), 'Prueba')
    await cargarLinea(usuario, 0, { cuenta: 1, debito: '50' })
    await cargarLinea(usuario, 1, { cuenta: 2, credito: '50' })
    await usuario.click(guardar())

    expect(await screen.findByText('La cuenta es sumaria')).toBeInTheDocument()
    expect(onCreado).not.toHaveBeenCalled()
  })

  it('exige descripción para poder guardar', async () => {
    const usuario = userEvent.setup()
    montar()

    await cargarLinea(usuario, 0, { cuenta: 1, debito: '100' })
    await cargarLinea(usuario, 1, { cuenta: 2, credito: '100' })
    expect(guardar()).toBeDisabled()

    await usuario.type(screen.getByPlaceholderText(/venta al contado/i), 'Con descripción')
    expect(guardar()).toBeEnabled()
  })
})
