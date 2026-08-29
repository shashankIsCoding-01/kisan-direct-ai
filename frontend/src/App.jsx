import { BrowserRouter, Routes, Route, NavLink } from 'react-router'
import ProtectedRoute from './components/auth/ProtectedRoute'
import { AuthProvider } from './context/AuthContext.jsx'
import { useAuth } from './hooks/useAuth'
import FarmerListingsPage from './pages/farmer/FarmerListingsPage'
import AuthPage from './pages/auth/AuthPage'
import MarketplacePage from './pages/marketplace/MarketplacePage'
import ProductDetailsPage from './pages/marketplace/ProductDetailsPage'
import OrdersPage from './pages/orders/OrdersPage'
import FpoDashboardPage from './pages/fpo/FpoDashboardPage'
import BulkBuyerPage from './pages/bulk/BulkBuyerPage'
import ForecastDashboardPage from './pages/forecast/ForecastDashboardPage'
import LogisticsDashboardPage from './pages/logistics/LogisticsDashboardPage'
import AnalyticsDashboardPage from './pages/admin/AnalyticsDashboardPage'

const navItems = [
  { to: '/', label: 'Home' },
  { to: '/marketplace', label: 'Marketplace' },
  { to: '/orders', label: 'Orders' },
  { to: '/forecast', label: 'Forecast' },
  { to: '/auth/login', label: 'Login' },
  { to: '/farmer', label: 'Farmer' },
  { to: '/fpo', label: 'FPO' },
  { to: '/consumer', label: 'Consumer' },
  { to: '/bulk-buyer', label: 'Bulk Buyer' },
  { to: '/logistics', label: 'Logistics' },
  { to: '/admin', label: 'Admin' },
]

function AppLayout({ children }) {
  const { user, signOut } = useAuth()

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <header className="border-b border-slate-200 bg-white shadow-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4">
          <div>
            <h1 className="text-xl font-bold text-emerald-700">KisanDirect AI</h1>
          </div>

          <nav className="flex flex-wrap items-center gap-3 text-sm font-medium" aria-label="Primary navigation">
            {navItems.filter((item) => item.to !== '/auth/login' || !user).map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `rounded-full px-3 py-2 transition ${
                    isActive
                      ? 'bg-emerald-600 text-white'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
            {user ? (
              <button type="button" onClick={signOut} className="rounded-full border border-slate-300 px-3 py-2 text-slate-700 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2">
                Sign out
              </button>
            ) : null}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8">{children}</main>
    </div>
  )
}

function HomePage() {
  return (
    <section className="space-y-6">
      <div className="rounded-2xl bg-gradient-to-r from-emerald-600 to-green-500 p-8 text-white shadow-lg">
        <p className="mb-2 text-sm font-medium uppercase tracking-[0.2em] text-emerald-100">
          Digital agriculture marketplace
        </p>
        <h2 className="text-4xl font-bold">Connecting farmers, FPOs, and buyers directly</h2>
        <p className="mt-4 max-w-2xl text-emerald-50">
          Clean marketplace foundation for inventory, orders, logistics, and analytics.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-800">Farmers</h3>
          <p className="mt-2 text-slate-600">List produce, manage stock, and improve realization.</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-800">FPOs</h3>
          <p className="mt-2 text-slate-600">Aggregate supply and coordinate collective selling.</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-800">Consumers</h3>
          <p className="mt-2 text-slate-600">Buy directly from verified sources and track delivery.</p>
        </div>
      </div>
    </section>
  )
}

function PlaceholderPage({ title, description }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
      <h2 className="text-2xl font-bold text-slate-800">{title}</h2>
      <p className="mt-3 text-slate-600">{description}</p>
      <div className="mt-6 rounded-xl bg-slate-100 p-4 text-sm text-slate-600">
        Frontend foundation only. Business features will be added later.
      </div>
    </section>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppLayout>
          <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/auth/login" element={<AuthPage mode="login" />} />
          <Route path="/auth/register" element={<AuthPage mode="register" />} />
          <Route path="/marketplace" element={<MarketplacePage />} />
          <Route path="/marketplace/products/:productId" element={<ProductDetailsPage />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/farmer" element={<FarmerListingsPage />} />
            <Route path="/orders" element={<OrdersPage />} />
            <Route path="/fpo" element={<FpoDashboardPage />} />
            <Route path="/bulk-buyer" element={<BulkBuyerPage />} />
            <Route path="/forecast" element={<ForecastDashboardPage />} />
            <Route path="/logistics" element={<LogisticsDashboardPage />} />
            <Route path="/admin" element={<AnalyticsDashboardPage />} />
          </Route>
          <Route
            path="/consumer"
            element={
              <PlaceholderPage
                title="Consumer Marketplace"
                description="Browse products and place orders from this area."
              />
            }
          />
          </Routes>
        </AppLayout>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
