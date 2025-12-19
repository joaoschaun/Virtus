import React, { useState, useEffect } from 'react';
import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  Calendar,
  BarChart3,
  Target,
  AlertTriangle,
  CheckCircle,
  Clock,
  RefreshCw,
  Search,
  Filter,
  Star,
  Plus,
  ChevronRight,
  ArrowUpRight,
  ArrowDownRight,
  Loader2,
  Info,
  Instagram,
  Copy,
  Check,
  Building2,
  PieChart,
  Activity
} from 'lucide-react';

// API Base URL - usa caminho relativo para funcionar com Nginx
const API_URL = '/api/dividend-bot';

// Types
interface UpcomingDividend {
  ticker: string;
  company_name: string;
  sector: string;
  current_price: number;
  dividend_type: string;
  value_per_share: number;
  ex_date: string;
  payment_date: string | null;
  dividend_yield: number;
  days_to_ex: number;
  annual_yield: number;
  recommendation: string;
  score: number;
}

interface StockAnalysis {
  ticker: string;
  company_name: string;
  sector: string;
  current_price: number;
  fundamentals: {
    dividend_yield: number;
    annual_dividend: number;
    payout_ratio: number;
    dividend_consistency: number;
    pe_ratio: number;
    pb_ratio: number;
    roe: number;
    debt_to_equity: number;
    market_cap: number;
    avg_volume: number;
    volatility_30d: number;
    price_52w_high: number;
    price_52w_low: number;
  };
  dividend_history: Array<{
    date: string;
    value: number;
  }>;
  source: string;
  last_update: string;
}

interface SocialContent {
  title: string;
  content: string;
  hashtags: string;
  data: any;
}

interface CalendarEvent {
  date: string;
  ticker: string;
  company_name: string;
  event_type: string;
  dividend_value: number;
  dividend_yield: number;
  has_position: boolean;
  // Novos campos
  buy_limit_date: string | null;  // Data limite para comprar
  avg_historical_dividend: number | null;  // Média histórica de dividendos
  company_score: number | null;  // Nota da empresa (0-100)
  sector: string | null;  // Setor
}

interface HealthStatus {
  status: string;
  checks: {
    storage: boolean;
    real_data_service: boolean;
    yahoo_finance: boolean;
    brapi: boolean;
    statusinvest: boolean;
  };
  message: string;
  brapi_key_configured: boolean;
}

// Utility functions
const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL'
  }).format(value);
};

const formatPercent = (value: number) => {
  return `${value.toFixed(2)}%`;
};

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleDateString('pt-BR');
};

const getRecommendationColor = (rec: string) => {
  switch (rec.toLowerCase()) {
    case 'buy': return 'text-green-400 bg-green-400/10';
    case 'wait': return 'text-yellow-400 bg-yellow-400/10';
    case 'avoid': return 'text-red-400 bg-red-400/10';
    default: return 'text-gray-400 bg-gray-400/10';
  }
};

const getRecommendationText = (rec: string) => {
  switch (rec.toLowerCase()) {
    case 'buy': return 'COMPRAR';
    case 'wait': return 'AGUARDAR';
    case 'avoid': return 'EVITAR';
    default: return rec.toUpperCase();
  }
};

const getScoreColor = (score: number) => {
  if (score >= 75) return 'text-green-400';
  if (score >= 55) return 'text-yellow-400';
  return 'text-red-400';
};

