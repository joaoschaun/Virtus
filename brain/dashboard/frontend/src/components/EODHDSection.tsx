/**
 * VIRTUS Dashboard - EODHD Market Data Section
 * 
 * Componente para exibição de dados financeiros do EODHD
 * Inclui: Market Overview, Calendário Econômico, Notícias
 */

import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  Calendar, 
  Newspaper, 
  Globe, 
  DollarSign,
  Activity,
  Clock,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  BarChart3,
  Bitcoin
} from 'lucide-react';

// ============================================================================
// TIPOS
// ============================================================================

interface MarketQuote {
  code?: string;
  close?: number;
  change?: number;
  change_p?: number;
  volume?: number;
  previousClose?: number;
  open?: number;
  high?: number;
  low?: number;
  timestamp?: number;
}

interface MarketOverview {
  timestamp: string;
  forex: Record<string, MarketQuote>;
  indices: Record<string, MarketQuote>;
  crypto: Record<string, MarketQuote>;
  commodities: Record<string, MarketQuote>;
}

interface EconomicEvent {
  date: string;
  event: string;
  country: string;
  actual?: string;
  previous?: string;
  estimate?: string;
  impact?: string;
}

interface NewsArticle {
  title: string;
  date: string;
  content?: string;
  link?: string;
  symbols?: string[];
  sentiment?: { polarity?: number };
}

// ============================================================================
// COMPONENTES AUXILIARES
// ============================================================================

const LoadingSpinner: React.FC = () => (
  <div className="flex items-center justify-center p-8">
    <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
  </div>
);

const ErrorMessage: React.FC<{ message: string }> = ({ message }) => (
  <div className="flex items-center gap-2 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400">
    <AlertCircle className="w-5 h-5" />
    <span>{message}</span>
  </div>
);

const PriceChange: React.FC<{ change?: number; changePercent?: number }> = ({ change, changePercent }) => {
  const isPositive = (change ?? 0) >= 0;
  const Icon = isPositive ? TrendingUp : TrendingDown;
  const colorClass = isPositive ? 'text-green-400' : 'text-red-400';
  
  return (
    <div className={`flex items-center gap-1 ${colorClass}`}>
      <Icon className="w-4 h-4" />
      <span>{changePercent?.toFixed(2)}%</span>
    </div>
  );
};

// ============================================================================
// MARKET OVERVIEW CARD
// ============================================================================

interface QuoteCardProps {
  name: string;
  data: MarketQuote;
  icon?: React.ReactNode;
}

const QuoteCard: React.FC<QuoteCardProps> = ({ name, data, icon }) => {
  const price = data.close || data.previousClose || 0;
  const changePercent = data.change_p || 0;
  const isPositive = changePercent >= 0;
  
  return (
    <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700/50 hover:border-slate-600/50 transition-all">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {icon}
          <span className="text-slate-300 font-medium">{name}</span>
        </div>
        <PriceChange changePercent={changePercent} />
      </div>
      <div className="text-2xl font-bold text-white">
        {price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 5 })}
      </div>
      <div className="flex items-center gap-2 mt-2 text-xs text-slate-500">
        <span>Vol: {(data.volume || 0).toLocaleString()}</span>
      </div>
    </div>
  );
};

// ============================================================================
// MARKET OVERVIEW SECTION
// ============================================================================

interface MarketOverviewSectionProps {
  data: MarketOverview | null;
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
}

