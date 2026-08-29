import { Link } from 'react-router'

function ProductCard({ product, onAddToCart, isAdding }) {
  return (
    <article className="flex h-full flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
      <div className="flex aspect-[4/3] items-center justify-center bg-emerald-50 p-6">
        {product.image_url ? (
          <img src={product.image_url} alt={product.name} className="h-full w-full object-cover" />
        ) : (
          <span className="text-5xl" aria-hidden="true">🌾</span>
        )}
      </div>
      <div className="flex flex-1 flex-col p-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-emerald-700">{product.category}</p>
        <Link to={`/marketplace/products/${product.id}`} className="mt-1 text-lg font-semibold text-slate-900 hover:text-emerald-700">
          {product.name}
        </Link>
        <p className="mt-2 text-sm text-slate-500">{product.quantity} {product.unit} available</p>
        <div className="mt-auto flex items-center justify-between gap-3 pt-4">
          <p className="font-bold text-slate-900">₹{product.price_per_unit}<span className="text-xs font-normal text-slate-500">/{product.unit}</span></p>
          {onAddToCart ? (
            <button disabled={isAdding} onClick={() => onAddToCart(product.id)} type="button" className="rounded-xl bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60">
              {isAdding ? 'Adding...' : 'Add to cart'}
            </button>
          ) : null}
        </div>
      </div>
    </article>
  )
}

export default ProductCard
