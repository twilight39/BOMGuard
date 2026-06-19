import { vi } from 'vitest'
import '@testing-library/jest-dom/vitest'

Element.prototype.scrollIntoView = vi.fn()

Object.defineProperty(globalThis, 'localStorage', {
  value: (() => {
    let store: Record<string, string> = {}
    return {
      getItem: (key: string) => store[key] ?? null,
      setItem: (key: string, value: string) => {
        store[key] = value
      },
      removeItem: (key: string) => {
        delete store[key]
      },
      clear: () => {
        store = {}
      },
    }
  })(),
  writable: true,
})
