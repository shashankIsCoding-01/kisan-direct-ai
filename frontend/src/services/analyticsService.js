const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

export async function getAnalyticsDashboard(token) {
  const response = await fetch(`${API_BASE_URL}/analytics/dashboard`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || 'Analytics request failed')
  return data
}

export async function getAnalyticsDefinitions() {
  const response = await fetch(`${API_BASE_URL}/analytics/definitions`)
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || 'Analytics definitions request failed')
  return data
}
