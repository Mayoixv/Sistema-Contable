import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach, vi } from 'vitest'

/**
 * localStorage en memoria.
 *
 * No se puede confiar en el de jsdom: Node 26 expone un `localStorage`
 * nativo experimental que queda deshabilitado si no se pasa
 * `--localstorage-file`, y termina tapando al de jsdom (window.localStorage
 * queda `undefined`). En Node 20 eso no pasa, así que sin esto los tests
 * pasarían en CI y fallarían localmente. Se instala siempre, para que el
 * comportamiento sea idéntico en cualquier versión de Node.
 */
class AlmacenamientoEnMemoria {
  #datos = new Map()

  get length() {
    return this.#datos.size
  }

  key(indice) {
    return [...this.#datos.keys()][indice] ?? null
  }

  getItem(clave) {
    return this.#datos.has(String(clave)) ? this.#datos.get(String(clave)) : null
  }

  setItem(clave, valor) {
    this.#datos.set(String(clave), String(valor))
  }

  removeItem(clave) {
    this.#datos.delete(String(clave))
  }

  clear() {
    this.#datos.clear()
  }
}

const almacenamiento = new AlmacenamientoEnMemoria()
for (const objetivo of [globalThis, globalThis.window].filter(Boolean)) {
  Object.defineProperty(objetivo, 'localStorage', {
    value: almacenamiento,
    configurable: true,
    writable: true,
  })
}

beforeEach(() => {
  // Sin esto, la sesión que deja un test se filtra al siguiente.
  localStorage.clear()
})

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})
