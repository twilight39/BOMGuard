import type { Bom, BomDetail } from '@/types'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed: ${res.status}`)
  }
  return res.json() as Promise<T>
}

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/api/health`)
  return res.json()
}

export async function fetchBoms(): Promise<Bom[]> {
  const res = await fetch(`${API_BASE}/api/boms/`)
  return handleResponse<Bom[]>(res)
}

export async function fetchBom(id: number): Promise<BomDetail> {
  const res = await fetch(`${API_BASE}/api/boms/${id}`)
  return handleResponse<BomDetail>(res)
}

export async function uploadBom(file: File): Promise<{ id: number; filename: string; status: string }> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${API_BASE}/api/boms/upload`, {
    method: 'POST',
    body: formData,
  })
  return handleResponse<{ id: number; filename: string; status: string }>(res)
}

export async function deleteBom(id: number): Promise<{ id: number; deleted: boolean }> {
  const res = await fetch(`${API_BASE}/api/boms/${id}`, {
    method: 'DELETE',
  })
  return handleResponse<{ id: number; deleted: boolean }>(res)
}
