function MetricCard({ label, metric, tone = 'emerald' }) {
  const toneClasses = {
    emerald: 'border-emerald-100 bg-emerald-50 text-emerald-900',
    sky: 'border-sky-100 bg-sky-50 text-sky-900',
    amber: 'border-amber-100 bg-amber-50 text-amber-900',
    slate: 'border-slate-200 bg-slate-50 text-slate-900',
  }
  const value = metric.value === null || metric.value === undefined ? 'Not available' : metric.value

  return (
    <article className={`rounded-2xl border p-4 ${toneClasses[tone]}`}>
      <p className="text-sm font-medium opacity-70">{label}</p>
      <p className="mt-3 break-words text-2xl font-bold">{value}</p>
      {metric.unit ? <p className="mt-1 text-xs opacity-70">{metric.unit}</p> : null}
      <p className="mt-3 text-xs opacity-70">Source: {metric.source}</p>
      <details className="mt-3 text-xs opacity-80">
        <summary className="cursor-pointer font-medium">Calculation</summary>
        <p className="mt-2">{metric.calculation}</p>
      </details>
    </article>
  )
}

export default MetricCard
