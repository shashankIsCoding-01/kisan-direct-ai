import { useEffect, useState } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { createProduct, deactivateProduct, getOwnProducts, getSellerNotifications, getSellerOrders, updateProduct } from '../../services/marketplaceService'
import { EmptyMessage, ErrorMessage, LoadingMessage } from '../../components/marketplace/StateMessage'

const initialForm = { name: '', description: '', category: '', unit: 'kg', price_per_unit: '', quantity: '', location: '', image_url: '' }

function FarmerListingsPage() {
  const { token } = useAuth()
  const [products, setProducts] = useState([])
  const [orders, setOrders] = useState([])
  const [notifications, setNotifications] = useState([])
  const [form, setForm] = useState(initialForm)
  const [editingId, setEditingId] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  async function loadData() {
    setIsLoading(true)
    setError('')
    try {
      const [listingResult, orderResult, notificationResult] = await Promise.all([
        getOwnProducts(token), getSellerOrders(token), getSellerNotifications(token),
      ])
      setProducts(listingResult)
      setOrders(orderResult)
      setNotifications(notificationResult)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    let isCurrent = true
    Promise.all([getOwnProducts(token), getSellerOrders(token), getSellerNotifications(token)])
      .then(([listingResult, orderResult, notificationResult]) => {
        if (!isCurrent) return
        setProducts(listingResult)
        setOrders(orderResult)
        setNotifications(notificationResult)
      })
      .catch((requestError) => { if (isCurrent) setError(requestError.message) })
      .finally(() => { if (isCurrent) setIsLoading(false) })
    return () => { isCurrent = false }
  }, [token])

  function updateField(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  function beginEdit(product) {
    setEditingId(product.id)
    setForm({ ...product, price_per_unit: String(product.price_per_unit), quantity: String(product.quantity) })
    setMessage('')
  }

  function resetForm() {
    setEditingId(null)
    setForm(initialForm)
  }

  async function submit(event) {
    event.preventDefault()
    setIsSaving(true)
    setError('')
    setMessage('')
    try {
      const payload = { ...form, price_per_unit: Number(form.price_per_unit), quantity: Number(form.quantity) }
      if (editingId) await updateProduct(token, editingId, payload)
      else await createProduct(token, payload)
      setMessage(editingId ? 'Listing updated.' : 'Listing created.')
      resetForm()
      await loadData()
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setIsSaving(false)
    }
  }

  async function deactivate(id) {
    setError('')
    try {
      await deactivateProduct(token, id)
      setMessage('Listing deactivated.')
      await loadData()
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  if (isLoading) return <LoadingMessage message="Loading your listings..." />

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div><p className="text-sm font-semibold uppercase tracking-[0.2em] text-emerald-700">Farmer workspace</p><h1 className="mt-2 text-3xl font-bold text-slate-900">Product management</h1><p className="mt-2 text-slate-600">Create, update, and deactivate your active listings.</p></div>
      </header>
      {error ? <ErrorMessage message={error} /> : null}
      {message ? <p className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{message}</p> : null}

      <form onSubmit={submit} className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:grid-cols-2" aria-label="Product listing form">
        <h2 className="md:col-span-2 text-lg font-semibold text-slate-800">{editingId ? 'Edit listing' : 'Create listing'}</h2>
        {['name', 'category', 'unit', 'price_per_unit', 'quantity', 'location', 'image_url'].map((field) => (
          <label key={field} className="text-sm font-medium capitalize text-slate-700">{field.replaceAll('_', ' ')}
            <input required={!['location', 'image_url'].includes(field)} type={['price_per_unit', 'quantity'].includes(field) ? 'number' : 'text'} min={['price_per_unit', 'quantity'].includes(field) ? '0.01' : undefined} step="0.01" name={field} value={form[field] || ''} onChange={updateField} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2.5 outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100" />
          </label>
        ))}
        <label className="text-sm font-medium text-slate-700 md:col-span-2">Description
          <textarea name="description" value={form.description || ''} onChange={updateField} rows="3" className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2.5 outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100" />
        </label>
        <div className="flex gap-3 md:col-span-2"><button disabled={isSaving} type="submit" className="rounded-xl bg-emerald-600 px-4 py-2.5 font-semibold text-white hover:bg-emerald-700 disabled:opacity-60">{isSaving ? 'Saving...' : editingId ? 'Save changes' : 'Create listing'}</button>{editingId ? <button type="button" onClick={resetForm} className="rounded-xl border border-slate-300 px-4 py-2.5 font-semibold text-slate-700 hover:bg-slate-50">Cancel</button> : null}</div>
      </form>

      <section className="space-y-3" aria-label="Your listings"><h2 className="text-xl font-semibold text-slate-800">Your listings</h2>{products.length === 0 ? <EmptyMessage title="No listings yet" description="Create your first produce listing above." /> : products.map((product) => <div key={product.id} className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between"><div><p className="font-semibold text-slate-900">{product.name}</p><p className="text-sm text-slate-500">{product.quantity} {product.unit} • ₹{product.price_per_unit}/{product.unit} • {product.is_active ? 'Active' : 'Deactivated'}</p></div><div className="flex gap-2"><button type="button" onClick={() => beginEdit(product)} className="rounded-xl border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">Edit</button>{product.is_active ? <button type="button" onClick={() => deactivate(product.id)} className="rounded-xl border border-red-200 px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-50">Deactivate</button> : null}</div></div>)}</section>

      <div className="grid gap-6 lg:grid-cols-2"><section className="space-y-3" aria-label="Seller orders"><h2 className="text-xl font-semibold text-slate-800">Orders received</h2>{orders.length === 0 ? <EmptyMessage title="No orders yet" description="Orders for your listings will appear here." /> : orders.map((order) => <div key={order.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><div className="flex justify-between"><span className="font-semibold">Order #{order.id}</span><span className="text-sm text-emerald-700">{order.status}</span></div><p className="mt-2 text-sm text-slate-600">₹{order.total_amount} • {order.shipping_address}</p></div>)}</section><section className="space-y-3" aria-label="Order notifications"><h2 className="text-xl font-semibold text-slate-800">Notifications</h2>{notifications.length === 0 ? <EmptyMessage title="No notifications" description="New orders will appear here." /> : notifications.map((notification) => <div key={notification.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><p className="font-semibold text-slate-800">{notification.title}</p><p className="mt-1 text-sm text-slate-600">{notification.message}</p></div>)}</section></div>
    </div>
  )
}

export default FarmerListingsPage
