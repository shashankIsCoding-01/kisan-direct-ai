const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || 'Marketplace request failed')
  return data
}

export function getProducts({ search, category, sort }) {
  const params = new URLSearchParams({ sort })
  if (search) params.set('search', search)
  if (category) params.set('category', category)
  return request(`/products?${params}`)
}

export function getProduct(productId) {
  return request(`/products/${productId}`)
}

export function addToCart(token, payload) {
  return request('/cart/items', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  })
}

export function getOwnProducts(token) {
  return request('/products/mine', { headers: { Authorization: `Bearer ${token}` } })
}

export function createProduct(token, payload) {
  return request('/products', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  })
}

export function updateProduct(token, productId, payload) {
  return request(`/products/${productId}`, {
    method: 'PATCH',
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  })
}

export function deactivateProduct(token, productId) {
  return request(`/products/${productId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  })
}

export function getSellerOrders(token) {
  return request('/orders/sales', { headers: { Authorization: `Bearer ${token}` } })
}

export function getSellerNotifications(token) {
  return request('/orders/notifications', { headers: { Authorization: `Bearer ${token}` } })
}
