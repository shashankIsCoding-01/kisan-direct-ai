export function LoadingMessage({ message = 'Loading...' }) {
  return <p className="rounded-xl border border-slate-200 bg-white p-5 text-sm text-slate-600" role="status">{message}</p>
}

export function ErrorMessage({ message }) {
  return <p className="rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-700" role="alert">{message}</p>
}

export function EmptyMessage({ title, description }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center">
      <h2 className="font-semibold text-slate-800">{title}</h2>
      <p className="mt-2 text-sm text-slate-500">{description}</p>
    </div>
  )
}
