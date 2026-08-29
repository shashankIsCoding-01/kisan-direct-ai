import { useEffect, useState } from 'react'
import MetricCard from '../../components/analytics/MetricCard'
import { ErrorMessage, LoadingMessage } from '../../components/marketplace/StateMessage'
import { useAuth } from '../../hooks/useAuth'
import { getAnalyticsDashboard } from '../../services/analyticsService'

const platformMetrics = [
  ['registered_farmers', 'Registered farmers'],
  ['active_fpos', 'Active FPOs'],
  ['active_buyers', 'Active bulk buyers'],
  ['active_consumers', 'Active consumers'],
  ['products_listed', 'Products listed'],
  ['orders', 'Non-cancelled orders'],
  ['transaction_value', 'Delivered transaction value'],
  ['farmer_realization', 'Farmer realization'],
  ['consumer_price', 'Consumer paid price'],
]

const routeMetrics = [
  ['baseline_route_distance', 'Baseline route distance'],
  ['optimized_route_distance', 'Optimized route distance'],
  ['distance_reduction', 'Distance reduction'],
  ['logistics_distance', 'Logistics distance'],
]

const forecastMetrics = [
  ['forecast_mae', 'Forecast MAE'],
  ['forecast_rmse', 'Forecast RMSE'],
  ['forecast_mape', 'Forecast MAPE'],
]

function MetricGroup({ title, metrics, data, tone }) {
  return (
    <section>
      <div className="mb-3 flex items-end justify-between gap-3">
        <h2 className="text-xl font-semibold text-slate-800">{title}</h2>
        <p className="text-xs text-slate-500">Values are measured from repository records</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {metrics.map(([key, label]) => <MetricCard key={key} label={label} metric={data[key]} tone={tone} />)}
      </div>
    </section>
  )
}

function AnalyticsDashboardPage() {
  const { token } = useAuth()
  const [dashboard, setDashboard] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    getAnalyticsDashboard(token)
      .then((result) => { if (active) setDashboard(result) })
      .catch((requestError) => { if (active) setError(requestError.message) })
      .finally(() => { if (active) setIsLoading(false) })
    return () => { active = false }
  }, [token])

  if (isLoading) return <LoadingMessage message="Loading operational analytics..." />
  if (error) return <ErrorMessage message={error} />
  if (!dashboard) return null

  return (
    <div className="space-y-8">
      <header className="rounded-2xl bg-slate-900 p-6 text-white shadow-lg sm:p-8">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-300">Admin analytics</p>
        <h1 className="mt-3 text-3xl font-bold">Operational impact dashboard</h1>
        <p className="mt-3 max-w-3xl text-slate-300">This dashboard reports what the platform can measure from its own records. It does not turn missing evidence into an impact claim.</p>
        <p className="mt-4 text-xs text-slate-400">Generated {new Date(dashboard.generated_at).toLocaleString()}</p>
      </header>

      <MetricGroup title="Actual platform metrics" metrics={platformMetrics} data={dashboard.actual} tone="emerald" />
      <MetricGroup title="Actual logistics and forecast metrics" metrics={[...routeMetrics, ...forecastMetrics]} data={dashboard.actual} tone="sky" />
      <MetricGroup title="Demo metrics" metrics={[...routeMetrics, ...forecastMetrics]} data={dashboard.demo} tone="amber" />

      <section>
        <h2 className="mb-3 text-xl font-semibold text-slate-800">Estimates and impact claims</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Object.entries(dashboard.estimates).map(([key, metric]) => <MetricCard key={key} label={key.replaceAll('_', ' ')} metric={metric} tone="slate" />)}
        </div>
      </section>

      <section className="rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-950">
        <h2 className="font-semibold">Limitations</h2>
        <ul className="mt-2 list-disc space-y-1 pl-5">{dashboard.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul>
      </section>
    </div>
  )
}

export default AnalyticsDashboardPage
