import { useEffect, useState } from 'react'
import { EmptyMessage, ErrorMessage, LoadingMessage } from '../../components/marketplace/StateMessage'
import { useAuth } from '../../hooks/useAuth'
import { createRequirement, getRequirements, matchRequirement, placeRequirementOrders } from '../../services/bulkService'

const initialForm = { product_name: '', unit: 'kg', required_quantity: '', quality: 'STANDARD', max_price: '', delivery_location: '', delivery_deadline: '' }

function BulkBuyerPage() {
  const { token } = useAuth()
  const [requirements, setRequirements] = useState([])
  const [matches, setMatches] = useState({})
  const [form, setForm] = useState(initialForm)
  const [isLoading, setIsLoading] = useState(true)
  const [busyId, setBusyId] = useState(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => {
    let active = true
    getRequirements(token)
      .then((result) => { if (active) setRequirements(result) })
      .catch((requestError) => { if (active) setError(requestError.message) })
      .finally(() => { if (active) setIsLoading(false) })
    return () => { active = false }
  }, [token])

  async function submitRequirement(event) {
    event.preventDefault()
    setBusyId('create')
    setError('')
    try {
      const result = await createRequirement(token, { ...form, required_quantity: Number(form.required_quantity), max_price: Number(form.max_price), delivery_deadline: new Date(form.delivery_deadline).toISOString() })
      setRequirements((current) => [result, ...current])
      setForm(initialForm)
      setMessage('Purchase requirement created.')
    } catch (requestError) { setError(requestError.message) } finally { setBusyId(null) }
  }

  async function runMatch(requirementId) {
    setBusyId(requirementId)
    setError('')
    try {
      const result = await matchRequirement(token, requirementId)
      setMatches((current) => ({ ...current, [requirementId]: result }))
      setMessage('Supply match refreshed from live listings.')
    } catch (requestError) { setError(requestError.message) } finally { setBusyId(null) }
  }

  async function placeOrders(requirementId) {
    setBusyId(requirementId)
    setError('')
    try { const result = await placeRequirementOrders(token, requirementId); setMessage(`${result.ordered_quantity} ordered across ${result.order_ids.length} supplier order(s). Remaining: ${result.remaining_quantity}.`); setRequirements(await getRequirements(token)); await runMatch(requirementId) } catch (requestError) { setError(requestError.message) } finally { setBusyId(null) }
  }

  if (isLoading) return <LoadingMessage message="Loading purchase requirements..." />

  return (
    <div className="space-y-6">
      <header className="rounded-2xl bg-amber-700 p-6 text-white shadow-lg sm:p-8"><p className="text-sm font-semibold uppercase tracking-[0.2em] text-amber-100">Bulk buyer workspace</p><h1 className="mt-3 text-3xl font-bold">Source with confidence</h1><p className="mt-3 max-w-2xl text-amber-50">Create requirements and compare live farmer and FPO supply using transparent deterministic rules.</p></header>
      {error ? <ErrorMessage message={error} /> : null}{message ? <p className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{message}</p> : null}
      <form onSubmit={submitRequirement} className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:grid-cols-2" aria-label="Purchase requirement form"><h2 className="md:col-span-2 text-lg font-semibold text-slate-800">New purchase requirement</h2><label className="text-sm font-medium text-slate-700">Product<input required minLength="2" name="product_name" value={form.product_name} onChange={(event) => setForm({ ...form, product_name: event.target.value })} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2.5" /></label><label className="text-sm font-medium text-slate-700">Required quantity<input required min="0.01" step="0.01" type="number" name="required_quantity" value={form.required_quantity} onChange={(event) => setForm({ ...form, required_quantity: event.target.value })} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2.5" /></label><label className="text-sm font-medium text-slate-700">Unit<input required name="unit" value={form.unit} onChange={(event) => setForm({ ...form, unit: event.target.value })} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2.5" /></label><label className="text-sm font-medium text-slate-700">Minimum quality<select name="quality" value={form.quality} onChange={(event) => setForm({ ...form, quality: event.target.value })} className="mt-1.5 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5"><option value="STANDARD">Standard</option><option value="GRADE_A">Grade A</option><option value="PREMIUM">Premium</option></select></label><label className="text-sm font-medium text-slate-700">Maximum price per unit<input required min="0.01" step="0.01" type="number" name="max_price" value={form.max_price} onChange={(event) => setForm({ ...form, max_price: event.target.value })} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2.5" /></label><label className="text-sm font-medium text-slate-700">Delivery deadline<input required type="datetime-local" name="delivery_deadline" value={form.delivery_deadline} onChange={(event) => setForm({ ...form, delivery_deadline: event.target.value })} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2.5" /></label><label className="text-sm font-medium text-slate-700 md:col-span-2">Delivery location<input required minLength="5" name="delivery_location" value={form.delivery_location} onChange={(event) => setForm({ ...form, delivery_location: event.target.value })} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2.5" /></label><button disabled={busyId === 'create'} type="submit" className="rounded-xl bg-amber-600 px-4 py-2.5 font-semibold text-white hover:bg-amber-700 disabled:opacity-60 md:col-span-2">{busyId === 'create' ? 'Creating...' : 'Create requirement'}</button></form>
      <section className="space-y-4" aria-label="Purchase requirements"><h2 className="text-xl font-semibold text-slate-800">Your requirements</h2>{requirements.length === 0 ? <EmptyMessage title="No requirements yet" description="Create a requirement to start matching supply." /> : requirements.map((requirement) => { const match = matches[requirement.id]; return <article key={requirement.id} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"><div><h3 className="text-lg font-semibold text-slate-900">{requirement.product_name}</h3><p className="mt-1 text-sm text-slate-500">Required: {requirement.required_quantity} {requirement.unit} • Quality: {requirement.quality} • Max: ₹{requirement.max_price}/{requirement.unit}</p><p className="text-sm text-slate-500">Deliver to {requirement.delivery_location} by {new Date(requirement.delivery_deadline).toLocaleString()}</p></div><span className="w-fit rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800">{requirement.status}</span></div><div className="mt-4 flex flex-wrap gap-2"><button disabled={busyId === requirement.id} onClick={() => runMatch(requirement.id)} type="button" className="rounded-xl bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-60">{busyId === requirement.id ? 'Working...' : 'Match live supply'}</button>{match?.matched_quantity > 0 ? <button disabled={busyId === requirement.id} onClick={() => placeOrders(requirement.id)} type="button" className="rounded-xl border border-emerald-600 px-3 py-2 text-sm font-semibold text-emerald-700 hover:bg-emerald-50 disabled:opacity-60">Place bulk orders</button> : null}</div>{match ? <div className="mt-5 grid gap-3 sm:grid-cols-4"><div className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-slate-500">Required</p><p className="font-semibold">{match.required_quantity} {requirement.unit}</p></div><div className="rounded-xl bg-emerald-50 p-3"><p className="text-xs text-emerald-700">Matched</p><p className="font-semibold text-emerald-800">{match.matched_quantity} {requirement.unit}</p></div><div className="rounded-xl bg-amber-50 p-3"><p className="text-xs text-amber-700">Remaining</p><p className="font-semibold text-amber-800">{match.remaining_quantity} {requirement.unit}</p></div><div className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-slate-500">Estimated cost</p><p className="font-semibold">₹{match.estimated_cost}</p></div></div> : null}{match ? <div className="mt-4 space-y-2"><p className="text-sm font-semibold text-slate-700">Suppliers and delivery estimate: {match.delivery_estimate ? new Date(match.delivery_estimate).toLocaleDateString() : 'Unavailable'}</p>{match.suppliers.length === 0 ? <p className="text-sm text-slate-500">No eligible supply currently available.</p> : match.suppliers.map((supplier) => <div key={supplier.product_id} className="flex flex-col gap-1 rounded-xl border border-slate-200 p-3 text-sm sm:flex-row sm:justify-between"><span>{supplier.supplier_name} • {supplier.quality} • {supplier.matched_quantity} {requirement.unit}</span><span className="font-semibold">₹{supplier.unit_price}/{requirement.unit} • ₹{supplier.estimated_cost}</span></div>)}</div> : null}</article> })}</section>
    </div>
  )
}

export default BulkBuyerPage
