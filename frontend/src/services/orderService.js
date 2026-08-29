const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

async function request(path, token, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...options.headers },
    ...options,
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || 'Order request failed')
  return data
}

export function getOrders(token, role) {
  const path = role === 'CONSUMER' || role === 'BULK_BUYER' ? '/orders/mine' : role === 'FARMER' || role === 'FPO' ? '/orders/incoming' : role === 'LOGISTICS' ? '/orders/ready-for-pickup' : '/orders/all'
  return request(path, token)
}

export function updateOrderStatus(token, orderId, status) {
  return request(`/orders/${orderId}/status`, token, { method: 'PATCH', body: JSON.stringify({ status }) })
}

export function cancelOrder(token, orderId) {
  return request(`/orders/${orderId}`, token, { method: 'DELETE' })
}

export function assignDelivery(token, orderId, logisticsOperatorId) {
  return request(`/orders/${orderId}/delivery`, token, { method: 'POST', body: JSON.stringify({ logistics_operator_id: logisticsOperatorId }) })
}

export function updateDeliveryStatus(token, deliveryId, status, currentLocation) {
  return request(`/deliveries/${deliveryId}/status`, token, { method: 'PATCH', body: JSON.stringify({ status, current_location: currentLocation || null }) })
}
