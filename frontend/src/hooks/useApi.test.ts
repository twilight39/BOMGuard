import { describe, it, expect, vi } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useApi } from './useApi'

describe('useApi', () => {
  it('starts in the idle state', () => {
    const fn = vi.fn().mockResolvedValue('ok')
    const { result } = renderHook(() => useApi(fn))

    expect(result.current.data).toBeNull()
    expect(result.current.loading).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('sets loading and returns data on success', async () => {
    let resolve: (value: unknown) => void = () => {}
    const fn = vi.fn().mockImplementation(() => new Promise((res) => { resolve = res }))
    const { result } = renderHook(() => useApi(fn))

    act(() => {
      result.current.execute()
    })

    expect(result.current.loading).toBe(true)

    act(() => {
      resolve({ id: 1 })
    })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.data).toEqual({ id: 1 })
    expect(result.current.error).toBeNull()
  })

  it('sets error on failure', async () => {
    const fn = vi.fn().mockRejectedValue(new Error('network error'))
    const { result } = renderHook(() => useApi(fn))

    await act(async () => {
      await result.current.execute()
    })

    expect(result.current.data).toBeNull()
    expect(result.current.error?.message).toBe('network error')
  })
})
