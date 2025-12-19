import React, { useState, useEffect, useRef } from 'react';
import {
  X,
  Volume2,
  VolumeX,
  Play,
  Pause,
  TrendingUp,
  TrendingDown,
  Calendar,
  Newspaper,
  DollarSign,
  AlertTriangle,
  Clock,
  Globe,
  BarChart3,
  Activity,
  Loader2,
  RefreshCw,
  ChevronRight
} from 'lucide-react';

const API_BASE = '';

interface MarketData {
  value: number;
  change: number;
  change_percent: number;
  direction: string;
}

interface NewsItem {
  title: string;
  summary: string;
  source: string;
  category: string;
  sentiment: string;
  impact: string;
  url?: string;
  published_at?: string;
}

interface EconomicEvent {
  time: string;
  country: string;
  event: string;
  impact: string;
  actual?: string;
  forecast?: string;
  previous?: string;
}

interface DividendAlert {
  ticker: string;
  company_name: string;
  buy_limit_date: string;
  ex_date: string;
  payment_date?: string;
  dividend_value: number;
  dividend_yield: number;
  days_remaining: number;
  urgency: string;
}

interface BriefingData {
  date: string;
  weekday: string;
  greeting: string;
  market_overview: {
    ibovespa: MarketData;
    dolar: MarketData;
    sp500: MarketData;
    sentiment: string;
    sentiment_description: string;
  };
  top_news: NewsItem[];
  economic_calendar: EconomicEvent[];
  dividend_alerts: DividendAlert[];
  summary_text: string;
  audio_text: string;
  generated_at: string;
}

interface DailyBriefingModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const DailyBriefingModal: React.FC<DailyBriefingModalProps> = ({ isOpen, onClose }) => {
  const [briefing, setBriefing] = useState<BriefingData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const speechRef = useRef<SpeechSynthesisUtterance | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'news' | 'calendar' | 'dividends'>('overview');

  useEffect(() => {
    if (isOpen) {
      loadBriefing();
    }
    return () => {
      stopSpeech();
    };
  }, [isOpen]);