// Component
const DividendsPage: React.FC = () => {
  // State
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'calendar' | 'analysis' | 'social'>('overview');
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  
  // Data
  const [upcomingDividends, setUpcomingDividends] = useState<UpcomingDividend[]>([]);
  const [calendarEvents, setCalendarEvents] = useState<CalendarEvent[]>([]);
  const [selectedStock, setSelectedStock] = useState<StockAnalysis | null>(null);
  const [socialContent, setSocialContent] = useState<SocialContent | null>(null);
  
  // Filters
  const [minYield, setMinYield] = useState(3);
  const [daysAhead, setDaysAhead] = useState(30);
  const [searchTicker, setSearchTicker] = useState('');
  const [copiedContent, setCopiedContent] = useState(false);
  
  // Calculadora de Investimento
  const [investmentAmount, setInvestmentAmount] = useState<number>(1000);
  const [selectedCalcTicker, setSelectedCalcTicker] = useState<string>('');

  // Load data on mount
  useEffect(() => {
    loadHealth();
    loadUpcomingDividends();
    loadCalendar();
  }, []);

  // Reload when filters change
  useEffect(() => {
    loadUpcomingDividends();
  }, [minYield, daysAhead]);

  const loadHealth = async () => {
    try {
      const response = await fetch(`${API_URL}/health`);
      const data = await response.json();
      setHealthStatus(data);
    } catch (err) {
      console.error('Erro ao verificar saúde:', err);
    }
  };

  const loadUpcomingDividends = async () => {
    setLoading(true);
    try {
      // Tenta endpoint real primeiro
      let response = await fetch(`${API_URL}/real/upcoming?days_ahead=${daysAhead}&min_yield=${minYield}`);
      
      if (!response.ok) {
        // Fallback para mock
        response = await fetch(`${API_URL}/upcoming?days_ahead=${daysAhead}&min_yield=${minYield}`);
      }
      
      const data = await response.json();
      setUpcomingDividends(data.dividends || []);
      setError(null);
    } catch (err) {
      setError('Erro ao carregar dividendos. Verifique se o backend está rodando.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadCalendar = async () => {
    try {
      const response = await fetch(`${API_URL}/calendar?days_ahead=30`);
      const data = await response.json();
      setCalendarEvents(data.events || []);
    } catch (err) {
      console.error('Erro ao carregar calendário:', err);
    }
  };

  const analyzeStock = async (ticker: string) => {
    setLoading(true);
    try {
      // Tenta endpoint real primeiro
      let response = await fetch(`${API_URL}/real/analyze/${ticker}`);
      
      if (!response.ok) {
        // Fallback para mock
        response = await fetch(`${API_URL}/analyze/${ticker}`);
      }
      
      const data = await response.json();
      setSelectedStock(data);
      setActiveTab('analysis');
    } catch (err) {
      console.error('Erro ao analisar ação:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadSocialContent = async (type: 'daily' | 'weekly' | 'stock', ticker?: string) => {
    setLoading(true);
    try {
      let url = '';
      switch (type) {
        case 'daily':
          url = `${API_URL}/social/daily-opportunities`;
          break;
        case 'weekly':
          url = `${API_URL}/social/weekly-summary`;
          break;
        case 'stock':
          url = `${API_URL}/social/stock-analysis/${ticker}`;
          break;
      }
      
      const response = await fetch(url);
      const data = await response.json();
      setSocialContent(data);
    } catch (err) {
      console.error('Erro ao carregar conteúdo social:', err);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedContent(true);
      setTimeout(() => setCopiedContent(false), 2000);
    } catch (err) {
      console.error('Erro ao copiar:', err);
    }
  };

  // Components
  const HealthBanner = () => {
    if (!healthStatus) return null;
    
    const isHealthy = healthStatus.status === 'healthy';
    const hasRealData = healthStatus.checks.real_data_service;
    
    if (isHealthy && hasRealData) return null;
    
    return (
      <div className={`mb-6 p-4 rounded-lg border ${hasRealData ? 'bg-green-500/10 border-green-500/30' : 'bg-yellow-500/10 border-yellow-500/30'}`}>
        <div className="flex items-start gap-3">
          {hasRealData ? (
            <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
          ) : (
            <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
          )}
          <div>
            <p className={`font-medium ${hasRealData ? 'text-green-400' : 'text-yellow-400'}`}>
              {hasRealData ? 'Serviço de dados reais ativo' : 'Modo de demonstração'}
            </p>
            <p className="text-sm text-virtus-text-secondary mt-1">
              {healthStatus.message}
            </p>
            <div className="flex gap-4 mt-2 text-xs text-virtus-text-muted">
              <span className={healthStatus.checks.yahoo_finance ? 'text-green-400' : 'text-gray-500'}>
                Yahoo: {healthStatus.checks.yahoo_finance ? '✓' : '✗'}
              </span>
              <span className={healthStatus.checks.brapi ? 'text-green-400' : 'text-gray-500'}>
                Brapi: {healthStatus.checks.brapi ? '✓' : '✗'}
              </span>
              <span className={healthStatus.checks.statusinvest ? 'text-green-400' : 'text-gray-500'}>
                StatusInvest: {healthStatus.checks.statusinvest ? '✓' : '✗'}
              </span>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const StatCard = ({ icon: Icon, label, value, subvalue, color }: {
    icon: any;
    label: string;
    value: string;
    subvalue?: string;
    color?: string;
  }) => (
    <div className="card p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-virtus-text-muted">{label}</p>
          <p className={`text-2xl font-bold mt-1 ${color || 'text-white'}`}>{value}</p>
          {subvalue && (
            <p className="text-sm text-virtus-text-secondary mt-1">{subvalue}</p>
          )}
        </div>
        <div className={`p-3 rounded-lg ${color ? `${color.replace('text-', 'bg-')}/20` : 'bg-virtus-accent-primary/20'}`}>
          <Icon className={`w-6 h-6 ${color || 'text-virtus-accent-primary'}`} />
        </div>
      </div>
    </div>
  );

  const DividendCard = ({ dividend }: { dividend: UpcomingDividend }) => (
    <div className="card p-4 hover:border-virtus-accent-primary/50 transition-colors cursor-pointer"
         onClick={() => analyzeStock(dividend.ticker)}>
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-white">{dividend.ticker}</span>
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${getRecommendationColor(dividend.recommendation)}`}>
              {getRecommendationText(dividend.recommendation)}
            </span>
          </div>
          <p className="text-sm text-virtus-text-secondary truncate max-w-[200px]">
            {dividend.company_name}
          </p>
        </div>
        <div className="text-right">
          <p className={`text-lg font-bold ${getScoreColor(dividend.score)}`}>
            {dividend.score.toFixed(0)}
          </p>
          <p className="text-xs text-virtus-text-muted">Score</p>
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <p className="text-virtus-text-muted">Preço</p>
          <p className="font-medium">{formatCurrency(dividend.current_price)}</p>
        </div>
        <div>
          <p className="text-virtus-text-muted">Dividendo</p>
          <p className="font-medium text-green-400">{formatCurrency(dividend.value_per_share)}</p>
        </div>
        <div>
          <p className="text-virtus-text-muted">DY</p>
          <p className="font-medium text-yellow-400">{formatPercent(dividend.dividend_yield)}</p>
        </div>
        <div>
          <p className="text-virtus-text-muted">🛒 Comprar até</p>
          <p className="font-medium text-blue-400">
            {formatDate(new Date(new Date(dividend.ex_date).getTime() - 86400000).toISOString().split('T')[0])}
          </p>
        </div>
      </div>
      
      <div className="grid grid-cols-3 gap-2 text-sm mt-3 pt-3 border-t border-virtus-border-primary">
        <div>
          <p className="text-virtus-text-muted text-xs">📅 Data Ex</p>
          <p className="font-medium text-xs">{formatDate(dividend.ex_date)}</p>
        </div>
        <div>
          <p className="text-virtus-text-muted text-xs">🏷️ Pode vender</p>
          <p className="font-medium text-xs text-orange-400">{formatDate(dividend.ex_date)}</p>
        </div>
        <div>
          <p className="text-virtus-text-muted text-xs">💰 Recebe em</p>
          <p className="font-medium text-xs text-green-400">{dividend.payment_date ? formatDate(dividend.payment_date) : 'A definir'}</p>
        </div>
      </div>
      
      <div className="flex items-center justify-between mt-2 pt-2 border-t border-virtus-border-primary">
        <div className="flex items-center gap-1 text-xs text-virtus-text-muted">
          <Clock className="w-3 h-3" />
          <span>{dividend.days_to_ex} dias para data ex</span>
        </div>
        <span className="text-xs text-virtus-text-secondary">{dividend.sector}</span>
      </div>
    </div>
  );

  // Função para cor do score
  const getScoreBadgeColor = (score: number | null) => {
    if (!score) return 'bg-gray-500/20 text-gray-400';
    if (score >= 75) return 'bg-green-500/20 text-green-400';
    if (score >= 55) return 'bg-yellow-500/20 text-yellow-400';
    return 'bg-red-500/20 text-red-400';
  };

  // Filtra apenas eventos de data ex para o calendário (simplifica a visualização)
  const exDateEvents = calendarEvents.filter(e => e.event_type === 'ex_date');

  const CalendarView = () => (
    <div className="space-y-4">
      {/* Header com explicação clara */}
      <div className="card p-4 bg-gradient-to-r from-yellow-500/10 to-green-500/10 border-yellow-500/30">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-yellow-400">Como funciona o calendário de dividendos:</p>
            <ul className="text-sm text-virtus-text-secondary mt-2 space-y-1">
              <li>📅 <strong className="text-yellow-400">Data Limite</strong> = Último dia para COMPRAR a ação e ter direito ao dividendo</li>
              <li>💰 <strong className="text-green-400">Data Pagamento</strong> = Quando o dividendo será creditado na sua conta</li>
            </ul>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <Calendar className="w-5 h-5 text-virtus-accent-primary" />
          Próximos Dividendos
        </h3>
        <span className="text-xs text-virtus-text-muted">
          {exDateEvents.length} oportunidades nos próximos 30 dias
        </span>
      </div>
      
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-virtus-bg-hover">
              <tr>
                <th className="text-left p-4 text-sm font-medium text-virtus-text-muted">Ação</th>
                <th className="text-left p-4 text-sm font-medium text-virtus-text-muted">Empresa</th>
                <th className="text-center p-4 text-sm font-medium">
                  <div className="flex flex-col items-center">
                    <span className="text-yellow-400">📅 Comprar até</span>
                    <span className="text-xs text-virtus-text-muted">(Data Limite)</span>
                  </div>
                </th>
                <th className="text-center p-4 text-sm font-medium">
                  <div className="flex flex-col items-center">
                    <span className="text-green-400">💰 Pagamento</span>
                    <span className="text-xs text-virtus-text-muted">(Crédito)</span>
                  </div>
                </th>
                <th className="text-right p-4 text-sm font-medium text-virtus-text-muted">Dividendo</th>
                <th className="text-right p-4 text-sm font-medium text-virtus-text-muted">Méd. Hist.</th>
                <th className="text-right p-4 text-sm font-medium text-virtus-text-muted">DY</th>
                <th className="text-center p-4 text-sm font-medium text-virtus-text-muted">Nota</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-virtus-border-primary">
              {exDateEvents.map((event, idx) => {
                // Encontra o evento de pagamento correspondente
                const paymentEvent = calendarEvents.find(
                  e => e.ticker === event.ticker && e.event_type === 'payment_date'
                );
                
                return (
                  <tr key={idx} className={`hover:bg-virtus-bg-hover transition-colors ${
                    event.has_position ? 'bg-virtus-accent-primary/5' : ''
                  }`}>
                    <td className="p-4">
                      <button 
                        onClick={() => analyzeStock(event.ticker)}
                        className="font-bold text-virtus-accent-primary hover:underline text-lg"
                      >
                        {event.ticker}
                      </button>
                      {event.has_position && (
                        <span className="ml-2 text-xs bg-blue-500/20 text-blue-400 px-1 rounded">Posição</span>
                      )}
                    </td>
                    <td className="p-4">
                      <div className="text-virtus-text-secondary">{event.company_name}</div>
                      {event.sector && (
                        <div className="text-xs text-virtus-text-muted">{event.sector}</div>
                      )}
                    </td>
                    <td className="p-4 text-center">
                      {event.buy_limit_date ? (
                        <div className="inline-flex flex-col items-center">
                          <span className="font-bold text-yellow-400 bg-yellow-400/10 px-3 py-1 rounded-lg text-lg">
                            {formatDate(event.buy_limit_date)}
                          </span>
                          <span className="text-xs text-virtus-text-muted mt-1">
                            {(() => {
                              const today = new Date();
                              const limitDate = new Date(event.buy_limit_date);
                              const diffDays = Math.ceil((limitDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
                              if (diffDays < 0) return '⚠️ Expirado';
                              if (diffDays === 0) return '🔥 HOJE!';
                              if (diffDays === 1) return '⏰ Amanhã';
                              return `${diffDays} dias`;
                            })()}
                          </span>
                        </div>
                      ) : (
                        <span className="text-virtus-text-muted">-</span>
                      )}
                    </td>
                    <td className="p-4 text-center">
                      {paymentEvent ? (
                        <span className="font-medium text-green-400 bg-green-400/10 px-3 py-1 rounded-lg">
                          {formatDate(paymentEvent.date)}
                        </span>
                      ) : (
                        <span className="text-virtus-text-muted">A definir</span>
                      )}
                    </td>
                    <td className="p-4 text-right">
                      <span className="font-bold text-green-400 text-lg">
                        {formatCurrency(event.dividend_value)}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      {event.avg_historical_dividend ? (
                        <span className="text-virtus-text-secondary">
                          {formatCurrency(event.avg_historical_dividend)}
                        </span>
                      ) : (
                        <span className="text-virtus-text-muted">-</span>
                      )}
                    </td>
                    <td className="p-4 text-right">
                      <span className="text-green-400 font-medium">
                        {formatPercent(event.dividend_yield)}
                      </span>
                    </td>
                    <td className="p-4 text-center">
                      {event.company_score ? (
                        <span className={`px-2 py-1 rounded text-xs font-bold ${getScoreBadgeColor(event.company_score)}`}>
                          {event.company_score.toFixed(0)}
                        </span>
                      ) : (
                        <span className="text-virtus-text-muted">-</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        
        {/* Legenda simplificada */}
        <div className="p-4 bg-virtus-bg-hover border-t border-virtus-border-primary">
          <div className="flex flex-wrap justify-between items-center gap-4">
            <div className="flex flex-wrap gap-4 text-xs">
              <div className="flex items-center gap-2">
                <span className="px-2 py-1 rounded bg-green-500/20 text-green-400 font-bold">75+</span>
                <span className="text-virtus-text-muted">Ótima</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-2 py-1 rounded bg-yellow-500/20 text-yellow-400 font-bold">55-74</span>
                <span className="text-virtus-text-muted">Boa</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-2 py-1 rounded bg-red-500/20 text-red-400 font-bold">&lt;55</span>
                <span className="text-virtus-text-muted">Atenção</span>
              </div>
            </div>
            <div className="text-xs text-virtus-text-muted">
              Méd. Hist. = Média dos últimos 12 dividendos pagos
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const AnalysisView = () => (
    <div className="space-y-6">
      {/* Search */}
      <div className="flex gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-virtus-text-muted" />
          <input
            type="text"
            placeholder="Buscar ticker (ex: PETR4, VALE3)..."
            value={searchTicker}
            onChange={(e) => setSearchTicker(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === 'Enter' && searchTicker && analyzeStock(searchTicker)}
            className="input pl-10 w-full"
          />
        </div>
        <button
          onClick={() => searchTicker && analyzeStock(searchTicker)}
          disabled={!searchTicker || loading}
          className="btn-primary px-6"
        >
          {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Analisar'}
        </button>
      </div>

      {/* Analysis Result */}
      {selectedStock && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Info */}
          <div className="lg:col-span-2 space-y-6">
            <div className="card p-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h2 className="text-2xl font-bold">{selectedStock.ticker}</h2>
                  <p className="text-virtus-text-secondary">{selectedStock.company_name}</p>
                  <p className="text-sm text-virtus-text-muted mt-1">{selectedStock.sector}</p>
                </div>
                <div className="text-right">
                  <p className="text-3xl font-bold">{formatCurrency(selectedStock.current_price)}</p>
                  <p className="text-xs text-virtus-text-muted mt-1">
                    Fonte: {selectedStock.source}
                  </p>
                </div>
              </div>

              {/* Fundamentals Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-3 bg-virtus-bg-hover rounded-lg">
                  <p className="text-xs text-virtus-text-muted">Dividend Yield</p>
                  <p className="text-lg font-bold text-green-400">
                    {formatPercent(selectedStock.fundamentals.dividend_yield)}
                  </p>
                </div>
                <div className="p-3 bg-virtus-bg-hover rounded-lg">
                  <p className="text-xs text-virtus-text-muted">Payout</p>
                  <p className="text-lg font-bold">
                    {formatPercent(selectedStock.fundamentals.payout_ratio)}
                  </p>
                </div>
                <div className="p-3 bg-virtus-bg-hover rounded-lg">
                  <p className="text-xs text-virtus-text-muted">P/L</p>
                  <p className="text-lg font-bold">
                    {selectedStock.fundamentals.pe_ratio.toFixed(1)}
                  </p>
                </div>
                <div className="p-3 bg-virtus-bg-hover rounded-lg">
                  <p className="text-xs text-virtus-text-muted">P/VP</p>
                  <p className="text-lg font-bold">
                    {selectedStock.fundamentals.pb_ratio.toFixed(2)}
                  </p>
                </div>
                <div className="p-3 bg-virtus-bg-hover rounded-lg">
                  <p className="text-xs text-virtus-text-muted">ROE</p>
                  <p className="text-lg font-bold text-yellow-400">
                    {formatPercent(selectedStock.fundamentals.roe)}
                  </p>
                </div>
                <div className="p-3 bg-virtus-bg-hover rounded-lg">
                  <p className="text-xs text-virtus-text-muted">Dív/PL</p>
                  <p className="text-lg font-bold">
                    {selectedStock.fundamentals.debt_to_equity.toFixed(1)}%
                  </p>
                </div>
                <div className="p-3 bg-virtus-bg-hover rounded-lg">
                  <p className="text-xs text-virtus-text-muted">Vol. 30d</p>
                  <p className="text-lg font-bold">
                    {selectedStock.fundamentals.volatility_30d.toFixed(1)}%
                  </p>
                </div>
                <div className="p-3 bg-virtus-bg-hover rounded-lg">
                  <p className="text-xs text-virtus-text-muted">Consistência</p>
                  <p className="text-lg font-bold text-green-400">
                    {selectedStock.fundamentals.dividend_consistency.toFixed(0)}%
                  </p>
                </div>
              </div>
            </div>

            {/* Price Range */}
            <div className="card p-6">
              <h3 className="text-lg font-semibold mb-4">Faixa de Preço (52 semanas)</h3>
              <div className="relative h-8 bg-virtus-bg-hover rounded-full">
                <div 
                  className="absolute h-full bg-gradient-to-r from-red-500 via-yellow-500 to-green-500 rounded-full opacity-30"
                  style={{ width: '100%' }}
                />
                <div 
                  className="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-white rounded-full border-2 border-virtus-accent-primary shadow-lg"
                  style={{ 
                    left: `${((selectedStock.current_price - selectedStock.fundamentals.price_52w_low) / 
                           (selectedStock.fundamentals.price_52w_high - selectedStock.fundamentals.price_52w_low)) * 100}%` 
                  }}
                />
              </div>
              <div className="flex justify-between mt-2 text-sm">
                <span className="text-red-400">
                  Mín: {formatCurrency(selectedStock.fundamentals.price_52w_low)}
                </span>
                <span className="text-green-400">
                  Máx: {formatCurrency(selectedStock.fundamentals.price_52w_high)}
                </span>
              </div>
            </div>
          </div>

          {/* Dividend History */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold mb-4">Histórico de Dividendos</h3>
            <div className="space-y-3">
              {selectedStock.dividend_history.slice(0, 8).map((div, idx) => (
                <div key={idx} className="flex justify-between items-center py-2 border-b border-virtus-border-primary last:border-0">
                  <span className="text-sm text-virtus-text-muted">
                    {formatDate(div.date)}
                  </span>
                  <span className="font-medium text-green-400">
                    {formatCurrency(div.value)}
                  </span>
                </div>
              ))}
            </div>
            
            <button
              onClick={() => loadSocialContent('stock', selectedStock.ticker)}
              className="btn-secondary w-full mt-4"
            >
              <Instagram className="w-4 h-4 mr-2" />
              Gerar Post Social
            </button>
          </div>
        </div>
      )}
    </div>
  );

  // Calculadora de Investimento Component
  const InvestmentCalculator = () => {
    // Usa dados do calendário (ex_date events) que tem dados reais
    const availableStocks = exDateEvents.map(e => ({
      ticker: e.ticker,
      company_name: e.company_name,
      dividend_value: e.dividend_value,
      dividend_yield: e.dividend_yield,
      sector: e.sector,
      ex_date: e.date,
      payment_date: calendarEvents.find(
        ev => ev.ticker === e.ticker && ev.event_type === 'payment_date'
      )?.date || null,
      // Estima preço baseado no DY: preço = dividendo / (DY/100)
      estimated_price: e.dividend_yield > 0 ? (e.dividend_value / (e.dividend_yield / 100)) : 0,
      annual_yield: e.dividend_yield * 4 // Estimativa: 4 pagamentos por ano
    }));
    
    // Remove duplicados
    const uniqueStocks = availableStocks.filter((stock, index, self) =>
      index === self.findIndex(s => s.ticker === stock.ticker)
    );
    
    const selectedDividend = selectedCalcTicker 
      ? uniqueStocks.find(d => d.ticker === selectedCalcTicker)
      : null;
    
    const calculateInvestment = () => {
      if (!selectedDividend || investmentAmount <= 0 || selectedDividend.estimated_price <= 0) return null;
      
      const shares = Math.floor(investmentAmount / selectedDividend.estimated_price);
      const actualInvestment = shares * selectedDividend.estimated_price;
      const dividendReceived = shares * selectedDividend.dividend_value;
      const annualDividend = dividendReceived * 4; // Estimativa: 4 pagamentos por ano
      const change = investmentAmount - actualInvestment;
      
      return {
        shares,
        actualInvestment,
        dividendReceived,
        annualDividend,
        change,
        yieldOnInvestment: actualInvestment > 0 ? (dividendReceived / actualInvestment) * 100 : 0
      };
    };
    
    const calc = calculateInvestment();
    
    return (
      <div className="card p-6 bg-gradient-to-br from-virtus-bg-card to-virtus-accent-primary/5 border-virtus-accent-primary/30">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-green-500/20 rounded-lg">
            <DollarSign className="w-6 h-6 text-green-400" />
          </div>
          <div>
            <h3 className="text-lg font-bold">Calculadora de Investimento</h3>
            <p className="text-xs text-virtus-text-muted">Simule quanto você receberá de dividendos</p>
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          {/* Seleção de Ação */}
          <div>
            <label className="text-sm text-virtus-text-muted mb-1 block">Escolha a Ação</label>
            <select
              value={selectedCalcTicker}
              onChange={(e) => setSelectedCalcTicker(e.target.value)}
              className="input w-full"
            >
              <option value="">Selecione uma ação...</option>
              {uniqueStocks.map((d) => (
                <option key={d.ticker} value={d.ticker}>
                  {d.ticker} - {d.company_name} (DY: {formatPercent(d.dividend_yield)})
                </option>
              ))}
            </select>
          </div>
          
          {/* Valor do Investimento */}
          <div>
            <label className="text-sm text-virtus-text-muted mb-1 block">Valor a Investir (R$)</label>
            <input
              type="number"
              value={investmentAmount}
              onChange={(e) => setInvestmentAmount(Number(e.target.value))}
              className="input w-full text-lg font-bold"
              min={0}
              step={100}
              placeholder="1000"
            />
          </div>
        </div>
        
        {/* Informações da Ação Selecionada */}
        {selectedDividend && (
          <div className="bg-virtus-bg-hover rounded-lg p-4 mb-4">
            <div className="flex items-center justify-between mb-3">
              <div>
                <span className="text-xl font-bold text-virtus-accent-primary">{selectedDividend.ticker}</span>
                <p className="text-sm text-virtus-text-secondary">{selectedDividend.company_name}</p>
                {selectedDividend.sector && (
                  <p className="text-xs text-virtus-text-muted">{selectedDividend.sector}</p>
                )}
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold">{formatCurrency(selectedDividend.estimated_price)}</p>
                <p className="text-xs text-virtus-text-muted">Preço Estimado*</p>
              </div>
            </div>
            
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="bg-virtus-bg-card rounded p-2">
                <p className="text-lg font-bold text-green-400">{formatCurrency(selectedDividend.dividend_value)}</p>
                <p className="text-xs text-virtus-text-muted">Dividendo/Ação</p>
              </div>
              <div className="bg-virtus-bg-card rounded p-2">
                <p className="text-lg font-bold text-yellow-400">{formatPercent(selectedDividend.dividend_yield)}</p>
                <p className="text-xs text-virtus-text-muted">DY Próximo</p>
              </div>
              <div className="bg-virtus-bg-card rounded p-2">
                <p className="text-lg font-bold text-purple-400">{formatPercent(selectedDividend.annual_yield)}</p>
                <p className="text-xs text-virtus-text-muted">DY Anual (est.)</p>
              </div>
            </div>
            
            <p className="text-xs text-virtus-text-muted mt-2 text-center">
              * Preço estimado baseado no dividend yield informado
            </p>
          </div>
        )}
        
        {/* Resultado do Cálculo */}
        {calc && selectedDividend && (
          <div className="space-y-3">
            <div className="h-px bg-virtus-border-primary" />
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="bg-virtus-bg-hover rounded-lg p-3 text-center">
                <p className="text-2xl font-bold text-virtus-accent-primary">{calc.shares}</p>
                <p className="text-xs text-virtus-text-muted">Ações que pode comprar</p>
              </div>
              <div className="bg-virtus-bg-hover rounded-lg p-3 text-center">
                <p className="text-2xl font-bold">{formatCurrency(calc.actualInvestment)}</p>
                <p className="text-xs text-virtus-text-muted">Investimento Real</p>
                {calc.change !== 0 && (
                  <p className="text-xs text-yellow-400">Sobra: {formatCurrency(Math.abs(calc.change))}</p>
                )}
              </div>
              <div className="bg-green-500/10 rounded-lg p-3 text-center border border-green-500/30">
                <p className="text-2xl font-bold text-green-400">{formatCurrency(calc.dividendReceived)}</p>
                <p className="text-xs text-virtus-text-muted">Dividendo Próximo</p>
                <p className="text-xs text-green-400">Em {formatDate(selectedDividend.payment_date || selectedDividend.ex_date)}</p>
              </div>
              <div className="bg-purple-500/10 rounded-lg p-3 text-center border border-purple-500/30">
                <p className="text-2xl font-bold text-purple-400">{formatCurrency(calc.annualDividend)}</p>
                <p className="text-xs text-virtus-text-muted">Estimativa Anual</p>
                <p className="text-xs text-purple-400">~{formatCurrency(calc.annualDividend / 12)}/mês</p>
              </div>
            </div>
            
            {/* Resumo */}
            <div className="bg-gradient-to-r from-green-500/10 to-purple-500/10 rounded-lg p-4 border border-green-500/20">
              <p className="text-sm text-virtus-text-secondary">
                💡 Investindo <strong className="text-white">{formatCurrency(investmentAmount)}</strong> em <strong className="text-virtus-accent-primary">{selectedDividend.ticker}</strong>:
              </p>
              <ul className="text-sm text-virtus-text-secondary mt-2 space-y-1">
                <li>→ Você compra <strong className="text-white">{calc.shares} ações</strong> a ~{formatCurrency(selectedDividend.estimated_price)} cada</li>
                <li>→ Receberá <strong className="text-green-400">{formatCurrency(calc.dividendReceived)}</strong> no próximo pagamento</li>
                <li>→ Estimativa de <strong className="text-purple-400">{formatCurrency(calc.annualDividend)}</strong> por ano em dividendos</li>
                <li>→ Rendimento de <strong className="text-yellow-400">{calc.yieldOnInvestment.toFixed(2)}%</strong> sobre o investimento (próximo dividendo)</li>
              </ul>
            </div>
          </div>
        )}
        
        {!selectedCalcTicker && (
          <div className="text-center py-6 text-virtus-text-muted">
            <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>Selecione uma ação acima para simular o investimento</p>
          </div>
        )}
      </div>
    );
  };

  const SocialView = () => (
    <div className="space-y-6">
      <div className="flex gap-4">
        <button
          onClick={() => loadSocialContent('daily')}
          className="btn-primary flex-1"
        >
          <TrendingUp className="w-4 h-4 mr-2" />
          Oportunidades Diárias
        </button>
        <button
          onClick={() => loadSocialContent('weekly')}
          className="btn-secondary flex-1"
        >
          <Calendar className="w-4 h-4 mr-2" />
          Resumo Semanal
        </button>
      </div>

      {socialContent && (
        <div className="card p-6">
          <div className="flex items-start justify-between mb-4">
            <h3 className="text-xl font-bold">{socialContent.title}</h3>
            <button
              onClick={() => copyToClipboard(socialContent.content + '\n\n' + socialContent.hashtags)}
              className="btn-secondary px-3"
            >
              {copiedContent ? (
                <Check className="w-4 h-4 text-green-400" />
              ) : (
                <Copy className="w-4 h-4" />
              )}
            </button>
          </div>
          
          <div className="bg-virtus-bg-hover rounded-lg p-4 mb-4">
            <pre className="whitespace-pre-wrap text-sm text-virtus-text-secondary font-sans">
              {socialContent.content}
            </pre>
          </div>
          
          <div className="flex flex-wrap gap-2">
            {socialContent.hashtags.split(' ').map((tag, idx) => (
              <span key={idx} className="px-2 py-1 bg-virtus-accent-primary/20 text-virtus-accent-primary rounded text-sm">
                {tag}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-3">
            <DollarSign className="w-8 h-8 text-green-400" />
            Dividend Capture Bot
          </h1>
          <p className="text-virtus-text-secondary mt-1">
            Análise e gestão de dividendos B3
          </p>
        </div>
        <button
          onClick={() => { loadUpcomingDividends(); loadCalendar(); loadHealth(); }}
          className="btn-secondary"
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Atualizar
        </button>
      </div>

      {/* Health Banner */}
      <HealthBanner />

      {/* Tabs */}
      <div className="flex gap-2 border-b border-virtus-border-primary pb-4">
        {[
          { id: 'overview', label: 'Visão Geral', icon: PieChart },
          { id: 'calendar', label: 'Calendário', icon: Calendar },
          { id: 'analysis', label: 'Análise', icon: BarChart3 },
          { id: 'social', label: 'Social Media', icon: Instagram },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
              activeTab === tab.id
                ? 'bg-virtus-accent-primary text-white'
                : 'text-virtus-text-secondary hover:bg-virtus-bg-hover'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400">
          {error}
        </div>
      )}

      {/* Content */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              icon={Calendar}
              label="Dividendos Próximos"
              value={upcomingDividends.length.toString()}
              subvalue={`Nos próximos ${daysAhead} dias`}
              color="text-virtus-accent-primary"
            />
            <StatCard
              icon={Target}
              label="Oportunidades"
              value={upcomingDividends.filter(d => d.recommendation === 'buy').length.toString()}
              subvalue="Recomendação: Comprar"
              color="text-green-400"
            />
            <StatCard
              icon={TrendingUp}
              label="Maior DY"
              value={upcomingDividends.length > 0 
                ? formatPercent(Math.max(...upcomingDividends.map(d => d.dividend_yield)))
                : '0%'}
              subvalue="Dividend Yield"
              color="text-yellow-400"
            />
            <StatCard
              icon={Star}
              label="Melhor Score"
              value={upcomingDividends.length > 0 
                ? Math.max(...upcomingDividends.map(d => d.score)).toFixed(0)
                : '0'}
              subvalue="Pontuação máxima"
              color="text-purple-400"
            />
          </div>

          {/* Investment Calculator */}
          <InvestmentCalculator />

          {/* Filters */}
          <div className="flex flex-wrap gap-4 items-center">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-virtus-text-muted" />
              <span className="text-sm text-virtus-text-muted">Filtros:</span>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-sm text-virtus-text-secondary">DY mínimo:</label>
              <input
                type="number"
                value={minYield}
                onChange={(e) => setMinYield(Number(e.target.value))}
                className="input w-20 text-sm"
                min={0}
                max={20}
                step={0.5}
              />
              <span className="text-sm text-virtus-text-muted">%</span>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-sm text-virtus-text-secondary">Dias:</label>
              <select
                value={daysAhead}
                onChange={(e) => setDaysAhead(Number(e.target.value))}
                className="input w-24 text-sm"
              >
                <option value={7}>7 dias</option>
                <option value={14}>14 dias</option>
                <option value={30}>30 dias</option>
                <option value={60}>60 dias</option>
              </select>
            </div>
          </div>

          {/* Dividend Cards Grid */}
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="w-8 h-8 animate-spin text-virtus-accent-primary" />
            </div>
          ) : upcomingDividends.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {upcomingDividends.map((dividend, idx) => (
                <DividendCard key={idx} dividend={dividend} />
              ))}
            </div>
          ) : (
            <div className="card p-12 text-center">
              <DollarSign className="w-12 h-12 text-virtus-text-muted mx-auto mb-4" />
              <p className="text-virtus-text-secondary">
                Nenhum dividendo encontrado com os filtros atuais.
              </p>
              <p className="text-sm text-virtus-text-muted mt-2">
                Tente ajustar o DY mínimo ou o período de busca.
              </p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'calendar' && <CalendarView />}
      {activeTab === 'analysis' && <AnalysisView />}
      {activeTab === 'social' && <SocialView />}
    </div>
  );
};

export default DividendsPage;
