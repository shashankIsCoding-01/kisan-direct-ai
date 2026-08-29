import { useEffect, useState } from 'react'
import ProductCard from '../../components/marketplace/ProductCard'
import { EmptyMessage, ErrorMessage, LoadingMessage } from '../../components/marketplace/StateMessage'
import { useAuth } from '../../hooks/useAuth'
import { getProducts, addToCart } from '../../services/marketplaceService'

function MarketplacePage() {
  const { token, user } = useAuth()
  const [filters, setFilters] = useState({ search: '', category: '', sort: 'newest' })
  const [products, setProducts] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [cartMessage, setCartMessage] = useState('')
  const [addingId, setAddingId] = useState(null)

  useEffect(() => {
    let isCurrent = true
    getProducts(filters)
      .then((result) => { if (isCurrent) setProducts(result.items) })
      .catch((requestError) => { if (isCurrent) setError(requestError.message) })
      .finally(() => { if (isCurrent) setIsLoading(false) })
    return () => { isCurrent = false }
  }, [filters])

  async function handleAddToCart(productId) {
    if (!token || !user) {
      setCartMessage('Sign in as a consumer or bulk buyer to add products to your cart.')
      return
    }
    setAddingId(productId)
    setCartMessage('')
    try {
      await addToCart(token, { product_id: productId, quantity: 1 })
      setCartMessage('Product added to your cart.')
    } catch (requestError) {
      setCartMessage(requestError.message)
    } finally {
      setAddingId(null)
    }
  }

  return (
    <div className="space-y-6">
      <header className="rounded-2xl bg-emerald-700 p-6 text-white shadow-lg sm:p-8">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-emerald-100">Direct from producers</p>
        <h1 className="mt-3 text-3xl font-bold sm:text-4xl">Fresh produce marketplace</h1>
        <p className="mt-3 max-w-2xl text-emerald-50">Browse active listings from farmers and FPOs.</p>
      </header>

      <section className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm md:grid-cols-[1fr_220px_180px]" aria-label="Product filters">
        <label className="text-sm font-medium text-slate-700">
          Search products
          <input value={filters.search} onChange={(event) => setFilters({ ...filters, search: event.target.value })} placeholder="Try tomatoes" className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2.5 outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100" />
        </label>
        <label className="text-sm font-medium text-slate-700">
          Category
          <input value={filters.category} onChange={(event) => setFilters({ ...filters, category: event.target.value })} placeholder="Vegetables" className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2.5 outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100" />
        </label>
        <label className="text-sm font-medium text-slate-700">
          Sort by
          <select value={filters.sort} onChange={(event) => setFilters({ ...filters, sort: event.target.value })} className="mt-1.5 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100">
            <option value="newest">Newest</option>
            <option value="price_asc">Price: low to high</option>
            <option value="price_desc">Price: high to low</option>
            <option value="name">Name</option>
          </select>
        </label>
      </section>

      {cartMessage ? <p className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{cartMessage}</p> : null}
      {isLoading ? <LoadingMessage message="Loading available products..." /> : null}
      {error ? <ErrorMessage message={error} /> : null}
      {!isLoading && !error && products.length === 0 ? <EmptyMessage title="No products found" description="Try a different search or category." /> : null}
      {!isLoading && !error && products.length > 0 ? (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {products.map((product) => <ProductCard key={product.id} product={product} onAddToCart={handleAddToCart} isAdding={addingId === product.id} />)}
        </div>
      ) : null}
    </div>
  )
}

export default MarketplacePage
