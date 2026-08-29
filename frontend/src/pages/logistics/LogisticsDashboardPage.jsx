import { useEffect, useState } from 'react'
import { ErrorMessage, EmptyMessage, LoadingMessage } from '../../components/marketplace/StateMessage'
import { useAuth } from '../../hooks/useAuth'
import { createVehicle, getDeliveries, getVehicles, optimizeRoute } from '../../services/logisticsService'

function LogisticsDashboardPage() {
  const { token } = useAuth()
  const [vehicles, setVehicles] = useState([])
  const [deliveries, setDeliveries] = useState([])
  const [route, setRoute] = useState(null)
  const [vehicleForm, setVehicleForm] = useState({ registration_number: '', vehicle_type: 'Truck', capacity: '', unit: 'kg' })
  const [routeForm, setRouteForm] = useState({ vehicle_id: '', depot_latitude: '', depot_longitude: '', average_speed_kmh: '30' })
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => {
    let active = true
    Promise.all([getVehicles(token), getDeliveries(token)])
      .then(([vehicleData, deliveryData]) => { if (active) { setVehicles(vehicleData); setDeliveries(deliveryData); if (vehicleData[0]) setRouteForm((current) => ({ ...current, vehicle_id: String(vehicleData[0].id) })) } })
      .catch((requestError) => { if (active) setError(requestError.message) })
      .finally(() => { if (active) setIsLoading(false) })
    return () => { active = false }
  }, [token])

  async function submitVehicle(event) {
    event.preventDefault()
    setIsSaving(true)
    setError('')
    try { const vehicle = await createVehicle(token, { ...vehicleForm, capacity: Number(vehicleForm.capacity) }); setVehicles((current) => [...current, vehicle]); setVehicleForm({ registration_number: '', vehicle_type: 'Truck', capacity: '', unit: 'kg' }); setMessage('Vehicle registered.') } catch (requestError) { setError(requestError.message) } finally { setIsSaving(false) }
  }

  async function submitRoute(event) {
    event.preventDefault()
    setIsSaving(true)
    setError('')
    try { const result = await optimizeRoute(token, { vehicle_id: Number(routeForm.vehicle_id), delivery_ids: deliveries.filter((delivery) => delivery.status === 'ASSIGNED' || delivery.status === 'PENDING').map((delivery) => delivery.id), depot_latitude: Number(routeForm.depot_latitude), depot_longitude: Number(routeForm.depot_longitude), average_speed_kmh: Number(routeForm.average_speed_kmh) }); setRoute(result); setMessage('Route optimized. The response compares the supplied baseline order with nearest-neighbor ordering.') } catch (requestError) { setError(requestError.message) } finally { setIsSaving(false) }
  }

  if (isLoading) return <LoadingMessage message="Loading logistics workspace..." />

  return (
    <div className="space-y-6">
      <header className="rounded-2xl bg-sky-800 p-6 text-white shadow-lg sm:p-8"><p className="text-sm font-semibold uppercase tracking-[0.2em] text-sky-100">Logistics operations</p><h1 className="mt-3 text-3xl font-bold">Delivery control center</h1><p className="mt-3 max-w-2xl text-sky-50">Manage vehicles and assignments, then compare a baseline route with a deterministic optimized route.</p></header>
      {error ? <ErrorMessage message={error} /> : null}{message ? <p className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{message}</p> : null}
      <div className="grid gap-6 xl:grid-cols-2"><form onSubmit={submitVehicle} className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="text-lg font-semibold">Register vehicle</h2>{[['registration_number', 'Registration number'], ['vehicle_type', 'Vehicle type'], ['capacity', 'Capacity']].map(([name, label]) => <label key={name} className="block text-sm font-medium text-slate-700">{label}<input required min={name === 'capacity' ? '0.01' : undefined} type={name === 'capacity' ? 'number' : 'text'} name={name} value={vehicleForm[name]} onChange={(event) => setVehicleForm({ ...vehicleForm, [name]: event.target.value })} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2.5" /></label>)}<button disabled={isSaving} type="submit" className="rounded-xl bg-sky-700 px-4 py-2.5 font-semibold text-white hover:bg-sky-800 disabled:opacity-60">Register vehicle</button><div className="space-y-2 pt-2">{vehicles.length === 0 ? <EmptyMessage title="No vehicles" description="Register a vehicle to build routes." /> : vehicles.map((vehicle) => <div key={vehicle.id} className="rounded-xl bg-slate-50 p-3 text-sm"><span className="font-semibold">{vehicle.registration_number}</span> • {vehicle.vehicle_type} • Capacity {vehicle.capacity} {vehicle.unit}</div>)}</div></form>
      <form onSubmit={submitRoute} className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="text-lg font-semibold">Optimize route</h2><label className="block text-sm font-medium text-slate-700">Vehicle<select required value={routeForm.vehicle_id} onChange={(event) => setRouteForm({ ...routeForm, vehicle_id: event.target.value })} className="mt-1.5 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5">{vehicles.map((vehicle) => <option key={vehicle.id} value={vehicle.id}>{vehicle.registration_number}</option>)}</select></label><div className="grid gap-3 sm:grid-cols-2"><label className="text-sm font-medium text-slate-700">Depot latitude<input required type="number" step="any" value={routeForm.depot_latitude} onChange={(event) => setRouteForm({ ...routeForm, depot_latitude: event.target.value })} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2.5" /></label><label className="text-sm font-medium text-slate-700">Depot longitude<input required type="number" step="any" value={routeForm.depot_longitude} onChange={(event) => setRouteForm({ ...routeForm, depot_longitude: event.target.value })} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2.5" /></label></div><label className="block text-sm font-medium text-slate-700">Average speed km/h<input required min="1" type="number" value={routeForm.average_speed_kmh} onChange={(event) => setRouteForm({ ...routeForm, average_speed_kmh: event.target.value })} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2.5" /></label><p className="text-sm text-slate-500">Eligible assignments: {deliveries.filter((delivery) => delivery.status === 'ASSIGNED' || delivery.status === 'PENDING').length}. The map can later consume the persisted waypoint order separately from this routing calculation.</p><button disabled={isSaving || deliveries.length === 0} type="submit" className="rounded-xl bg-sky-700 px-4 py-2.5 font-semibold text-white hover:bg-sky-800 disabled:opacity-60">{isSaving ? 'Optimizing...' : 'Compare and optimize'}</button></form></div>
      {route ? <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-xl font-semibold">Route result</h2><p className="mt-1 text-sm text-slate-500">Provider: {route.routing_provider} • Method: {route.optimization_method}</p></div><span className="rounded-full bg-sky-100 px-3 py-1 text-xs font-semibold text-sky-800">Routing result</span></div><div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-5"><Metric label="Baseline distance" value={`${route.baseline_distance_km} km`} /><Metric label="Optimized distance" value={`${route.optimized_distance_km} km`} /><Metric label="Travel time" value={`${route.estimated_travel_time_min} min`} /><Metric label="Stops" value={route.number_of_stops} /><Metric label="Capacity used" value={`${route.capacity_utilization_percent}%`} /></div><p className="mt-4 text-sm font-semibold text-emerald-700">Distance reduction: {route.distance_reduction_percent}%</p><p className="mt-2 text-sm text-slate-500">Map display, routing distance calculation, and route optimization are separate concerns. This view does not claim that map rendering or routing is AI.</p></section> : null}
    </div>
  )
}

function Metric({ label, value }) { return <div className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-slate-500">{label}</p><p className="mt-1 text-lg font-semibold text-slate-800">{value}</p></div> }

export default LogisticsDashboardPage
