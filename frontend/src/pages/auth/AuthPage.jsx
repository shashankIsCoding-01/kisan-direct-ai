import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router'
import { useAuth } from '../../hooks/useAuth'

const roles = [
  ['FARMER', 'Farmer'],
  ['FPO', 'FPO'],
  ['CONSUMER', 'Consumer'],
  ['BULK_BUYER', 'Bulk Buyer'],
]

function AuthPage({ mode = 'login' }) {
  const isRegister = mode === 'register'
  const { signIn, signUp } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [form, setForm] = useState({ email: '', password: '', full_name: '', role: 'CONSUMER' })
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  function updateField(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  async function submit(event) {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      if (isRegister) {
        await signUp(form)
      } else {
        await signIn({ email: form.email, password: form.password })
      }
      navigate(location.state?.from?.pathname || '/farmer', { replace: true })
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="mx-auto max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-emerald-700">KisanDirect AI</p>
      <h1 className="mt-3 text-3xl font-bold text-slate-900">{isRegister ? 'Create your account' : 'Welcome back'}</h1>
      <p className="mt-2 text-sm text-slate-600">{isRegister ? 'Join the direct agricultural marketplace.' : 'Sign in to continue to your workspace.'}</p>

      {error ? <div className="mt-5 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700" role="alert">{error}</div> : null}

      <form className="mt-6 space-y-4" onSubmit={submit}>
        {isRegister ? (
          <label className="block text-sm font-medium text-slate-700">
            Full name
            <input required minLength={2} maxLength={150} name="full_name" value={form.full_name} onChange={updateField} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2.5 text-slate-900 outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100" />
          </label>
        ) : null}

        <label className="block text-sm font-medium text-slate-700">
          Email address
          <input required type="email" name="email" autoComplete="email" value={form.email} onChange={updateField} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2.5 text-slate-900 outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100" />
        </label>

        <label className="block text-sm font-medium text-slate-700">
          Password
          <input required minLength={8} maxLength={128} type="password" name="password" autoComplete={isRegister ? 'new-password' : 'current-password'} value={form.password} onChange={updateField} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2.5 text-slate-900 outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100" />
        </label>

        {isRegister ? (
          <label className="block text-sm font-medium text-slate-700">
            Account type
            <select name="role" value={form.role} onChange={updateField} className="mt-1.5 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-slate-900 outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100">
              {roles.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
        ) : null}

        <button disabled={isSubmitting} type="submit" className="w-full rounded-xl bg-emerald-600 px-4 py-3 font-semibold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60">
          {isSubmitting ? 'Please wait...' : isRegister ? 'Create account' : 'Sign in'}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-600">
        {isRegister ? 'Already have an account? ' : 'Need an account? '}
        <Link className="font-semibold text-emerald-700 hover:text-emerald-800" to={isRegister ? '/auth/login' : '/auth/register'}>
          {isRegister ? 'Sign in' : 'Register'}
        </Link>
      </p>
    </section>
  )
}

export default AuthPage
