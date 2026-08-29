const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

async function request(path, token, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, { headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...options.headers }, ...options })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || 'Bulk buyer request failed')
  return data
}

export function getRequirements(token) { return request('/bulk-requirements', token) }
export function createRequirement(token, payload) { return request('/bulk-requirements', token, { method: 'POST', body: JSON.stringify(payload) }) }
export function matchRequirement(token, requirementId) { return request(`/bulk-requirements/${requirementId}/match`, token, { method: 'POST' }) }
export function placeRequirementOrders(token, requirementId) { return request(`/bulk-requirements/${requirementId}/place-orders`, token, { method: 'POST' }) }