  const loadBriefing = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/api/briefing/daily`);
      if (!response.ok) throw new Error('Erro ao carregar briefing');
      const data = await response.json();
      setBriefing(data);
    } catch (err) {
      setError('Não foi possível carregar o briefing. Tente novamente.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const speakText = (text: string) => {
    if ('speechSynthesis' in window) {
      stopSpeech();
      
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'pt-BR';
      utterance.rate = 0.95;
      utterance.pitch = 1;
      utterance.volume = isMuted ? 0 : 1;
      
      // Tenta encontrar voz em português
      const voices = speechSynthesis.getVoices();
      const ptVoice = voices.find(v => v.lang.includes('pt-BR')) || 
                      voices.find(v => v.lang.includes('pt')) ||
                      voices[0];
      if (ptVoice) {
        utterance.voice = ptVoice;
      }
      
      utterance.onend = () => setIsPlaying(false);
      utterance.onerror = () => setIsPlaying(false);
      
      speechRef.current = utterance;
      speechSynthesis.speak(utterance);
      setIsPlaying(true);
    }
  };

  const stopSpeech = () => {
    if ('speechSynthesis' in window) {
      speechSynthesis.cancel();
      setIsPlaying(false);
    }
  };

  const togglePlayPause = () => {
    if (isPlaying) {
      stopSpeech();
    } else if (briefing?.audio_text) {
      speakText(briefing.audio_text);
    }
  };

  const toggleMute = () => {
    setIsMuted(!isMuted);
    if (speechRef.current) {
      speechRef.current.volume = isMuted ? 1 : 0;
    }
  };

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'very_bullish': return 'text-green-400 bg-green-500/20';
      case 'bullish': return 'text-green-400 bg-green-500/10';
      case 'bearish': return 'text-red-400 bg-red-500/10';
      case 'very_bearish': return 'text-red-400 bg-red-500/20';
      default: return 'text-yellow-400 bg-yellow-500/10';
    }
  };

  const getSentimentIcon = (sentiment: string) => {
    if (sentiment.includes('bullish')) return <TrendingUp className="w-5 h-5" />;
    if (sentiment.includes('bearish')) return <TrendingDown className="w-5 h-5" />;
    return <Activity className="w-5 h-5" />;
  };

  const getImpactColor = (impact: string) => {
    switch (impact) {
      case 'high': return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'medium': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      default: return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    }
  };

  const getUrgencyStyle = (urgency: string) => {
    switch (urgency) {
      case 'today': return 'bg-red-500 text-white animate-pulse';
      case 'urgent': return 'bg-orange-500 text-white';
      default: return 'bg-yellow-500/20 text-yellow-400';
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(value);
  };

  const formatNumber = (value: number, decimals = 0) => {
    return new Intl.NumberFormat('pt-BR', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    }).format(value);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative bg-virtus-bg-card border border-virtus-border-primary rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="bg-gradient-to-r from-virtus-accent-primary/20 via-virtus-bg-card to-green-500/20 border-b border-virtus-border-primary p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-virtus-accent-primary/20 rounded-xl">
                <BarChart3 className="w-8 h-8 text-virtus-accent-primary" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-white">Briefing Diário</h2>
                {briefing && (
                  <p className="text-virtus-text-secondary">
                    {briefing.weekday}, {briefing.date}
                  </p>
                )}
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              {/* Controles de Áudio */}
              {briefing && (
                <div className="flex items-center gap-2 bg-virtus-bg-hover rounded-lg p-2">
                  <button
                    onClick={togglePlayPause}
                    className="p-2 rounded-lg hover:bg-virtus-bg-card transition-colors"
                    title={isPlaying ? 'Pausar' : 'Ouvir Briefing'}
                  >
                    {isPlaying ? (
                      <Pause className="w-5 h-5 text-virtus-accent-primary" />
                    ) : (
                      <Play className="w-5 h-5 text-virtus-accent-primary" />
                    )}
                  </button>
                  <button
                    onClick={toggleMute}
                    className="p-2 rounded-lg hover:bg-virtus-bg-card transition-colors"
                    title={isMuted ? 'Ativar som' : 'Mutar'}
                  >
                    {isMuted ? (
                      <VolumeX className="w-5 h-5 text-virtus-text-muted" />
                    ) : (
                      <Volume2 className="w-5 h-5 text-green-400" />
                    )}
                  </button>
                </div>
              )}
              
              <button
                onClick={loadBriefing}
                className="p-2 rounded-lg hover:bg-virtus-bg-hover transition-colors"
                title="Atualizar"
              >
                <RefreshCw className={`w-5 h-5 text-virtus-text-muted ${loading ? 'animate-spin' : ''}`} />
              </button>
              
              <button
                onClick={onClose}
                className="p-2 rounded-lg hover:bg-virtus-bg-hover transition-colors"
              >
                <X className="w-6 h-6 text-virtus-text-muted" />
              </button>
            </div>
          </div>
          
          {/* Tabs */}
          <div className="flex gap-2 mt-4">
            {[
              { id: 'overview', label: 'Visão Geral', icon: Activity },
              { id: 'news', label: 'Notícias', icon: Newspaper },
              { id: 'calendar', label: 'Calendário', icon: Calendar },
              { id: 'dividends', label: 'Dividendos', icon: DollarSign },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  activeTab === tab.id
                    ? 'bg-virtus-accent-primary text-white shadow-lg shadow-virtus-accent-primary/20'
                    : 'text-virtus-text-secondary hover:bg-virtus-bg-hover'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </div>
        </div>
        
        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20">
              <Loader2 className="w-12 h-12 text-virtus-accent-primary animate-spin mb-4" />
              <p className="text-virtus-text-secondary">Carregando briefing...</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center py-20">
              <AlertTriangle className="w-12 h-12 text-red-400 mb-4" />
              <p className="text-red-400 mb-4">{error}</p>
              <button
                onClick={loadBriefing}
                className="btn-primary"
              >
                Tentar novamente
              </button>
            </div>
          ) : briefing && (
            <>
              {/* Overview Tab */}
              {activeTab === 'overview' && (
                <div className="space-y-6">
                  {/* Saudação */}
                  <div className="text-center mb-8">
                    <h3 className="text-3xl font-bold text-white mb-2">
                      {briefing.greeting}! 👋
                    </h3>
                    <p className="text-virtus-text-secondary">
                      Aqui está o resumo do mercado para você
                    </p>
                  </div>
                  
                  {/* Sentimento do Mercado */}
                  <div className={`p-4 rounded-xl border ${getSentimentColor(briefing.market_overview.sentiment)}`}>
                    <div className="flex items-center gap-3">
                      {getSentimentIcon(briefing.market_overview.sentiment)}
                      <div>
                        <p className="font-bold text-lg">Sentimento do Mercado</p>
                        <p className="text-sm opacity-80">{briefing.market_overview.sentiment_description}</p>
                      </div>
                    </div>
                  </div>
                  
                  {/* Índices */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* IBOVESPA */}
                    <div className="bg-virtus-bg-hover rounded-xl p-4 border border-virtus-border-primary">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-virtus-text-muted">IBOVESPA</span>
                        <span className={`text-xs px-2 py-1 rounded ${
                          briefing.market_overview.ibovespa.direction === 'up' 
                            ? 'bg-green-500/20 text-green-400' 
                            : 'bg-red-500/20 text-red-400'
                        }`}>
                          {briefing.market_overview.ibovespa.direction === 'up' ? '↑' : '↓'}
                          {Math.abs(briefing.market_overview.ibovespa.change_percent).toFixed(2)}%
                        </span>
                      </div>
                      <p className="text-2xl font-bold">
                        {formatNumber(briefing.market_overview.ibovespa.value)}
                      </p>
                      <p className="text-xs text-virtus-text-muted">pontos</p>
                    </div>
                    
                    {/* Dólar */}
                    <div className="bg-virtus-bg-hover rounded-xl p-4 border border-virtus-border-primary">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-virtus-text-muted">DÓLAR</span>
                        <span className={`text-xs px-2 py-1 rounded ${
                          briefing.market_overview.dolar.direction === 'up' 
                            ? 'bg-red-500/20 text-red-400' 
                            : 'bg-green-500/20 text-green-400'
                        }`}>
                          {briefing.market_overview.dolar.direction === 'up' ? '↑' : '↓'}
                          {Math.abs(briefing.market_overview.dolar.change_percent).toFixed(2)}%
                        </span>
                      </div>
                      <p className="text-2xl font-bold">
                        R$ {briefing.market_overview.dolar.value.toFixed(2)}
                      </p>
                      <p className="text-xs text-virtus-text-muted">cotação</p>
                    </div>
                    
                    {/* S&P 500 */}
                    <div className="bg-virtus-bg-hover rounded-xl p-4 border border-virtus-border-primary">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-virtus-text-muted">S&P 500</span>
                        <span className={`text-xs px-2 py-1 rounded ${
                          briefing.market_overview.sp500.direction === 'up' 
                            ? 'bg-green-500/20 text-green-400' 
                            : 'bg-red-500/20 text-red-400'
                        }`}>
                          {briefing.market_overview.sp500.direction === 'up' ? '↑' : '↓'}
                          {Math.abs(briefing.market_overview.sp500.change_percent).toFixed(2)}%
                        </span>
                      </div>
                      <p className="text-2xl font-bold">
                        {formatNumber(briefing.market_overview.sp500.value)}
                      </p>
                      <p className="text-xs text-virtus-text-muted">pontos</p>
                    </div>
                  </div>
                  
                  {/* Alertas de Dividendos Urgentes */}
                  {briefing.dividend_alerts.filter(d => d.urgency === 'today' || d.urgency === 'urgent').length > 0 && (
                    <div className="bg-gradient-to-r from-red-500/10 to-orange-500/10 rounded-xl p-4 border border-red-500/30">
                      <div className="flex items-center gap-2 mb-3">
                        <AlertTriangle className="w-5 h-5 text-red-400" />
                        <h4 className="font-bold text-red-400">Dividendos Urgentes!</h4>
                      </div>
                      <div className="space-y-2">
                        {briefing.dividend_alerts
                          .filter(d => d.urgency === 'today' || d.urgency === 'urgent')
                          .map((d, idx) => (
                            <div key={idx} className="flex items-center justify-between bg-virtus-bg-card rounded-lg p-3">
                              <div>
                                <span className="font-bold text-white">{d.ticker}</span>
                                <span className="text-xs text-virtus-text-muted ml-2">{d.company_name}</span>
                              </div>
                              <div className="flex items-center gap-3">
                                <span className="text-green-400 font-medium">{d.dividend_yield}% DY</span>
                                <span className={`text-xs px-2 py-1 rounded font-bold ${getUrgencyStyle(d.urgency)}`}>
                                  {d.urgency === 'today' ? '🔥 HOJE!' : `⏰ ${d.days_remaining}d`}
                                </span>
                              </div>
                            </div>
                          ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Eventos de Alto Impacto */}
                  {briefing.economic_calendar.filter(e => e.impact === 'high').length > 0 && (
                    <div className="bg-gradient-to-r from-red-500/10 via-yellow-500/5 to-red-500/10 rounded-xl p-4 border border-red-500/30">
                      <div className="flex items-center gap-2 mb-3">
                        <Calendar className="w-5 h-5 text-red-400" />
                        <h4 className="font-bold text-red-400">🔴 Eventos de Alto Impacto Hoje!</h4>
                      </div>
                      <div className="space-y-2">
                        {briefing.economic_calendar
                          .filter(e => e.impact === 'high')
                          .slice(0, 5)
                          .map((e, idx) => (
                            <div key={idx} className="flex items-center justify-between bg-virtus-bg-card rounded-lg p-3">
                              <div className="flex items-center gap-3">
                                <div className="flex items-center gap-2 min-w-[60px]">
                                  <Clock className="w-4 h-4 text-red-400" />
                                  <span className="font-mono text-red-400 font-bold">{e.time}</span>
                                </div>
                                <span className="text-xs bg-virtus-bg-hover px-2 py-1 rounded text-virtus-text-muted">
                                  {e.country}
                                </span>
                                <span className="text-white font-medium">{e.event}</span>
                              </div>
                              <span className="text-xs bg-red-500/20 text-red-400 px-2 py-1 rounded font-bold">
                                Alto
                              </span>
                            </div>
                          ))}
                      </div>
                      <button
                        onClick={() => setActiveTab('calendar')}
                        className="text-sm text-red-400 hover:underline mt-3 flex items-center gap-1"
                      >
                        Ver calendário completo →
                      </button>
                    </div>
                  )}
                  
                  {/* Preview Notícias */}
                  {briefing.top_news.length > 0 && (
                    <div>
                      <h4 className="font-bold text-white mb-3 flex items-center gap-2">
                        <Newspaper className="w-5 h-5 text-virtus-accent-primary" />
                        Principais Notícias
                      </h4>
                      <div className="space-y-2">
                        {briefing.top_news.slice(0, 3).map((news, idx) => (
                          <div key={idx} className="flex items-start gap-3 p-3 bg-virtus-bg-hover rounded-lg">
                            <div className={`w-2 h-2 mt-2 rounded-full ${
                              news.sentiment === 'bullish' ? 'bg-green-400' :
                              news.sentiment === 'bearish' ? 'bg-red-400' : 'bg-yellow-400'
                            }`} />
                            <div className="flex-1 min-w-0">
                              <p className="text-white font-medium truncate">{news.title}</p>
                              <p className="text-xs text-virtus-text-muted">{news.source}</p>
                            </div>
                            <ChevronRight className="w-4 h-4 text-virtus-text-muted flex-shrink-0" />
                          </div>
                        ))}
                      </div>
                      <button
                        onClick={() => setActiveTab('news')}
                        className="text-sm text-virtus-accent-primary hover:underline mt-2"
                      >
                        Ver todas as notícias →
                      </button>
                    </div>
                  )}
                </div>
              )}
              
              {/* News Tab */}
              {activeTab === 'news' && (
                <div className="space-y-4">
                  <h3 className="text-xl font-bold text-white flex items-center gap-2">
                    <Newspaper className="w-6 h-6 text-virtus-accent-primary" />
                    Notícias do Mercado
                  </h3>
                  
                  {briefing.top_news.length > 0 ? (
                    <div className="space-y-3">
                      {briefing.top_news.map((news, idx) => (
                        <div key={idx} className="bg-virtus-bg-hover rounded-xl p-4 border border-virtus-border-primary hover:border-virtus-accent-primary/50 transition-colors">
                          <div className="flex items-start justify-between gap-4 mb-2">
                            <h4 className="font-bold text-white">{news.title}</h4>
                            <span className={`px-2 py-1 rounded text-xs font-medium whitespace-nowrap ${
                              news.sentiment === 'bullish' ? 'bg-green-500/20 text-green-400' :
                              news.sentiment === 'bearish' ? 'bg-red-500/20 text-red-400' :
                              'bg-gray-500/20 text-gray-400'
                            }`}>
                              {news.sentiment === 'bullish' ? '↑ Alta' :
                               news.sentiment === 'bearish' ? '↓ Baixa' : '— Neutro'}
                            </span>
                          </div>
                          <p className="text-sm text-virtus-text-secondary mb-3">{news.summary}</p>
                          <div className="flex items-center justify-between text-xs text-virtus-text-muted">
                            <span>{news.source}</span>
                            <span className={`px-2 py-0.5 rounded border ${getImpactColor(news.impact)}`}>
                              Impacto: {news.impact}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-10 text-virtus-text-muted">
                      <Newspaper className="w-12 h-12 mx-auto mb-3 opacity-50" />
                      <p>Nenhuma notícia disponível no momento</p>
                    </div>
                  )}
                </div>
              )}
              
              {/* Calendar Tab */}
              {activeTab === 'calendar' && (
                <div className="space-y-4">
                  <h3 className="text-xl font-bold text-white flex items-center gap-2">
                    <Calendar className="w-6 h-6 text-virtus-accent-primary" />
                    Calendário Econômico
                  </h3>
                  
                  {briefing.economic_calendar.length > 0 ? (
                    <div className="space-y-2">
                      {briefing.economic_calendar.map((event, idx) => (
                        <div key={idx} className="flex items-center gap-4 bg-virtus-bg-hover rounded-lg p-3 border border-virtus-border-primary">
                          <div className="flex items-center gap-2 min-w-[80px]">
                            <Clock className="w-4 h-4 text-virtus-text-muted" />
                            <span className="font-mono text-white">{event.time}</span>
                          </div>
                          <div className="flex items-center gap-2 min-w-[50px]">
                            <Globe className="w-4 h-4 text-virtus-text-muted" />
                            <span className="text-virtus-text-secondary">{event.country}</span>
                          </div>
                          <div className="flex-1">
                            <span className="text-white">{event.event}</span>
                          </div>
                          <span className={`px-2 py-1 rounded text-xs font-bold border ${getImpactColor(event.impact)}`}>
                            {event.impact === 'high' ? '🔴 Alto' :
                             event.impact === 'medium' ? '🟡 Médio' : '🟢 Baixo'}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-10 text-virtus-text-muted">
                      <Calendar className="w-12 h-12 mx-auto mb-3 opacity-50" />
                      <p>Nenhum evento econômico para hoje</p>
                    </div>
                  )}
                </div>
              )}
              
              {/* Dividends Tab */}
              {activeTab === 'dividends' && (
                <div className="space-y-4">
                  <h3 className="text-xl font-bold text-white flex items-center gap-2">
                    <DollarSign className="w-6 h-6 text-green-400" />
                    Oportunidades de Dividendos
                  </h3>
                  
                  {briefing.dividend_alerts.length > 0 ? (
                    <div className="space-y-3">
                      {briefing.dividend_alerts.map((div, idx) => (
                        <div key={idx} className={`rounded-xl p-4 border ${
                          div.urgency === 'today' ? 'bg-red-500/10 border-red-500/30' :
                          div.urgency === 'urgent' ? 'bg-orange-500/10 border-orange-500/30' :
                          'bg-virtus-bg-hover border-virtus-border-primary'
                        }`}>
                          <div className="flex items-center justify-between mb-3">
                            <div>
                              <span className="text-xl font-bold text-white">{div.ticker}</span>
                              <p className="text-sm text-virtus-text-secondary">{div.company_name}</p>
                            </div>
                            <span className={`px-3 py-1 rounded-full text-sm font-bold ${getUrgencyStyle(div.urgency)}`}>
                              {div.urgency === 'today' ? '🔥 ÚLTIMO DIA!' :
                               div.urgency === 'urgent' ? `⏰ ${div.days_remaining} dias` :
                               `📅 ${div.days_remaining} dias`}
                            </span>
                          </div>
                          
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                            <div className="bg-virtus-bg-card rounded-lg p-2">
                              <p className="text-virtus-text-muted text-xs">Comprar até</p>
                              <p className="font-bold text-yellow-400">
                                {new Date(div.buy_limit_date).toLocaleDateString('pt-BR')}
                              </p>
                            </div>
                            <div className="bg-virtus-bg-card rounded-lg p-2">
                              <p className="text-virtus-text-muted text-xs">Dividendo</p>
                              <p className="font-bold text-green-400">
                                {formatCurrency(div.dividend_value)}
                              </p>
                            </div>
                            <div className="bg-virtus-bg-card rounded-lg p-2">
                              <p className="text-virtus-text-muted text-xs">Dividend Yield</p>
                              <p className="font-bold text-green-400">{div.dividend_yield}%</p>
                            </div>
                            <div className="bg-virtus-bg-card rounded-lg p-2">
                              <p className="text-virtus-text-muted text-xs">Pagamento</p>
                              <p className="font-bold text-virtus-text-secondary">
                                {div.payment_date ? new Date(div.payment_date).toLocaleDateString('pt-BR') : 'A definir'}
                              </p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-10 text-virtus-text-muted">
                      <DollarSign className="w-12 h-12 mx-auto mb-3 opacity-50" />
                      <p>Nenhuma oportunidade de dividendo no momento</p>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
        
        {/* Footer */}
        <div className="bg-virtus-bg-hover border-t border-virtus-border-primary p-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-virtus-text-muted">
              {briefing && `Atualizado em ${new Date(briefing.generated_at).toLocaleTimeString('pt-BR')}`}
            </p>
            <div className="flex gap-2">
              <button
                onClick={togglePlayPause}
                className="btn-secondary flex items-center gap-2"
              >
                {isPlaying ? <Pause className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
                {isPlaying ? 'Pausar Áudio' : 'Ouvir Briefing'}
              </button>
              <button
                onClick={onClose}
                className="btn-primary"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DailyBriefingModal;
