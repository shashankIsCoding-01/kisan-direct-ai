import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'
import { getProduct, addToCart } from '../../services/marketplaceService'
import { useAuth } from '../../hooks/useAuth'
import { ErrorMessage, LoadingMessage } from '../../components/marketplace/StateMessage'

function ProductDetailsPage() {
  const { productId } = useParams()
  const { token, user } = useAuth()
  const [product, setProduct] = useState(null)
  const [quantity, setQuantity] = useState('1')
  const [statusMessage, setStatusMessage] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    getProduct(productId).then(setProduct).catch((requestError) => setError(requestError.message)).finally(() => setIsLoading(false))
  }, [productId])

  async function handleAddToCart() {
    if (!token || !user) {
      setStatusMessage('Sign in as a consumer or bulk buyer to add products to your cart.')
      return
    }
    try {
      await addToCart(token, { product_id: Number(productId), quantity: Number(quantity) })
      setStatusMessage('Product added to your cart.')
    } catch (requestError) {
      setStatusMessage(requestError.message)
    }
  }

  if (isLoading) return <LoadingMessage message="Loading product details..." />
  if (error) return <ErrorMessage message={error} />
  if (!product) return null

  return (
    <div className="space-y-5">
      <Link to="/marketplace" className="text-sm font-semibold text-emerald-700 hover:text-emerald-800">← Back to marketplace</Link>
      <article className="grid gap-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:grid-cols-2 md:p-8">
        <div className="flex aspect-square items-center justify-center rounded-xl bg-emerald-50 p-8">
          {product.image_url ? <img src={product.image_url} alt={product.name} className="h-full w-full rounded-xl object-cover" /> : <span className="text-8xl" aria-hidden="true">🌾</span>}
        </div>
        <div className="flex flex-col justify-center">
          <p className="text-sm font-semibold uppercase tracking-wider text-emerald-700">{product.category}</p>
          <h1 className="mt-2 text-3xl font-bold text-slate-900">{product.name}</h1>
          <p className="mt-4 text-slate-600">{product.description || 'Fresh produce listed directly by the producer.'}</p>
          <p className="mt-6 text-2xl font-bold text-slate-900">₹{product.price_per_unit}<span className="text-sm font-normal text-slate-500"> / {product.unit}</span></p>
          <p className="mt-2 text-sm text-slate-500">{product.quantity} {product.unit} available{product.location ? ` in ${product.location}` : ''}</p>
          <div className="mt-6 flex max-w-sm gap-3">
            <label className="flex-1 text-sm font-medium text-slate-700">Quantity
              <input type="number" min="1" max={Number(product.quantity)} step="0.01" value={quantity} onChange={(event) => setQuantity(event.target.value)} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2.5 outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100" />
            </label>
            <button type="button" onClick={handleAddToCart} className="self-end rounded-xl bg-emerald-600 px-4 py-3 font-semibold text-white hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2">Add to cart</button>
          </div>
          {statusMessage ? <p className="mt-4 text-sm text-emerald-700" role="status">{statusMessage}</p> : null}
        </div>
      </article>
    </div>
  )
}

export default ProductDetailsPage
