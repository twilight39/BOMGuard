const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/api/health`)
  return res.json()
}
