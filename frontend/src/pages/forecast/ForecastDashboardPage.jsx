import { useState } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { requestForecast, trainForecastModel } from '../../services/forecastService'
import { ErrorMessage, LoadingMessage } from '../../components/marketplace/StateMessage'

function ForecastDashboardPage() {
  const { token } = useAuth()
  const [form, setForm] = useState({ product: '', location: '', buyer_type: 'BULK_BUYER', price: '', start_date: '', days_ahead: 7 })
  const [forecast, setForecast] = useState(null)
  const [training, setTraining] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  async function submitForecast(event) {
    event.preventDefault()
    setIsLoading(true)
    setError('')
    setMessage('')
    try {
      const result = await requestForecast(token, { ...form, price: Number(form.price), days_ahead: Number(form.days_ahead), start_date: form.start_date || null })
      setForecast(result)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setIsLoading(false)
    }
  }

  async function trainModel() {
    setIsLoading(true)
    setError('')
    setMessage('')
    try {
      const result = await trainForecastModel(token)
      setTraining(result)
      setMessage(`Model trained on ${result.training_rows} validated observations.`)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setIsLoading(false)
    }
  }

  function updateField(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  return (
    <div className="space-y-6">
      <header className="rounded-2xl bg-teal-800 p-6 text-white shadow-lg sm:p-8">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-teal-100">Demand intelligence</p>
        <h1 className="mt-3 text-3xl font-bold">Demand forecast</h1>
        <p className="mt-3 max-w-2xl text-teal-50">Use validated historical order data to estimate upcoming product demand.</p>
      </header>
      {error ? <ErrorMessage message={error} /> : null}
      {message ? <p className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{message}</p> : null}
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div><h2 className="text-lg font-semibold text-slate-800">Forecast request</h2><p className="mt-1 text-sm text-slate-500">The model compares linear regression with a historical-mean baseline during training.</p></div>
          <button type="button" onClick={trainModel} disabled={isLoading} className="rounded-xl border border-teal-700 px-3 py-2 text-sm font-semibold text-teal-800 hover:bg-teal-50 disabled:opacity-60">{isLoading ? 'Working...' : 'Train model'}</button>
        </div>
        <form onSubmit={submitForecast} className="mt-5 grid gap-4 md:grid-cols-2">
          <label className="text-sm font-medium text-slate-700">Product<input required name="product" value={form.product} onChange={updateField} placeholder="Tomato" className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2.5" /></label>
          <label className="text-sm font-medium text-slate-700">Location<input required name="location" value={form.location} onChange={updateField} placeholder="Birbhum" className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2.5" /></label>
          <label className="text-sm font-medium text-slate-700">Buyer type<select name="buyer_type" value={form.buyer_type} onChange={updateField} className="mt-1.5 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5"><option>FARMER</option><option>FPO</option><option>CONSUMER</option><option>BULK_BUYER</option></select></label>
          <label className="text-sm font-medium text-slate-700">Expected price per unit<input required min="0.01" step="0.01" type="number" name="price" value={form.price} onChange={updateField} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2.5" /></label>
          <label className="text-sm font-medium text-slate-700">Start date<input type="date" name="start_date" value={form.start_date} onChange={updateField} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2.5" /></label>
          <label className="text-sm font-medium text-slate-700">Forecast days<input required min="1" max="30" type="number" name="days_ahead" value={form.days_ahead} onChange={updateField} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2.5" /></label>
          <button disabled={isLoading} type="submit" className="rounded-xl bg-teal-700 px-4 py-2.5 font-semibold text-white hover:bg-teal-800 disabled:opacity-60 md:col-span-2">{isLoading ? 'Calculating...' : 'Generate forecast'}</button>
        </form>
      </section>
      {isLoading ? <LoadingMessage message="Processing forecast request..." /> : null}
      {training ? <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="text-lg font-semibold">Training evaluation</h2><p className="mt-2 text-sm text-slate-600">Selected model: {training.selected_model}. Data source: {training.data_source}. Metrics are measured on a chronological holdout, not fabricated.</p><div className="mt-4 grid gap-3 sm:grid-cols-3"><Metric label="Baseline MAE" value={training.baseline.mae} /><Metric label="Regression MAE" value={training.regression.mae} /><Metric label="Regression MAPE" value={`${training.regression.mape}%`} /></div></section> : null}
      {forecast ? <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-xl font-semibold text-slate-800">{forecast.product} in {forecast.location}</h2><p className="mt-1 text-sm text-slate-500">Forecast period: {forecast.forecast_period} • Model: {forecast.model_name}</p></div><span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">{forecast.data_source}</span></div><div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{forecast.forecast.map((point) => <div key={point.date} className="rounded-xl bg-teal-50 p-4"><p className="text-sm text-teal-800">{point.date}</p><p className="mt-2 text-2xl font-bold text-teal-900">{point.predicted_demand}</p><p className="text-xs text-teal-700">predicted units</p></div>)}</div><div className="mt-5 rounded-xl bg-amber-50 p-4 text-sm text-amber-900"><p className="font-semibold">Limitations</p><ul className="mt-2 list-disc space-y-1 pl-5">{forecast.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul></div></section> : null}
    </div>
  )
}

function Metric({ label, value }) {
  return <div className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-slate-500">{label}</p><p className="mt-1 text-lg font-semibold text-slate-800">{value}</p></div>
}

export default ForecastDashboardPage
