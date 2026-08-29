const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

async function request(path, token, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, { headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...options.headers }, ...options })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || 'Logistics request failed')
  return data
}

export function getVehicles(token) { return request('/logistics/vehicles', token) }
export function createVehicle(token, payload) { return request('/logistics/vehicles', token, { method: 'POST', body: JSON.stringify(payload) }) }
export function createPickupLocation(token, payload) { return request('/logistics/pickup-locations', token, { method: 'POST', body: JSON.stringify(payload) }) }
export function createDeliveryLocation(token, payload) { return request('/logistics/delivery-locations', token, { method: 'POST', body: JSON.stringify(payload) }) }
export function getDeliveries(token) { return request('/logistics/deliveries', token) }
export function optimizeRoute(token, payload) { return request('/logistics/routes/optimize', token, { method: 'POST', body: JSON.stringify(payload) }) }
