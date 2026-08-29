const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

async function request(path, token, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...options.headers },
    ...options,
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || 'Forecast request failed')
  return data
}

export function requestForecast(token, payload) {
  return request('/forecast/predict', token, { method: 'POST', body: JSON.stringify(payload) })
}

export function trainForecastModel(token) {
  return request('/forecast/train', token, { method: 'POST' })
}
