import type { Bom, BomDetail, ScanResult } from '@/types'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function camelize<T>(obj: unknown): T {
  if (obj === null || obj === undefined) return obj as T
  if (Array.isArray(obj)) return obj.map((item) => camelize(item)) as T
  if (typeof obj !== 'object') return obj as T
  const result: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(obj)) {
    const camelKey = key.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase())
    result[camelKey] = camelize(value)
  }
  return result as T
}

async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  return fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: 'include',
    headers: {
      ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...options.headers,
    },
  })
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed: ${res.status}`)
  }
  return res.json() as Promise<T>
}

export async function fetchHealth() {
  const res = await apiFetch('/api/health')
  return res.json()
}

export async function fetchMe(): Promise<{ id: string; email: string; name: string | null; avatar_url: string | null } | null> {
  const res = await apiFetch('/api/auth/me')
  if (!res.ok) return null
  return res.json()
}

export async function updateMe(body: { name: string }): Promise<{ id: string; email: string; name: string | null; avatar_url: string | null }> {
  const res = await apiFetch('/api/auth/me', {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Failed to update profile')
  }
  return res.json()
}

export async function deleteMe(): Promise<{ status: string }> {
  const res = await apiFetch('/api/auth/me', { method: 'DELETE' })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Failed to delete account')
  }
  return res.json()
}

export async function uploadAvatar(file: File): Promise<{ id: string; email: string; name: string | null; avatar_url: string | null }> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await apiFetch('/api/auth/avatar', {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Failed to upload avatar')
  }
  return res.json()
}

export async function fetchBoms(): Promise<Bom[]> {
  const res = await apiFetch('/api/boms/')
  const data = await handleResponse<unknown>(res)
  return camelize<Bom[]>(data)
}

export async function fetchBom(id: number): Promise<BomDetail> {
  const res = await apiFetch(`/api/boms/${id}`)
  const data = await handleResponse<unknown>(res)
  return camelize<BomDetail>(data)
}

export async function uploadBom(file: File): Promise<{ id: number; filename: string; status: string }> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await apiFetch('/api/boms/upload', {
    method: 'POST',
    body: formData,
  })
  return handleResponse<{ id: number; filename: string; status: string }>(res)
}

export async function deleteBom(id: number): Promise<{ id: number; deleted: boolean }> {
  const res = await apiFetch(`/api/boms/${id}`, {
    method: 'DELETE',
  })
  return handleResponse<{ id: number; deleted: boolean }>(res)
}

export async function loadSample(sampleId: string): Promise<Bom> {
  const res = await apiFetch(`/api/boms/samples/${sampleId}`, { method: 'POST' })
  const data = await handleResponse<unknown>(res)
  return camelize<Bom>(data)
}

export async function fetchSampleList(): Promise<Array<{ id: string; name: string; filename: string }>> {
  const res = await apiFetch('/api/boms/samples')
  return handleResponse(res)
}

export async function fetchStats(): Promise<{ substances: number; regulations: number; boms: number }> {
  const res = await apiFetch('/api/admin/ml/stats')
  return handleResponse(res)
}

export async function triggerScan(bomId: number): Promise<{ bom_id: number; status: string; hits_found: number; compliance_status: string }> {
  const res = await apiFetch(`/api/scan/${bomId}`, { method: 'POST' })
  return handleResponse<{ bom_id: number; status: string; hits_found: number; compliance_status: string }>(res)
}

export async function fetchScanResults(bomId: number): Promise<ScanResult[]> {
  const res = await apiFetch(`/api/scan/${bomId}/result`)
  const data = await handleResponse<unknown>(res)
  return camelize<ScanResult[]>(data)
}

export interface AskSource {
  id: number
  substance_id: number | null
  regulation_id: string | null
  summary_text: string
}

export interface AskResponse {
  answer: string
  sources: AskSource[]
}

export async function askQuestion(question: string): Promise<AskResponse> {
  const res = await fetch(`${API_BASE}/api/ask/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  if (!res.ok) {
    throw new Error(`Ask failed: ${res.status}`)
  }
  return res.json()
}