const MarketOverviewSection: React.FC<MarketOverviewSectionProps> = ({ data, loading, error, onRefresh }) => {
  const [activeTab, setActiveTab] = useState<'forex' | 'indices' | 'crypto'>('forex');
  
  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} />;
  if (!data) return null;
  
  const getMarketData = () => {
    switch (activeTab) {
      case 'forex': return data.forex;
      case 'indices': return data.indices;
      case 'crypto': return data.crypto;
      default: return {};
    }
  };
  
  const marketData = getMarketData();
  
  return (
    <div className="bg-slate-900/50 rounded-xl p-6 border border-slate-700/50">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <BarChart3 className="w-6 h-6 text-blue-400" />
          <h2 className="text-xl font-bold text-white">Market Overview</h2>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex bg-slate-800 rounded-lg p-1">
            {(['forex', 'indices', 'crypto'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === tab 
                    ? 'bg-blue-600 text-white' 
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>
          <button
            onClick={onRefresh}
            className="p-2 rounded-lg bg-slate-800 text-slate-400 hover:text-white transition-colors"
            title="Atualizar"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {Object.entries(marketData).map(([symbol, quote]) => (
          <QuoteCard
            key={symbol}
            name={symbol}
            data={quote}
            icon={
              activeTab === 'crypto' ? <Bitcoin className="w-5 h-5 text-orange-400" /> :
              activeTab === 'forex' ? <DollarSign className="w-5 h-5 text-green-400" /> :
              <Activity className="w-5 h-5 text-blue-400" />
            }
          />
        ))}
      </div>
      
      {Object.keys(marketData).length === 0 && (
        <div className="text-center text-slate-500 py-8">
          Nenhum dado disponível
        </div>
      )}
      
      <div className="mt-4 text-xs text-slate-500 text-right">
        Atualizado: {new Date(data.timestamp).toLocaleString('pt-BR')}
      </div>
    </div>
  );
};

// ============================================================================
// ECONOMIC CALENDAR SECTION
// ============================================================================

interface EconomicCalendarSectionProps {
  events: EconomicEvent[];
  loading: boolean;
  error: string | null;
}

const getImpactColor = (impact?: string) => {
  switch (impact?.toLowerCase()) {
    case 'high': return 'text-red-400 bg-red-400/10';
    case 'medium': return 'text-yellow-400 bg-yellow-400/10';
    case 'low': return 'text-green-400 bg-green-400/10';
    default: return 'text-slate-400 bg-slate-400/10';
  }
};

const EconomicCalendarSection: React.FC<EconomicCalendarSectionProps> = ({ events, loading, error }) => {
  const [expanded, setExpanded] = useState(false);
  
  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} />;
  
  const displayEvents = expanded ? events : events.slice(0, 5);
  
  return (
    <div className="bg-slate-900/50 rounded-xl p-6 border border-slate-700/50">
      <div className="flex items-center gap-3 mb-6">
        <Calendar className="w-6 h-6 text-purple-400" />
        <h2 className="text-xl font-bold text-white">Calendário Econômico</h2>
        <span className="bg-purple-500/20 text-purple-400 text-xs px-2 py-1 rounded-full">
          {events.length} eventos
        </span>
      </div>
      
      <div className="space-y-3">
        {displayEvents.map((event, index) => (
          <div 
            key={index}
            className="bg-slate-800/50 rounded-lg p-4 border border-slate-700/50 hover:border-slate-600/50 transition-all"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-lg">{getCountryFlag(event.country)}</span>
                  <span className="text-white font-medium">{event.event}</span>
                </div>
                <div className="flex items-center gap-4 text-sm text-slate-400">
                  <div className="flex items-center gap-1">
                    <Clock className="w-4 h-4" />
                    {formatEventDate(event.date)}
                  </div>
                  <div className="flex items-center gap-1">
                    <Globe className="w-4 h-4" />
                    {event.country}
                  </div>
                </div>
              </div>
              <div className="flex flex-col items-end gap-2">
                <span className={`px-2 py-1 rounded text-xs ${getImpactColor(event.impact)}`}>
                  {event.impact || 'N/A'}
                </span>
              </div>
            </div>
            
            {(event.actual || event.previous || event.estimate) && (
              <div className="flex gap-6 mt-3 pt-3 border-t border-slate-700/50 text-sm">
                {event.actual && (
                  <div>
                    <span className="text-slate-500">Atual:</span>
                    <span className="text-white ml-1 font-medium">{event.actual}</span>
                  </div>
                )}
                {event.estimate && (
                  <div>
                    <span className="text-slate-500">Previsão:</span>
                    <span className="text-slate-300 ml-1">{event.estimate}</span>
                  </div>
                )}
                {event.previous && (
                  <div>
                    <span className="text-slate-500">Anterior:</span>
                    <span className="text-slate-300 ml-1">{event.previous}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
      
      {events.length > 5 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full mt-4 py-2 flex items-center justify-center gap-2 text-slate-400 hover:text-white transition-colors"
        >
          {expanded ? (
            <>
              <ChevronUp className="w-4 h-4" />
              Mostrar menos
            </>
          ) : (
            <>
              <ChevronDown className="w-4 h-4" />
              Ver todos ({events.length - 5} mais)
            </>
          )}
        </button>
      )}
    </div>
  );
};

// ============================================================================
// NEWS SECTION
// ============================================================================

interface NewsSectionProps {
  news: NewsArticle[];
  loading: boolean;
  error: string | null;
}

const getSentimentColor = (polarity?: number) => {
  if (!polarity) return 'text-slate-400';
  if (polarity > 0.2) return 'text-green-400';
  if (polarity < -0.2) return 'text-red-400';
  return 'text-yellow-400';
};

const NewsSection: React.FC<NewsSectionProps> = ({ news, loading, error }) => {
  const [expanded, setExpanded] = useState(false);
  
  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} />;
  
  const displayNews = expanded ? news : news.slice(0, 5);
  
  return (
    <div className="bg-slate-900/50 rounded-xl p-6 border border-slate-700/50">
      <div className="flex items-center gap-3 mb-6">
        <Newspaper className="w-6 h-6 text-amber-400" />
        <h2 className="text-xl font-bold text-white">Notícias do Mercado</h2>
        <span className="bg-amber-500/20 text-amber-400 text-xs px-2 py-1 rounded-full">
          {news.length} notícias
        </span>
      </div>
      
      <div className="space-y-4">
        {displayNews.map((article, index) => (
          <a
            key={index}
            href={article.link}
            target="_blank"
            rel="noopener noreferrer"
            className="block bg-slate-800/50 rounded-lg p-4 border border-slate-700/50 hover:border-amber-500/50 transition-all"
          >
            <h3 className="text-white font-medium mb-2 line-clamp-2">
              {article.title}
            </h3>
            
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-3 text-slate-400">
                <div className="flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  {formatNewsDate(article.date)}
                </div>
                
                {article.symbols && article.symbols.length > 0 && (
                  <div className="flex gap-1">
                    {article.symbols.slice(0, 3).map((symbol, i) => (
                      <span 
                        key={i}
                        className="bg-slate-700 px-2 py-0.5 rounded text-xs"
                      >
                        {symbol}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              
              {article.sentiment?.polarity !== undefined && (
                <span className={`text-xs ${getSentimentColor(article.sentiment.polarity)}`}>
                  Sentimento: {(article.sentiment.polarity * 100).toFixed(0)}%
                </span>
              )}
            </div>
          </a>
        ))}
      </div>
      
      {news.length > 5 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full mt-4 py-2 flex items-center justify-center gap-2 text-slate-400 hover:text-white transition-colors"
        >
          {expanded ? (
            <>
              <ChevronUp className="w-4 h-4" />
              Mostrar menos
            </>
          ) : (
            <>
              <ChevronDown className="w-4 h-4" />
              Ver mais notícias
            </>
          )}
        </button>
      )}
    </div>
  );
};

// ============================================================================
// HELPERS
// ============================================================================

const getCountryFlag = (country: string): string => {
  const flags: Record<string, string> = {
    'US': '🇺🇸',
    'USA': '🇺🇸',
    'GB': '🇬🇧',
    'GBR': '🇬🇧',
    'EU': '🇪🇺',
    'EUR': '🇪🇺',
    'JP': '🇯🇵',
    'JPN': '🇯🇵',
    'CN': '🇨🇳',
    'CHN': '🇨🇳',
    'AU': '🇦🇺',
    'AUS': '🇦🇺',
    'CA': '🇨🇦',
    'CAN': '🇨🇦',
    'CH': '🇨🇭',
    'CHE': '🇨🇭',
    'BR': '🇧🇷',
    'BRA': '🇧🇷',
    'DE': '🇩🇪',
    'DEU': '🇩🇪',
    'FR': '🇫🇷',
    'FRA': '🇫🇷',
  };
  return flags[country.toUpperCase()] || '🌍';
};

const formatEventDate = (dateString: string): string => {
  try {
    const date = new Date(dateString);
    return date.toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return dateString;
  }
};

const formatNewsDate = (dateString: string): string => {
  try {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const hours = Math.floor(diff / (1000 * 60 * 60));
    
    if (hours < 1) return 'Agora';
    if (hours < 24) return `${hours}h atrás`;
    
    return date.toLocaleDateString('pt-BR');
  } catch {
    return dateString;
  }
};

// ============================================================================
// COMPONENTE PRINCIPAL
// ============================================================================

export interface EODHDSectionProps {
  apiUrl?: string;
}

const EODHDSection: React.FC<EODHDSectionProps> = ({ apiUrl = '/api' }) => {
  // Estados
  const [marketOverview, setMarketOverview] = useState<MarketOverview | null>(null);
  const [economicEvents, setEconomicEvents] = useState<EconomicEvent[]>([]);
  const [news, setNews] = useState<NewsArticle[]>([]);
  
  const [marketLoading, setMarketLoading] = useState(true);
  const [calendarLoading, setCalendarLoading] = useState(true);
  const [newsLoading, setNewsLoading] = useState(true);
  
  const [marketError, setMarketError] = useState<string | null>(null);
  const [calendarError, setCalendarError] = useState<string | null>(null);
  const [newsError, setNewsError] = useState<string | null>(null);
  
  // Fetch Market Overview
  const fetchMarketOverview = async () => {
    setMarketLoading(true);
    setMarketError(null);
    
    try {
      const response = await fetch(`${apiUrl}/eodhd/market/overview`);
      if (!response.ok) throw new Error('Erro ao carregar dados de mercado');
      const data = await response.json();
      setMarketOverview(data);
    } catch (err) {
      setMarketError(err instanceof Error ? err.message : 'Erro desconhecido');
    } finally {
      setMarketLoading(false);
    }
  };
  
  // Fetch Economic Calendar
  const fetchEconomicCalendar = async () => {
    setCalendarLoading(true);
    setCalendarError(null);
    
    try {
      const response = await fetch(`${apiUrl}/eodhd/calendar/events?days=7`);
      if (!response.ok) throw new Error('Erro ao carregar calendário');
      const data = await response.json();
      setEconomicEvents(data.events || []);
    } catch (err) {
      setCalendarError(err instanceof Error ? err.message : 'Erro desconhecido');
    } finally {
      setCalendarLoading(false);
    }
  };
  
  // Fetch News
  const fetchNews = async () => {
    setNewsLoading(true);
    setNewsError(null);
    
    try {
      const response = await fetch(`${apiUrl}/eodhd/news?limit=20`);
      if (!response.ok) throw new Error('Erro ao carregar notícias');
      const data = await response.json();
      setNews(data.news || []);
    } catch (err) {
      setNewsError(err instanceof Error ? err.message : 'Erro desconhecido');
    } finally {
      setNewsLoading(false);
    }
  };
  
  // Load inicial
  useEffect(() => {
    fetchMarketOverview();
    fetchEconomicCalendar();
    fetchNews();
    
    // Auto-refresh a cada 5 minutos
    const interval = setInterval(() => {
      fetchMarketOverview();
    }, 5 * 60 * 1000);
    
    return () => clearInterval(interval);
  }, [apiUrl]);
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-gradient-to-r from-blue-600 to-purple-600">
          <Activity className="w-6 h-6 text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Dados de Mercado</h1>
          <p className="text-slate-400 text-sm">Powered by EODHD Financial APIs</p>
        </div>
      </div>
      
      {/* Market Overview */}
      <MarketOverviewSection
        data={marketOverview}
        loading={marketLoading}
        error={marketError}
        onRefresh={fetchMarketOverview}
      />
      
      {/* Grid: Calendar + News */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <EconomicCalendarSection
          events={economicEvents}
          loading={calendarLoading}
          error={calendarError}
        />
        
        <NewsSection
          news={news}
          loading={newsLoading}
          error={newsError}
        />
      </div>
    </div>
  );
};

export default EODHDSection;
