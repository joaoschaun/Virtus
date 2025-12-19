import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useAuthStore } from './stores/authStore'
import ErrorBoundary from './components/ErrorBoundary'
import { ToastProvider } from './components/ui/Toast'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import TradesPage from './pages/TradesPage'
import PositionsPage from './pages/PositionsPage'
import BotsPage from './pages/BotsPage'
import StrategiesPage from './pages/StrategiesPage'
import AnalysisPage from './pages/AnalysisPage'
import SettingsPage from './pages/SettingsPage'
import SocialMediaPage from './pages/SocialMedia'
import ForexPage from './pages/ForexPage'
import DividendsPage from './pages/DividendsPageV2'  // Nova versão otimizada
import PaperTradingPage from './pages/PaperTradingPage'  // Paper Trading
import MonitoringPage from './pages/MonitoringPage'  // Drawdown, Audit, Metrics
import PortalHome from './portal/PortalHome'
// Brapi - Mercado Brasileiro
import StocksPage from './pages/StocksPage'
import CryptoPage from './pages/CryptoPage'
import FIIsPage from './pages/FIIsPage'
import CurrencyPage from './pages/CurrencyPage'
import IndicatorsPage from './pages/IndicatorsPage'
import MarketOverviewPage from './pages/MarketOverviewPage'
// Screener e Carteira FIIs
import ScreenerPage from './pages/ScreenerPage'
import FIIPortfolioPage from './pages/FIIPortfolioPage'

// Query Client com configurações otimizadas
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000, // 30 segundos
      gcTime: 5 * 60 * 1000, // 5 minutos (antigo cacheTime)
      retry: 2,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
    },
  },
})

// Protected Route Component
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  
  return <>{children}</>
}

// Public Route Component (redirect if authenticated)
function PublicRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  
  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }
  
  return <>{children}</>
}

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <BrowserRouter>
            <Routes>
            {/* Public Routes */}
            <Route
              path="/login"
            element={
              <PublicRoute>
                <LoginPage />
              </PublicRoute>
            }
          />
          
          {/* Protected Routes */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="trades" element={<TradesPage />} />
            <Route path="positions" element={<PositionsPage />} />
            <Route path="bots" element={<BotsPage />} />
            <Route path="strategies" element={<StrategiesPage />} />
            <Route path="analysis" element={<AnalysisPage />} />
            <Route path="forex" element={<ForexPage />} />
            <Route path="dividends" element={<DividendsPage />} />
            <Route path="social" element={<SocialMediaPage />} />
            <Route path="paper-trading" element={<PaperTradingPage />} />
            <Route path="monitoring" element={<MonitoringPage />} />
            {/* Brapi - Mercado Brasileiro */}
            <Route path="market-overview" element={<MarketOverviewPage />} />
            <Route path="stocks" element={<StocksPage />} />
            <Route path="crypto" element={<CryptoPage />} />
            <Route path="fiis" element={<FIIsPage />} />
            <Route path="currency" element={<CurrencyPage />} />
            <Route path="indicators" element={<IndicatorsPage />} />
            {/* Screener e Carteira */}
            <Route path="screener" element={<ScreenerPage />} />
            <Route path="fii-portfolio" element={<FIIPortfolioPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
          
          {/* Catch all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      </ToastProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}

export default App
