/**
 * VIRTUS Portal - Homepage
 * ========================
 * 
 * Página principal do portal público com:
 * - Ticker de cotações em tempo real
 * - Índices de mercado
 * - Notícias do dia
 * - Calendário econômico
 * - Ações brasileiras em destaque
 */

import { useState, useEffect, useRef } from 'react';
import { 
  TrendingUp, TrendingDown, Calendar, Newspaper, Clock, 
  RefreshCw, ChevronRight, AlertTriangle, BarChart3,
  DollarSign, Bitcoin, Globe, Zap, ArrowUp, ArrowDown
} from 'lucide-react';

// Types
interface MarketQuote {
  symbol: string;
  name: string;
  price: number;
  change: number;
  change_percent: number;
  volume?: number;
  high?: number;
  low?: number;
}

interface NewsItem {
  id: string;
  title: string;
  summary: string;
  source: string;
  category: string;
  sentiment: string;
  published_at: string;
  image_url?: string;
  url?: string;
}

interface EconomicEvent {
  time: string;
  time_brazil: string;
  country: string;
  event: string;
  impact: string;
  actual?: string;
  forecast?: string;
  previous?: string;
}

interface PortalData {
  success: boolean;
  timestamp: string;
  market: {
    indices: Record<string, MarketQuote>;
    brazil_stocks: MarketQuote[];
  };
  news: {
    latest: NewsItem[];
    forex: NewsItem[];
    brazil: NewsItem[];
  };
  calendar: {
    today: EconomicEvent[];
    high_impact: EconomicEvent[];
  };
  summary: {
    market_status: string;
    sentiment: {
      overall: string;
      bullish: number;
      bearish: number;
      neutral: number;
    };
  };
}

// API Base URL - usar URL relativa para passar pelo proxy Nginx
const API_BASE = '';

