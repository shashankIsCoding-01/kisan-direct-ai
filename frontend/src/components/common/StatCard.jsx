function StatCard({ label, value, change }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:shadow-md">
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <div className="mt-3 flex items-end justify-between gap-2">
        <p className="text-2xl font-bold tracking-tight text-slate-900">{value}</p>
        <span className="rounded-full bg-emerald-100 px-2 py-1 text-xs font-semibold text-emerald-700">
          {change}
        </span>
      </div>
    </div>
  )
}

export default StatCard
