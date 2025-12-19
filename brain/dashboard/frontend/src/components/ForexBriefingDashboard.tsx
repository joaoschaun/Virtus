/**
 * VIRTUS Dashboard - Forex Briefing Dashboard
 * ============================================
 * 
 * Dashboard completo para operações Forex:
 * - Briefing diário com áudio em português
 * - Calendário econômico
 * - Sinais por símbolo
 * - Notícias relevantes
 */

import React, { useState, useEffect, useRef } from 'react';
import { 
  Play, 
  Pause, 
  Volume2, 
  VolumeX,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Minus,
  Calendar,
  Newspaper,
  AlertTriangle,
  BarChart3,
  Clock,
  Globe,
  Share2,
  Download,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

// Tipos
interface ForexNews {
  id: string;
  title: string;
  summary: string;
  source: string;
  provider: string;
  published_at: string;
  url?: string;
  symbols: string[];
  sentiment: 'bullish' | 'bearish' | 'neutral' | 'mixed';
  sentiment_score: number;
  impact: 'high' | 'medium' | 'low';
  audio_url?: string;
}

interface EconomicEvent {
  id: string;
  name: string;
  country: string;
  date: string;
  actual?: string;
  previous?: string;
  forecast?: string;
  impact: 'high' | 'medium' | 'low';
  currencies_affected: string[];
}

interface SymbolSignal {
  symbol: string;
  direction: 'bullish' | 'bearish' | 'neutral' | 'mixed';
  strength: number;
  news_sentiment: string;
  calendar_impact: string;
  summary: string;
  key_events: string[];
  timestamp: string;
}

interface DailyBriefing {
  date: string;
  market_mood: 'bullish' | 'bearish' | 'neutral' | 'mixed';
  headline: string;
  summary: string;
  signals: { [key: string]: SymbolSignal };
  top_news: ForexNews[];
  key_events: EconomicEvent[];
  social_post: string;
  audio_url?: string;
  audio_text: string;
}

// API Base URL
const API_BASE = '';

// Símbolos Forex
const FOREX_SYMBOLS = [
  { symbol: 'XAUUSD', name: 'Ouro', icon: '🥇' },
  { symbol: 'EURUSD', name: 'EUR/USD', icon: '🇪🇺' },
  { symbol: 'GBPUSD', name: 'GBP/USD', icon: '🇬🇧' },
  { symbol: 'USDJPY', name: 'USD/JPY', icon: '🇯🇵' },
];

// Países e bandeiras
const COUNTRY_FLAGS: { [key: string]: string } = {
  'US': '🇺🇸',
  'EU': '🇪🇺',
  'GB': '🇬🇧',
  'JP': '🇯🇵',
  'CH': '🇨🇭',
  'AU': '🇦🇺',
  'CA': '🇨🇦',
};

// Componente Principal
export default function ForexBriefingDashboard() {
  // Estados
  const [briefing, setBriefing] = useState<DailyBriefing | null>(null);
  const [news, setNews] = useState<ForexNews[]>([]);
  const [events, setEvents] = useState<EconomicEvent[]>([]);
  const [signals, setSignals] = useState<{ [key: string]: SymbolSignal }>({});
  
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [activeTab, setActiveTab] = useState<'briefing' | 'calendar' | 'news'>('briefing');
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  
  // Audio
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [volume, setVolume] = useState(0.8);
  const [audioProgress, setAudioProgress] = useState(0);
  const audioRef = useRef<HTMLAudioElement>(null);
  
  // UI
  const [expandedEvent, setExpandedEvent] = useState<string | null>(null);
  
  // Carrega dados iniciais
  useEffect(() => {
    loadAllData();
  }, []);
  
  // Atualiza progresso do áudio
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    
    const updateProgress = () => {
      if (audio.duration) {
        setAudioProgress((audio.currentTime / audio.duration) * 100);
      }
    };
    
    audio.addEventListener('timeupdate', updateProgress);
    return () => audio.removeEventListener('timeupdate', updateProgress);
  }, []);
  
  // Funções de carregamento
  const loadAllData = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      await Promise.all([
        loadBriefing(),
        loadNews(),
        loadCalendar(),
        loadSignals(),
      ]);
    } catch (err) {
      setError('Erro ao carregar dados. Tente novamente.');
      console.error('Erro:', err);
    } finally {
      setIsLoading(false);
    }
  };
  
  const loadBriefing = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/forex/briefing/daily`);
      const data = await response.json();
      if (data.success) {
        setBriefing(data.briefing);
      }
    } catch (err) {
      console.error('Erro ao carregar briefing:', err);
    }
  };
  
  const loadNews = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/forex/news?limit=20`);
      const data = await response.json();
      if (data.success) {
        setNews(data.news);
      }
    } catch (err) {
      console.error('Erro ao carregar notícias:', err);
    }
  };
  
  const loadCalendar = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/forex/calendar?days_ahead=7&min_impact=medium`);
      const data = await response.json();
      if (data.success) {
        setEvents(data.events);
      }
    } catch (err) {
      console.error('Erro ao carregar calendário:', err);
    }
  };
  
  const loadSignals = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/forex/signals`);
      const data = await response.json();
      if (data.success) {
        setSignals(data.signals);
      }
    } catch (err) {
      console.error('Erro ao carregar sinais:', err);
    }
  };
  
  // Controles de áudio
  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;
    
    if (isPlaying) {
      audio.pause();
    } else {
      audio.play();
    }
    setIsPlaying(!isPlaying);
  };
  
  const toggleMute = () => {
    const audio = audioRef.current;
    if (audio) {
      audio.muted = !isMuted;
      setIsMuted(!isMuted);
    }
  };
  
  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    if (audioRef.current) {
      audioRef.current.volume = newVolume;
    }
  };
  
  // Renderização de ícones de sentimento
  const getSentimentIcon = (sentiment: string) => {
    switch (sentiment) {
      case 'bullish':
        return <TrendingUp className="w-5 h-5 text-green-500" />;
      case 'bearish':
        return <TrendingDown className="w-5 h-5 text-red-500" />;
      case 'mixed':
        return <Minus className="w-5 h-5 text-yellow-500" />;
      default:
        return <Minus className="w-5 h-5 text-gray-400" />;
    }
  };
  
  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'bullish':
        return 'bg-green-500/10 text-green-500 border-green-500/20';
      case 'bearish':
        return 'bg-red-500/10 text-red-500 border-red-500/20';
      case 'mixed':
        return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
      default:
        return 'bg-gray-500/10 text-gray-400 border-gray-500/20';
    }
  };
  
  const getImpactColor = (impact: string) => {
    switch (impact) {
      case 'high':
        return 'bg-red-500 text-white';
      case 'medium':
        return 'bg-yellow-500 text-black';
      default:
        return 'bg-gray-500 text-white';
    }
  };
  
  // Formatar data
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };
  
  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-900">
        <div className="text-center">
          <RefreshCw className="w-12 h-12 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Carregando Forex Briefing...</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-gray-900 text-white p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <BarChart3 className="w-8 h-8 text-blue-500" />
            Forex Briefing
          </h1>
          <p className="text-gray-400 text-sm mt-1">
            {briefing?.headline || 'Análise diária do mercado forex'}
          </p>
        </div>
        
        <div className="flex items-center gap-4">
          {/* Market Mood Badge */}
          {briefing && (
            <div className={`px-4 py-2 rounded-lg border ${getSentimentColor(briefing.market_mood)}`}>
              {getSentimentIcon(briefing.market_mood)}
              <span className="ml-2 font-medium">
                {briefing.market_mood === 'bullish' ? 'Otimista' :
                 briefing.market_mood === 'bearish' ? 'Cauteloso' :
                 briefing.market_mood === 'mixed' ? 'Misto' : 'Neutro'}
              </span>
            </div>
          )}
          
          <button
            onClick={loadAllData}
            className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors"
            title="Atualizar"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>
      </div>
      
      {/* Signals Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {FOREX_SYMBOLS.map(({ symbol, name, icon }) => {
          const signal = signals[symbol];
          return (
            <div
              key={symbol}
              className={`p-4 rounded-xl bg-gray-800 border cursor-pointer transition-all hover:scale-105 ${
                selectedSymbol === symbol ? 'border-blue-500 ring-2 ring-blue-500/30' : 'border-gray-700'
              }`}
              onClick={() => setSelectedSymbol(selectedSymbol === symbol ? null : symbol)}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-2xl">{icon}</span>
                {signal && getSentimentIcon(signal.direction)}
              </div>
              <h3 className="font-bold text-lg">{symbol}</h3>
              <p className="text-gray-400 text-sm">{name}</p>
              {signal && (
                <div className="mt-2">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 bg-gray-700 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${
                          signal.direction === 'bullish' ? 'bg-green-500' :
                          signal.direction === 'bearish' ? 'bg-red-500' : 'bg-gray-500'
                        }`}
                        style={{ width: `${signal.strength * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-400">
                      {Math.round(signal.strength * 100)}%
                    </span>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
      
      {/* Selected Symbol Detail */}
      {selectedSymbol && signals[selectedSymbol] && (
        <div className="mb-6 p-4 rounded-xl bg-gray-800 border border-gray-700">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xl">
              {FOREX_SYMBOLS.find(s => s.symbol === selectedSymbol)?.icon}
            </span>
            <h3 className="font-bold">{selectedSymbol}</h3>
          </div>
          <p className="text-gray-300">{signals[selectedSymbol].summary}</p>
          {signals[selectedSymbol].key_events.length > 0 && (
            <div className="mt-2">
              <p className="text-sm text-gray-400">Eventos relevantes:</p>
              <ul className="list-disc list-inside text-sm text-gray-300">
                {signals[selectedSymbol].key_events.map((event, i) => (
                  <li key={i}>{event}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
      
      {/* Audio Player */}
      {briefing?.audio_url && (
        <div className="mb-6 p-4 rounded-xl bg-gradient-to-r from-blue-900/50 to-purple-900/50 border border-blue-500/30">
          <div className="flex items-center gap-4">
            <button
              onClick={togglePlay}
              className="w-12 h-12 rounded-full bg-blue-500 flex items-center justify-center hover:bg-blue-600 transition-colors"
            >
              {isPlaying ? (
                <Pause className="w-6 h-6" />
              ) : (
                <Play className="w-6 h-6 ml-1" />
              )}
            </button>
            
            <div className="flex-1">
              <p className="font-medium mb-2">🎧 Ouça o Briefing de Hoje</p>
              <div className="h-2 bg-gray-700 rounded-full">
                <div
                  className="h-2 bg-blue-500 rounded-full transition-all"
                  style={{ width: `${audioProgress}%` }}
                />
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              <button onClick={toggleMute} className="p-2 hover:bg-gray-700 rounded">
                {isMuted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
              </button>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={volume}
                onChange={handleVolumeChange}
                className="w-20 accent-blue-500"
              />
            </div>
          </div>
          
          <audio
            ref={audioRef}
            src={`${API_BASE}${briefing.audio_url}`}
            onEnded={() => setIsPlaying(false)}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
          />
        </div>
      )}
      
      {/* Tabs */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setActiveTab('briefing')}
          className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
            activeTab === 'briefing' ? 'bg-blue-500 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          Resumo
        </button>
        <button
          onClick={() => setActiveTab('calendar')}
          className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
            activeTab === 'calendar' ? 'bg-blue-500 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
          }`}
        >
          <Calendar className="w-4 h-4" />
          Calendário
        </button>
        <button
          onClick={() => setActiveTab('news')}
          className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
            activeTab === 'news' ? 'bg-blue-500 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
          }`}
        >
          <Newspaper className="w-4 h-4" />
          Notícias
        </button>
      </div>
      
      {/* Tab Content */}
      <div className="rounded-xl bg-gray-800 border border-gray-700 p-4">
        {/* Briefing Tab */}
        {activeTab === 'briefing' && briefing && (
          <div className="space-y-4">
            <div>
              <h3 className="font-bold text-lg mb-2">Resumo do Dia</h3>
              <p className="text-gray-300">{briefing.summary}</p>
            </div>
            
            {/* Key Events */}
            {briefing.key_events.length > 0 && (
              <div>
                <h3 className="font-bold text-lg mb-2 flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-yellow-500" />
                  Eventos de Alto Impacto
                </h3>
                <div className="space-y-2">
                  {briefing.key_events.map(event => (
                    <div
                      key={event.id}
                      className="p-3 rounded-lg bg-gray-700/50 flex items-center justify-between"
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-xl">{COUNTRY_FLAGS[event.country] || '🌍'}</span>
                        <div>
                          <p className="font-medium">{event.name}</p>
                          <p className="text-sm text-gray-400">{formatDate(event.date)}</p>
                        </div>
                      </div>
                      <span className={`px-2 py-1 rounded text-xs font-bold ${getImpactColor(event.impact)}`}>
                        {event.impact.toUpperCase()}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {/* Social Post */}
            {briefing.social_post && (
              <div>
                <h3 className="font-bold text-lg mb-2 flex items-center gap-2">
                  <Share2 className="w-5 h-5 text-blue-500" />
                  Post para Redes Sociais
                </h3>
                <div className="p-4 rounded-lg bg-gray-700/50 whitespace-pre-wrap text-sm">
                  {briefing.social_post}
                </div>
                <button
                  onClick={() => navigator.clipboard.writeText(briefing.social_post)}
                  className="mt-2 px-4 py-2 bg-blue-500 rounded-lg text-sm hover:bg-blue-600 transition-colors"
                >
                  Copiar Post
                </button>
              </div>
            )}
          </div>
        )}
        
        {/* Calendar Tab */}
        {activeTab === 'calendar' && (
          <div>
            <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
              <Calendar className="w-5 h-5 text-blue-500" />
              Calendário Econômico (7 dias)
            </h3>
            
            {events.length === 0 ? (
              <p className="text-gray-400">Nenhum evento encontrado.</p>
            ) : (
              <div className="space-y-2">
                {events.map(event => (
                  <div
                    key={event.id}
                    className="p-3 rounded-lg bg-gray-700/50 cursor-pointer hover:bg-gray-700"
                    onClick={() => setExpandedEvent(expandedEvent === event.id ? null : event.id)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="text-xl">{COUNTRY_FLAGS[event.country] || '🌍'}</span>
                        <div>
                          <p className="font-medium">{event.name}</p>
                          <p className="text-sm text-gray-400 flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {formatDate(event.date)}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-1 rounded text-xs font-bold ${getImpactColor(event.impact)}`}>
                          {event.impact.toUpperCase()}
                        </span>
                        {expandedEvent === event.id ? (
                          <ChevronUp className="w-5 h-5 text-gray-400" />
                        ) : (
                          <ChevronDown className="w-5 h-5 text-gray-400" />
                        )}
                      </div>
                    </div>
                    
                    {expandedEvent === event.id && (
                      <div className="mt-3 pt-3 border-t border-gray-600 grid grid-cols-3 gap-4 text-sm">
                        <div>
                          <p className="text-gray-400">Anterior</p>
                          <p className="font-medium">{event.previous || '-'}</p>
                        </div>
                        <div>
                          <p className="text-gray-400">Previsão</p>
                          <p className="font-medium">{event.forecast || '-'}</p>
                        </div>
                        <div>
                          <p className="text-gray-400">Atual</p>
                          <p className="font-medium text-blue-400">{event.actual || 'Pendente'}</p>
                        </div>
                        <div className="col-span-3">
                          <p className="text-gray-400">Moedas afetadas</p>
                          <div className="flex gap-1 mt-1">
                            {event.currencies_affected.map(currency => (
                              <span key={currency} className="px-2 py-1 bg-gray-600 rounded text-xs">
                                {currency}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
        
        {/* News Tab */}
        {activeTab === 'news' && (
          <div>
            <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
              <Newspaper className="w-5 h-5 text-blue-500" />
              Notícias Forex
            </h3>
            
            {news.length === 0 ? (
              <p className="text-gray-400">Nenhuma notícia encontrada.</p>
            ) : (
              <div className="space-y-3">
                {news.map(item => (
                  <div
                    key={item.id}
                    className="p-4 rounded-lg bg-gray-700/50 hover:bg-gray-700 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          {getSentimentIcon(item.sentiment)}
                          <span className={`px-2 py-0.5 rounded text-xs ${getImpactColor(item.impact)}`}>
                            {item.impact.toUpperCase()}
                          </span>
                          <span className="text-xs text-gray-400">
                            {item.source} • {item.provider.toUpperCase()}
                          </span>
                        </div>
                        <h4 className="font-medium mb-1">{item.title}</h4>
                        <p className="text-sm text-gray-400">{item.summary}</p>
                        <div className="flex flex-wrap gap-1 mt-2">
                          {item.symbols.map(symbol => (
                            <span key={symbol} className="px-2 py-1 bg-blue-500/20 text-blue-400 rounded text-xs">
                              {symbol}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-gray-400">{formatDate(item.published_at)}</p>
                        {item.url && (
                          <a
                            href={item.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-blue-400 text-xs hover:underline mt-1"
                          >
                            <Globe className="w-3 h-3" />
                            Abrir
                          </a>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
      
      {/* Error Toast */}
      {error && (
        <div className="fixed bottom-4 right-4 p-4 bg-red-500 rounded-lg text-white shadow-lg">
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-4 underline"
          >
            Fechar
          </button>
        </div>
      )}
    </div>
  );
}
