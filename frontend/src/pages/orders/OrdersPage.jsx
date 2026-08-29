import { useEffect, useState } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { assignDelivery, cancelOrder, getOrders, updateDeliveryStatus, updateOrderStatus } from '../../services/orderService'
import { EmptyMessage, ErrorMessage, LoadingMessage } from '../../components/marketplace/StateMessage'

const orderFlow = ['PENDING', 'CONFIRMED', 'PREPARING', 'READY_FOR_PICKUP', 'IN_TRANSIT', 'DELIVERED']

function statusLabel(status) {
  return status.replaceAll('_', ' ').toLowerCase().replace(/^\w/, (letter) => letter.toUpperCase())
}

function nextAction(order, role) {
  if (role === 'FARMER' || role === 'FPO') {
    return { PENDING: 'CONFIRMED', CONFIRMED: 'PREPARING', PREPARING: 'READY_FOR_PICKUP' }[order.status]
  }
  if (role === 'LOGISTICS' && order.delivery) {
    return order.delivery.status === 'ASSIGNED' ? 'PICKED_UP' : order.delivery.status === 'PICKED_UP' ? 'IN_TRANSIT' : 'DELIVERED'
  }
  return null
}

function OrdersPage() {
  const { token, user } = useAuth()
  const [orders, setOrders] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busyId, setBusyId] = useState(null)

  async function loadOrders() {
    try {
      setError('')
      setOrders(await getOrders(token, user.role))
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    getOrders(token, user.role)
      .then((result) => { if (active) setOrders(result) })
      .catch((requestError) => { if (active) setError(requestError.message) })
      .finally(() => { if (active) setIsLoading(false) })
    return () => { active = false }
  }, [token, user.role])

  async function perform(action, id) {
    setBusyId(id)
    setError('')
    setMessage('')
    try {
      await action()
      setMessage('Order updated successfully.')
      await loadOrders()
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusyId(null)
    }
  }

  async function handleOrderAction(order) {
    const target = nextAction(order, user.role)
    if (target === 'PICKED_UP' || target === 'IN_TRANSIT' || target === 'DELIVERED') {
      return perform(() => updateDeliveryStatus(token, order.delivery.id, target), order.id)
    }
    if (target) return perform(() => updateOrderStatus(token, order.id, target), order.id)
    if (user.role === 'LOGISTICS' && order.status === 'READY_FOR_PICKUP') {
      return perform(() => assignDelivery(token, order.id, user.id), order.id)
    }
    return null
  }

  if (isLoading) return <LoadingMessage message="Loading orders..." />

  const heading = user.role === 'ADMIN' ? 'All orders' : user.role === 'LOGISTICS' ? 'Pickup queue' : user.role === 'CONSUMER' || user.role === 'BULK_BUYER' ? 'My orders' : 'Incoming orders'
  return (
    <div className="space-y-6">
      <header><p className="text-sm font-semibold uppercase tracking-[0.2em] text-emerald-700">Order management</p><h1 className="mt-2 text-3xl font-bold text-slate-900">{heading}</h1><p className="mt-2 text-slate-600">Track each order through its validated delivery lifecycle.</p></header>
      {error ? <ErrorMessage message={error} /> : null}
      {message ? <p className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{message}</p> : null}
      {orders.length === 0 ? <EmptyMessage title="No orders found" description="Orders will appear here when they are available." /> : <div className="space-y-4">{orders.map((order) => <article key={order.id} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"><div><h2 className="font-semibold text-slate-900">Order #{order.id}</h2><p className="mt-1 text-sm text-slate-500">{order.shipping_address} • ₹{order.total_amount}</p></div><span className="w-fit rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">{statusLabel(order.status)}</span></div><div className="mt-5 grid gap-2 sm:grid-cols-3">{order.items.map((item) => <p key={item.product_id} className="text-sm text-slate-600">{item.product_name} × {item.quantity} {item.unit_price ? `at ₹${item.unit_price}` : ''}</p>)}</div><div className="mt-5 flex flex-wrap gap-2">{orderFlow.map((state) => <span key={state} className={`rounded-full px-2.5 py-1 text-xs ${state === order.status ? 'bg-emerald-600 text-white' : orderFlow.indexOf(state) < orderFlow.indexOf(order.status) ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-400'}`}>{statusLabel(state)}</span>)}</div>{user.role === 'CONSUMER' && order.status === 'PENDING' ? <button disabled={busyId === order.id} onClick={() => perform(() => cancelOrder(token, order.id), order.id)} type="button" className="mt-5 rounded-xl border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 hover:bg-red-50 disabled:opacity-60">Cancel order</button> : null}{(user.role === 'FARMER' || user.role === 'FPO' || user.role === 'LOGISTICS') && (nextAction(order, user.role) || order.status === 'READY_FOR_PICKUP') ? <button disabled={busyId === order.id} onClick={() => handleOrderAction(order)} type="button" className="mt-5 rounded-xl bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-60">{busyId === order.id ? 'Updating...' : user.role === 'LOGISTICS' && !order.delivery ? 'Assign delivery' : `Set ${statusLabel(nextAction(order, user.role))}`}</button> : null}</article>)}</div>}
    </div>
  )
}

export default OrdersPage
