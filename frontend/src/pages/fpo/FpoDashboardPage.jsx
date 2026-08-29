import { useCallback, useEffect, useState } from 'react'
import { EmptyMessage, ErrorMessage, LoadingMessage } from '../../components/marketplace/StateMessage'
import { useAuth } from '../../hooks/useAuth'
import { addMember, aggregateProduce, createFpo, getFpoAnalytics, getFpoListings, getFpoOrders, getMemberInventory, getMembers, getMyFpo, removeMember } from '../../services/fpoService'

const profileForm = { name: '', registration_number: '', address: '' }
const aggregateForm = { name: '', category: '', unit: 'kg', price_per_unit: '', location: '', allocations: [] }

function FpoDashboardPage() {
  const { token } = useAuth()
  const [fpo, setFpo] = useState(null)
  const [members, setMembers] = useState([])
  const [inventory, setInventory] = useState([])
  const [listings, setListings] = useState([])
  const [orders, setOrders] = useState([])
  const [analytics, setAnalytics] = useState(null)
  const [profile, setProfile] = useState(profileForm)
  const [farmerId, setFarmerId] = useState('')
  const [aggregation, setAggregation] = useState(aggregateForm)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const loadDashboard = useCallback(async (profileData) => {
    const [memberData, inventoryData, listingData, orderData, analyticsData] = await Promise.all([
      getMembers(token, profileData.id), getMemberInventory(token, profileData.id), getFpoListings(token, profileData.id), getFpoOrders(token, profileData.id), getFpoAnalytics(token, profileData.id),
    ])
    setMembers(memberData)
    setInventory(inventoryData.items)
    setListings(listingData)
    setOrders(orderData)
    setAnalytics(analyticsData)
  }, [token])

  useEffect(() => {
    let active = true
    getMyFpo(token)
      .then(async (profileData) => { if (active) { setFpo(profileData); await loadDashboard(profileData) } })
      .catch((requestError) => { if (active && !requestError.message.toLowerCase().includes('not found')) setError(requestError.message) })
      .finally(() => { if (active) setIsLoading(false) })
    return () => { active = false }
  }, [loadDashboard, token])

  async function submitProfile(event) {
    event.preventDefault()
    setIsSaving(true)
    setError('')
    try { const result = await createFpo(token, profile); setFpo(result); await loadDashboard(result); setMessage('FPO profile created.') } catch (requestError) { setError(requestError.message) } finally { setIsSaving(false) }
  }

  async function submitMember(event) {
    event.preventDefault()
    setIsSaving(true)
    try { await addMember(token, fpo.id, farmerId); setFarmerId(''); setMembers(await getMembers(token, fpo.id)); setInventory((await getMemberInventory(token, fpo.id)).items); setMessage('Farmer added to the FPO.') } catch (requestError) { setError(requestError.message) } finally { setIsSaving(false) }
  }

  function toggleAllocation(item) {
    setAggregation((current) => {
      const existing = current.allocations.find((allocation) => allocation.source_product_id === item.source_product_id)
      return { ...current, name: current.name || item.product_name, category: current.category || '', unit: item.unit, allocations: existing ? current.allocations.filter((allocation) => allocation.source_product_id !== item.source_product_id) : [...current.allocations, { source_product_id: item.source_product_id, quantity: '' }] }
    })
  }

  function updateAllocation(id, quantity) {
    setAggregation((current) => ({ ...current, allocations: current.allocations.map((allocation) => allocation.source_product_id === id ? { ...allocation, quantity } : allocation) }))
  }

  async function submitAggregation(event) {
    event.preventDefault()
    setIsSaving(true)
    try { await aggregateProduce(token, fpo.id, { ...aggregation, price_per_unit: Number(aggregation.price_per_unit), allocations: aggregation.allocations.map((item) => ({ ...item, quantity: Number(item.quantity) })) }); setMessage('Aggregated listing created and source quantities reserved.'); setListings(await getFpoListings(token, fpo.id)); setInventory((await getMemberInventory(token, fpo.id)).items); setAggregation(aggregateForm) } catch (requestError) { setError(requestError.message) } finally { setIsSaving(false) }
  }

  if (isLoading) return <LoadingMessage message="Loading FPO dashboard..." />
  if (error && !fpo) return <ErrorMessage message={error} />
  if (!fpo) return <form onSubmit={submitProfile} className="mx-auto max-w-xl space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"><div><p className="text-sm font-semibold uppercase tracking-[0.2em] text-emerald-700">FPO onboarding</p><h1 className="mt-2 text-3xl font-bold text-slate-900">Create your FPO profile</h1></div>{['name', 'registration_number', 'address'].map((field) => <label key={field} className="block text-sm font-medium capitalize text-slate-700">{field.replaceAll('_', ' ')}<input required={field !== 'registration_number'} name={field} value={profile[field]} onChange={(event) => setProfile({ ...profile, [field]: event.target.value })} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2.5" /></label>)}<button disabled={isSaving} type="submit" className="rounded-xl bg-emerald-600 px-4 py-2.5 font-semibold text-white disabled:opacity-60">{isSaving ? 'Creating...' : 'Create profile'}</button></form>

  return (
    <div className="space-y-6">
      <header className="rounded-2xl bg-emerald-800 p-6 text-white shadow-lg"><p className="text-sm font-semibold uppercase tracking-[0.2em] text-emerald-100">FPO dashboard</p><h1 className="mt-2 text-3xl font-bold">{fpo.name}</h1><p className="mt-2 text-emerald-100">{fpo.address}</p></header>
      {error ? <ErrorMessage message={error} /> : null}{message ? <p className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{message}</p> : null}
      <div className="grid gap-4 sm:grid-cols-3"><div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-sm text-slate-500">Members</p><p className="mt-2 text-2xl font-bold">{members.filter((member) => member.is_active).length}</p></div><div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-sm text-slate-500">Orders</p><p className="mt-2 text-2xl font-bold">{analytics?.order_count ?? 0}</p></div><div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-sm text-slate-500">Revenue</p><p className="mt-2 text-2xl font-bold">₹{analytics?.revenue ?? 0}</p></div></div>
      <div className="grid gap-6 xl:grid-cols-2"><section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="text-lg font-semibold">Manage farmer members</h2><form onSubmit={submitMember} className="mt-4 flex gap-2"><input required type="number" min="1" placeholder="Farmer user ID" value={farmerId} onChange={(event) => setFarmerId(event.target.value)} className="min-w-0 flex-1 rounded-xl border border-slate-300 px-3 py-2.5" /><button disabled={isSaving} type="submit" className="rounded-xl bg-emerald-600 px-3 py-2.5 text-sm font-semibold text-white disabled:opacity-60">Add</button></form><div className="mt-4 space-y-2">{members.length === 0 ? <EmptyMessage title="No members" description="Add a farmer by user ID." /> : members.map((member) => <div key={member.id} className="flex justify-between rounded-xl bg-slate-50 p-3 text-sm"><span>Farmer #{member.farmer_id}</span>{member.is_active ? <button type="button" onClick={async () => { await removeMember(token, fpo.id, member.farmer_id); setMembers(await getMembers(token, fpo.id)); setMessage('Membership deactivated.') }} className="font-medium text-red-700">Remove</button> : <span className="text-slate-400">Inactive</span>}</div>)}</div></section>
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="text-lg font-semibold">Member inventory</h2><div className="mt-4 space-y-2">{inventory.length === 0 ? <EmptyMessage title="No available supply" description="Active farmer listings appear here." /> : inventory.map((item) => <label key={item.source_product_id} className="flex items-center gap-3 rounded-xl bg-slate-50 p-3 text-sm"><input type="checkbox" checked={aggregation.allocations.some((allocation) => allocation.source_product_id === item.source_product_id)} onChange={() => toggleAllocation(item)} /><span className="flex-1">{item.product_name} • Farmer #{item.farmer_id} • {item.available_quantity} {item.unit}</span>{aggregation.allocations.some((allocation) => allocation.source_product_id === item.source_product_id) ? <input type="number" min="0.01" max={Number(item.available_quantity)} step="0.01" value={aggregation.allocations.find((allocation) => allocation.source_product_id === item.source_product_id)?.quantity || ''} onChange={(event) => updateAllocation(item.source_product_id, event.target.value)} className="w-24 rounded-lg border border-slate-300 px-2 py-1" aria-label={`Quantity for ${item.product_name}`} /> : null}</label>)}</div></section></div>
      <form onSubmit={submitAggregation} className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:grid-cols-2"><h2 className="md:col-span-2 text-lg font-semibold">Create aggregated listing</h2>{['name', 'category', 'unit', 'price_per_unit', 'location'].map((field) => <label key={field} className="text-sm font-medium capitalize text-slate-700">{field.replaceAll('_', ' ')}<input required={!['location'].includes(field)} name={field} type={field === 'price_per_unit' ? 'number' : 'text'} value={aggregation[field]} onChange={(event) => setAggregation({ ...aggregation, [field]: event.target.value })} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2.5" /></label>)}<button disabled={isSaving || aggregation.allocations.length === 0} type="submit" className="rounded-xl bg-emerald-600 px-4 py-2.5 font-semibold text-white disabled:opacity-60 md:col-span-2">Reserve supply and publish listing</button></form>
      <div className="grid gap-6 xl:grid-cols-2"><section><h2 className="mb-3 text-xl font-semibold">Aggregated listings</h2>{listings.length === 0 ? <EmptyMessage title="No aggregated listings" description="Select member inventory to publish supply." /> : listings.map((listing) => <div key={listing.id} className="mb-2 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"><p className="font-semibold">{listing.name}</p><p className="text-sm text-slate-500">{listing.quantity} {listing.unit} • ₹{listing.price_per_unit}/{listing.unit}</p></div>)}</section><section><h2 className="mb-3 text-xl font-semibold">Bulk orders</h2>{orders.length === 0 ? <EmptyMessage title="No bulk orders" description="Orders for aggregated listings appear here." /> : orders.map((order) => <div key={order.id} className="mb-2 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"><p className="font-semibold">Order #{order.id}</p><p className="text-sm text-slate-500">{order.status} • ₹{order.total_amount}</p></div>)}</section></div>
    </div>
  )
}

export default FpoDashboardPage