// Ticker Component
function MarketTicker({ indices }: { indices: Record<string, MarketQuote> }) {
  const tickerRef = useRef<HTMLDivElement>(null);
  
  const tickerItems = [
    { key: 'ibovespa', icon: '📈', color: 'text-blue-400' },
    { key: 'sp500', icon: '🇺🇸', color: 'text-green-400' },
    { key: 'nasdaq', icon: '💻', color: 'text-purple-400' },
    { key: 'dolar', icon: '💵', color: 'text-emerald-400' },
    { key: 'euro', icon: '💶', color: 'text-yellow-400' },
    { key: 'bitcoin', icon: '₿', color: 'text-orange-400' },
    { key: 'ouro', icon: '🥇', color: 'text-amber-400' },
  ];

  return (
    <div className="bg-gray-900 border-b border-gray-800 overflow-hidden">
      <div 
        ref={tickerRef}
        className="flex animate-marquee whitespace-nowrap py-2"
      >
        {[...tickerItems, ...tickerItems].map((item, idx) => {
          const quote = indices[item.key];
          if (!quote) return null;
          
          const isPositive = quote.change >= 0;
          
          return (
            <div key={`${item.key}-${idx}`} className="flex items-center mx-6">
              <span className="mr-2">{item.icon}</span>
              <span className={`font-medium ${item.color}`}>{quote.name}</span>
              <span className="ml-2 text-white font-bold">
                {quote.price.toLocaleString('pt-BR', { 
                  minimumFractionDigits: 2, 
                  maximumFractionDigits: 2 
                })}
              </span>
              <span className={`ml-2 flex items-center ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                {isPositive ? <ArrowUp size={14} /> : <ArrowDown size={14} />}
                {Math.abs(quote.change_percent).toFixed(2)}%
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Index Card Component
function IndexCard({ quote, icon }: { quote: MarketQuote; icon: React.ReactNode }) {
  const isPositive = quote.change >= 0;
  
  return (
    <div className="bg-gray-800/50 backdrop-blur rounded-xl p-4 border border-gray-700 hover:border-blue-500/50 transition-all">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {icon}
          <span className="text-gray-400 text-sm">{quote.name}</span>
        </div>
        <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
          isPositive ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
        }`}>
          {isPositive ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
          {Math.abs(quote.change_percent).toFixed(2)}%
        </div>
      </div>
      <div className="text-2xl font-bold text-white">
        {quote.price.toLocaleString('pt-BR', { 
          minimumFractionDigits: 2, 
          maximumFractionDigits: 2 
        })}
      </div>
      <div className={`text-sm ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
        {isPositive ? '+' : ''}{quote.change.toFixed(2)}
      </div>
    </div>
  );
}

// News Card Component
function NewsCard({ news }: { news: NewsItem }) {
  const sentimentColor = {
    bullish: 'border-l-green-500',
    bearish: 'border-l-red-500',
    neutral: 'border-l-gray-500'
  }[news.sentiment] || 'border-l-gray-500';

  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  return (
    <a 
      href={news.url || '#'} 
      target="_blank" 
      rel="noopener noreferrer"
      className={`block bg-gray-800/50 backdrop-blur rounded-lg p-4 border-l-4 ${sentimentColor} hover:bg-gray-700/50 transition-all`}
    >
      <div className="flex items-start gap-3">
        {news.image_url && (
          <img 
            src={news.image_url} 
            alt="" 
            className="w-20 h-20 object-cover rounded-lg flex-shrink-0"
            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
          />
        )}
        <div className="flex-1 min-w-0">
          <h3 className="text-white font-medium line-clamp-2 mb-1">{news.title}</h3>
          <p className="text-gray-400 text-sm line-clamp-2">{news.summary}</p>
          <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
            <span>{news.source}</span>
            <span>•</span>
            <span>{formatDate(news.published_at)}</span>
          </div>
        </div>
      </div>
    </a>
  );
}

// Economic Event Row Component
function EventRow({ event }: { event: EconomicEvent }) {
  const impactColor = {
    high: 'bg-red-500/20 text-red-400 border-red-500/50',
    medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50',
    low: 'bg-gray-500/20 text-gray-400 border-gray-500/50'
  }[event.impact] || 'bg-gray-500/20 text-gray-400 border-gray-500/50';

  const countryFlags: Record<string, string> = {
    'US': '🇺🇸',
    'BR': '🇧🇷',
    'EU': '🇪🇺',
    'GB': '🇬🇧',
    'JP': '🇯🇵',
    'CN': '🇨🇳',
    'DE': '🇩🇪',
    'FR': '🇫🇷',
  };

  return (
    <div className="flex items-center gap-3 py-2 border-b border-gray-700/50 last:border-0">
      <div className="w-12 text-center">
        <span className="text-blue-400 font-mono text-sm">{event.time_brazil}</span>
      </div>
      <div className="w-8 text-center text-lg">
        {countryFlags[event.country] || '🌍'}
      </div>
      <div className="flex-1 min-w-0">
        <span className="text-white text-sm truncate">{event.event}</span>
      </div>
      <div className={`px-2 py-0.5 rounded text-xs font-medium border ${impactColor}`}>
        {event.impact === 'high' ? 'ALTO' : event.impact === 'medium' ? 'MÉDIO' : 'BAIXO'}
      </div>
    </div>
  );
}

// Stock Row Component
function StockRow({ stock }: { stock: MarketQuote }) {
  const isPositive = stock.change >= 0;
  
  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-700/50 last:border-0 hover:bg-gray-700/30 px-2 rounded transition-all">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center text-white font-bold text-xs">
          {stock.symbol.slice(0, 4)}
        </div>
        <div>
          <div className="text-white font-medium">{stock.symbol}</div>
          <div className="text-gray-500 text-xs truncate max-w-[120px]">{stock.name}</div>
        </div>
      </div>
      <div className="text-right">
        <div className="text-white font-medium">
          R$ {stock.price.toFixed(2)}
        </div>
        <div className={`text-sm ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
          {isPositive ? '+' : ''}{stock.change_percent.toFixed(2)}%
        </div>
      </div>
    </div>
  );
}

// Main Portal Home Component
export default function PortalHome() {
  const [data, setData] = useState<PortalData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/api/portal/home`);
      
      if (!response.ok) {
        throw new Error('Erro ao carregar dados');
      }
      
      const result = await response.json();
      setData(result);
      setLastUpdate(new Date());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro desconhecido');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    
    // Atualiza a cada 5 minutos
    const interval = setInterval(fetchData, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !data) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-400">Carregando dados do mercado...</p>
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <p className="text-red-400">{error}</p>
          <button 
            onClick={fetchData}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Tentar novamente
          </button>
        </div>
      </div>
    );
  }

  const indices = data?.market?.indices || {};
  const stocks = data?.market?.brazil_stocks || [];
  const news = data?.news?.latest || [];
  const highImpactEvents = data?.calendar?.high_impact || [];
  const allEvents = data?.calendar?.today || [];

  return (
    <div className="min-h-screen bg-gray-900">
      {/* Ticker */}
      {Object.keys(indices).length > 0 && <MarketTicker indices={indices} />}
      
      {/* Header */}
      <header className="bg-gray-900/95 backdrop-blur border-b border-gray-800 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl flex items-center justify-center">
                <BarChart3 className="text-white" size={24} />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">VIRTUS</h1>
                <p className="text-xs text-gray-400">Investimentos</p>
              </div>
            </div>
            
            <nav className="hidden md:flex items-center gap-6">
              <a href="#mercado" className="text-gray-300 hover:text-white transition-colors">Mercado</a>
              <a href="#noticias" className="text-gray-300 hover:text-white transition-colors">Notícias</a>
              <a href="#calendario" className="text-gray-300 hover:text-white transition-colors">Calendário</a>
              <a href="#acoes" className="text-gray-300 hover:text-white transition-colors">Ações</a>
            </nav>
            
            <div className="flex items-center gap-3">
              {lastUpdate && (
                <span className="text-xs text-gray-500 hidden sm:block">
                  Atualizado: {lastUpdate.toLocaleTimeString('pt-BR')}
                </span>
              )}
              <button 
                onClick={fetchData}
                disabled={loading}
                className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white transition-all"
              >
                <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
              </button>
              <a 
                href="https://dashboard.virtusinvestimentos.com.br"
                className="px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg font-medium hover:opacity-90 transition-opacity"
              >
                Dashboard
              </a>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section with Market Status */}
      <section className="bg-gradient-to-b from-gray-800/50 to-gray-900 py-8">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-6">
            <div>
              <h2 className="text-2xl font-bold text-white mb-1">
                Bom dia! {new Date().toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' })}
              </h2>
              <p className="text-gray-400">
                {data?.summary?.market_status || 'Acompanhe o mercado em tempo real'}
              </p>
            </div>
            
            {/* High Impact Alert */}
            {highImpactEvents.length > 0 && (
              <div className="flex items-center gap-2 px-4 py-2 bg-red-500/20 border border-red-500/50 rounded-lg">
                <Zap className="text-red-400" size={18} />
                <span className="text-red-400 font-medium">
                  {highImpactEvents.length} evento(s) de alto impacto hoje
                </span>
              </div>
            )}
          </div>

          {/* Market Indices Grid */}
          <div id="mercado" className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
            {indices.ibovespa && <IndexCard quote={indices.ibovespa} icon={<TrendingUp className="text-blue-400" size={18} />} />}
            {indices.sp500 && <IndexCard quote={indices.sp500} icon={<Globe className="text-green-400" size={18} />} />}
            {indices.nasdaq && <IndexCard quote={indices.nasdaq} icon={<BarChart3 className="text-purple-400" size={18} />} />}
            {indices.dow_jones && <IndexCard quote={indices.dow_jones} icon={<TrendingUp className="text-cyan-400" size={18} />} />}
            {indices.dolar && <IndexCard quote={indices.dolar} icon={<DollarSign className="text-emerald-400" size={18} />} />}
            {indices.euro && <IndexCard quote={indices.euro} icon={<DollarSign className="text-yellow-400" size={18} />} />}
            {indices.bitcoin && <IndexCard quote={indices.bitcoin} icon={<Bitcoin className="text-orange-400" size={18} />} />}
          </div>
        </div>
      </section>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* News Column - 2/3 width */}
          <div id="noticias" className="lg:col-span-2 space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <Newspaper className="text-blue-400" size={24} />
                Últimas Notícias
              </h2>
              <a href="#" className="text-blue-400 hover:text-blue-300 flex items-center gap-1 text-sm">
                Ver todas <ChevronRight size={16} />
              </a>
            </div>
            
            <div className="space-y-4">
              {news.slice(0, 8).map((item) => (
                <NewsCard key={item.id} news={item} />
              ))}
              
              {news.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  Nenhuma notícia disponível no momento
                </div>
              )}
            </div>
          </div>

          {/* Sidebar - 1/3 width */}
          <div className="space-y-6">
            
            {/* Economic Calendar */}
            <div id="calendario" className="bg-gray-800/50 backdrop-blur rounded-xl p-4 border border-gray-700">
              <h3 className="text-lg font-bold text-white flex items-center gap-2 mb-4">
                <Calendar className="text-blue-400" size={20} />
                Calendário Econômico
              </h3>
              
              {highImpactEvents.length > 0 && (
                <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                  <h4 className="text-red-400 font-medium text-sm mb-2 flex items-center gap-1">
                    <AlertTriangle size={14} />
                    Alto Impacto
                  </h4>
                  <div className="space-y-1">
                    {highImpactEvents.slice(0, 5).map((event, idx) => (
                      <EventRow key={idx} event={event} />
                    ))}
                  </div>
                </div>
              )}
              
              <div className="space-y-1 max-h-64 overflow-y-auto">
                {allEvents.filter(e => e.impact !== 'high').slice(0, 10).map((event, idx) => (
                  <EventRow key={idx} event={event} />
                ))}
              </div>
              
              {allEvents.length === 0 && (
                <p className="text-gray-500 text-center py-4">
                  Nenhum evento hoje
                </p>
              )}
            </div>

            {/* Brazil Stocks */}
            <div id="acoes" className="bg-gray-800/50 backdrop-blur rounded-xl p-4 border border-gray-700">
              <h3 className="text-lg font-bold text-white flex items-center gap-2 mb-4">
                <BarChart3 className="text-green-400" size={20} />
                Ações em Destaque
              </h3>
              
              <div className="space-y-1">
                {stocks.slice(0, 8).map((stock) => (
                  <StockRow key={stock.symbol} stock={stock} />
                ))}
              </div>
              
              {stocks.length === 0 && (
                <p className="text-gray-500 text-center py-4">
                  Cotações indisponíveis
                </p>
              )}
            </div>
            
            {/* Market Sentiment */}
            {data?.summary?.sentiment && (
              <div className="bg-gray-800/50 backdrop-blur rounded-xl p-4 border border-gray-700">
                <h3 className="text-lg font-bold text-white mb-4">Sentimento do Mercado</h3>
                
                <div className="flex items-center justify-between mb-3">
                  <span className="text-gray-400">Notícias</span>
                  <span className={`font-medium ${
                    data.summary.sentiment.overall === 'bullish' ? 'text-green-400' :
                    data.summary.sentiment.overall === 'bearish' ? 'text-red-400' : 'text-gray-400'
                  }`}>
                    {data.summary.sentiment.overall === 'bullish' ? 'Otimista' :
                     data.summary.sentiment.overall === 'bearish' ? 'Pessimista' : 'Neutro'}
                  </span>
                </div>
                
                <div className="flex gap-2">
                  <div className="flex-1 bg-green-500/20 rounded-full h-2">
                    <div 
                      className="bg-green-500 h-2 rounded-full" 
                      style={{ 
                        width: `${(data.summary.sentiment.bullish / 
                          (data.summary.sentiment.bullish + data.summary.sentiment.bearish + data.summary.sentiment.neutral)) * 100}%` 
                      }}
                    />
                  </div>
                  <div className="flex-1 bg-red-500/20 rounded-full h-2">
                    <div 
                      className="bg-red-500 h-2 rounded-full" 
                      style={{ 
                        width: `${(data.summary.sentiment.bearish / 
                          (data.summary.sentiment.bullish + data.summary.sentiment.bearish + data.summary.sentiment.neutral)) * 100}%` 
                      }}
                    />
                  </div>
                </div>
                
                <div className="flex justify-between mt-2 text-xs text-gray-500">
                  <span>{data.summary.sentiment.bullish} positivas</span>
                  <span>{data.summary.sentiment.neutral} neutras</span>
                  <span>{data.summary.sentiment.bearish} negativas</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-gray-800/50 border-t border-gray-700 py-8 mt-12">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
                <BarChart3 className="text-white" size={18} />
              </div>
              <span className="text-gray-400">VIRTUS Investimentos © 2025</span>
            </div>
            
            <div className="flex items-center gap-6 text-sm text-gray-500">
              <span>Dados: ForexNews, EODHD, Brapi</span>
              <span>•</span>
              <span>Atualização: 5 min</span>
            </div>
          </div>
        </div>
      </footer>
      
      {/* CSS for Marquee Animation */}
      <style>{`
        @keyframes marquee {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
        .animate-marquee {
          animation: marquee 30s linear infinite;
        }
        .animate-marquee:hover {
          animation-play-state: paused;
        }
        .line-clamp-2 {
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
      `}</style>
    </div>
  );
}
