import { Navigate, Outlet, useLocation } from 'react-router'
import { useAuth } from '../../hooks/useAuth'

function ProtectedRoute() {
  const { user, isCheckingSession } = useAuth()
  const location = useLocation()

  if (isCheckingSession) {
    return <p className="rounded-xl bg-white p-6 text-slate-600 shadow-sm" role="status">Checking your session...</p>
  }

  return user ? <Outlet /> : <Navigate to="/auth/login" replace state={{ from: location }} />
}

export default ProtectedRoute
