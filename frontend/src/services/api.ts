const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

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
