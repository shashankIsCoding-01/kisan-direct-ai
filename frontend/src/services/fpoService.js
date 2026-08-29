const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

async function request(path, token, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, { headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...options.headers }, ...options })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || 'FPO request failed')
  return data
}

export function getMyFpo(token) { return request('/fpos/mine', token) }
export function createFpo(token, payload) { return request('/fpos', token, { method: 'POST', body: JSON.stringify(payload) }) }
export function getMembers(token, fpoId) { return request(`/fpos/${fpoId}/members`, token) }
export function addMember(token, fpoId, farmerId) { return request(`/fpos/${fpoId}/members`, token, { method: 'POST', body: JSON.stringify({ farmer_id: Number(farmerId) }) }) }
export function removeMember(token, fpoId, farmerId) { return request(`/fpos/${fpoId}/members/${farmerId}`, token, { method: 'DELETE' }) }
export function getMemberInventory(token, fpoId) { return request(`/fpos/${fpoId}/inventory`, token) }
export function aggregateProduce(token, fpoId, payload) { return request(`/fpos/${fpoId}/aggregate`, token, { method: 'POST', body: JSON.stringify(payload) }) }
export function getFpoListings(token, fpoId) { return request(`/fpos/${fpoId}/listings`, token) }
export function getFpoOrders(token, fpoId) { return request(`/fpos/${fpoId}/orders`, token) }
export function getFpoAnalytics(token, fpoId) { return request(`/fpos/${fpoId}/analytics`, token) }
