import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import NewsPage from './pages/NewsPage'
import CalendarPage from './pages/CalendarPage'
import QuotesPage from './pages/QuotesPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="noticias" element={<NewsPage />} />
          <Route path="calendario" element={<CalendarPage />} />
          <Route path="cotacoes" element={<QuotesPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
