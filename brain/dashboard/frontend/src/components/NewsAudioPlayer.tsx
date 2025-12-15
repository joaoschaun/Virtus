/**
 * VIRTUS Dashboard - News Audio Player
 * =====================================
 * 
 * Componente para reprodução de notícias financeiras em áudio (português).
 */

import React, { useState, useEffect, useRef } from 'react';
import { 
  Play, 
  Pause, 
  SkipForward, 
  SkipBack, 
  Volume2, 
  VolumeX,
  Newspaper,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Minus,
  Clock,
  ExternalLink,
} from 'lucide-react';

// Tipos
interface NewsItem {
  id: string;
  title: string;
  summary: string;
  content: string;
  source: string;
  category: string;
  priority: string;
  published_at: string;
  url?: string;
  related_symbols: string[];
  audio_url?: string;
  audio_duration_seconds: number;
  sentiment?: 'bullish' | 'bearish' | 'neutral';
  impact_score: number;
}

interface Category {
  value: string;
  label: string;
  icon: string;
}

// API Base URL
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Componente Principal
export default function NewsAudioPlayer() {
  const [news, setNews] = useState<NewsItem[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [volume, setVolume] = useState(0.8);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoPlay, setAutoPlay] = useState(true);
  const [progress, setProgress] = useState(0);
  
  const audioRef = useRef<HTMLAudioElement>(null);

  // Busca categorias
  useEffect(() => {
    fetchCategories();
  }, []);

  // Busca notícias quando categoria muda
  useEffect(() => {
    fetchNews();
  }, [selectedCategory]);

  // Atualiza progresso do áudio
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const updateProgress = () => {
      if (audio.duration) {
        setProgress((audio.currentTime / audio.duration) * 100);
      }
    };

    audio.addEventListener('timeupdate', updateProgress);
    return () => audio.removeEventListener('timeupdate', updateProgress);
  }, []);

  // Auto-play próxima notícia
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleEnded = () => {
      if (autoPlay && currentIndex < news.length - 1) {
        setCurrentIndex(prev => prev + 1);
        setTimeout(() => {
          audio.play().catch(console.error);
        }, 500);
      } else {
        setIsPlaying(false);
      }
    };

    audio.addEventListener('ended', handleEnded);
    return () => audio.removeEventListener('ended', handleEnded);
  }, [autoPlay, currentIndex, news.length]);

  const fetchCategories = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/news/categories/list`);
      if (response.ok) {
        const data = await response.json();
        setCategories(data.categories);
      }
    } catch (err) {
      console.error('Erro ao buscar categorias:', err);
    }
  };

  const fetchNews = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(
        `${API_BASE}/api/news?category=${selectedCategory}&limit=10`
      );
      
      if (!response.ok) {
        throw new Error('Falha ao carregar notícias');
      }
      
      const data = await response.json();
      setNews(data.news);
      setCurrentIndex(0);
      setProgress(0);
      
    } catch (err: any) {
      setError(err.message || 'Erro ao carregar notícias');
    } finally {
      setIsLoading(false);
    }
  };

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
    } else {
      audio.play().catch(console.error);
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

  const skipNext = () => {
    if (currentIndex < news.length - 1) {
      setCurrentIndex(prev => prev + 1);
      setProgress(0);
      if (isPlaying && audioRef.current) {
        setTimeout(() => audioRef.current?.play(), 100);
      }
    }
  };

  const skipPrevious = () => {
    if (currentIndex > 0) {
      setCurrentIndex(prev => prev - 1);
      setProgress(0);
      if (isPlaying && audioRef.current) {
        setTimeout(() => audioRef.current?.play(), 100);
      }
    }
  };

  const playSummary = async () => {
    try {
      const audio = audioRef.current;
      if (audio) {
        audio.src = `${API_BASE}/api/news/summary/audio`;
        await audio.play();
        setIsPlaying(true);
      }
    } catch (err) {
      console.error('Erro ao reproduzir resumo:', err);
    }
  };

  const getSentimentIcon = (sentiment?: string) => {
    switch (sentiment) {
      case 'bullish':
        return <TrendingUp className="w-4 h-4 text-green-500" />;
      case 'bearish':
        return <TrendingDown className="w-4 h-4 text-red-500" />;
      default:
        return <Minus className="w-4 h-4 text-gray-400" />;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'medium':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      default:
        return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const currentNews = news[currentIndex];

  return (
    <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-700/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Newspaper className="w-5 h-5 text-blue-400" />
          <h3 className="font-semibold text-white">Notícias em Áudio</h3>
          <span className="text-xs text-gray-400">🇧🇷 Português</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={playSummary}
            className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            📻 Resumo Diário
          </button>
          <button
            onClick={fetchNews}
            className="p-1.5 text-gray-400 hover:text-white transition-colors"
            title="Atualizar"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Categorias */}
      <div className="px-4 py-2 border-b border-gray-700/50 flex gap-2 overflow-x-auto">
        {categories.map(cat => (
          <button
            key={cat.value}
            onClick={() => setSelectedCategory(cat.value)}
            className={`px-3 py-1.5 text-xs rounded-lg whitespace-nowrap transition-colors ${
              selectedCategory === cat.value
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700/50 text-gray-300 hover:bg-gray-700'
            }`}
          >
            {cat.icon} {cat.label}
          </button>
        ))}
      </div>

      {/* Audio Element (hidden) */}
      <audio
        ref={audioRef}
        src={currentNews?.audio_url ? `${API_BASE}${currentNews.audio_url}` : undefined}
      />

      {/* Player */}
      <div className="p-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          </div>
        ) : error ? (
          <div className="text-center py-8">
            <p className="text-red-400 mb-2">{error}</p>
            <button
              onClick={fetchNews}
              className="text-blue-400 hover:text-blue-300 text-sm"
            >
              Tentar novamente
            </button>
          </div>
        ) : currentNews ? (
          <>
            {/* Current News Info */}
            <div className="mb-4">
              <div className="flex items-start justify-between gap-4 mb-2">
                <h4 className="text-white font-medium leading-tight">
                  {currentNews.title}
                </h4>
                <div className="flex items-center gap-2 shrink-0">
                  {getSentimentIcon(currentNews.sentiment)}
                  <span className={`px-2 py-0.5 text-xs rounded border ${getPriorityColor(currentNews.priority)}`}>
                    {currentNews.priority === 'high' ? 'Alta' : currentNews.priority === 'medium' ? 'Média' : 'Baixa'}
                  </span>
                </div>
              </div>
              
              <p className="text-gray-400 text-sm mb-2 line-clamp-2">
                {currentNews.summary}
              </p>
              
              <div className="flex items-center gap-3 text-xs text-gray-500">
                <span>{currentNews.source}</span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {formatDate(currentNews.published_at)}
                </span>
                {currentNews.related_symbols.length > 0 && (
                  <span className="flex gap-1">
                    {currentNews.related_symbols.slice(0, 3).map(symbol => (
                      <span key={symbol} className="px-1.5 py-0.5 bg-gray-700 rounded text-gray-300">
                        {symbol}
                      </span>
                    ))}
                  </span>
                )}
                {currentNews.url && (
                  <a
                    href={currentNews.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-blue-400 hover:text-blue-300"
                  >
                    <ExternalLink className="w-3 h-3" />
                    Ler mais
                  </a>
                )}
              </div>
            </div>

            {/* Progress Bar */}
            <div className="mb-4">
              <div className="h-1 bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>{audioRef.current ? formatTime(audioRef.current.currentTime) : '0:00'}</span>
                <span>{formatTime(currentNews.audio_duration_seconds)}</span>
              </div>
            </div>

            {/* Controls */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <button
                  onClick={skipPrevious}
                  disabled={currentIndex === 0}
                  className="p-2 text-gray-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <SkipBack className="w-5 h-5" />
                </button>
                
                <button
                  onClick={togglePlay}
                  className="p-3 bg-blue-600 hover:bg-blue-700 text-white rounded-full transition-colors"
                >
                  {isPlaying ? (
                    <Pause className="w-6 h-6" />
                  ) : (
                    <Play className="w-6 h-6 ml-0.5" />
                  )}
                </button>
                
                <button
                  onClick={skipNext}
                  disabled={currentIndex === news.length - 1}
                  className="p-2 text-gray-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <SkipForward className="w-5 h-5" />
                </button>
              </div>

              <div className="flex items-center gap-3">
                <span className="text-xs text-gray-500">
                  {currentIndex + 1} / {news.length}
                </span>
                
                <div className="flex items-center gap-2">
                  <button onClick={toggleMute} className="text-gray-400 hover:text-white">
                    {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
                  </button>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={volume}
                    onChange={handleVolumeChange}
                    className="w-16 h-1 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                  />
                </div>

                <label className="flex items-center gap-1.5 text-xs text-gray-400">
                  <input
                    type="checkbox"
                    checked={autoPlay}
                    onChange={(e) => setAutoPlay(e.target.checked)}
                    className="rounded border-gray-600 bg-gray-700 text-blue-600"
                  />
                  Auto
                </label>
              </div>
            </div>
          </>
        ) : (
          <div className="text-center py-8 text-gray-400">
            Nenhuma notícia disponível
          </div>
        )}
      </div>

      {/* News List */}
      {news.length > 0 && (
        <div className="border-t border-gray-700/50 max-h-64 overflow-y-auto">
          {news.map((item, index) => (
            <button
              key={item.id}
              onClick={() => {
                setCurrentIndex(index);
                setProgress(0);
              }}
              className={`w-full px-4 py-2 text-left hover:bg-gray-700/30 transition-colors flex items-center gap-3 ${
                index === currentIndex ? 'bg-blue-600/20 border-l-2 border-blue-500' : ''
              }`}
            >
              <div className="shrink-0">
                {index === currentIndex && isPlaying ? (
                  <div className="w-6 h-6 flex items-center justify-center">
                    <div className="flex gap-0.5">
                      <div className="w-1 h-3 bg-blue-500 animate-pulse" />
                      <div className="w-1 h-4 bg-blue-500 animate-pulse delay-75" />
                      <div className="w-1 h-2 bg-blue-500 animate-pulse delay-150" />
                    </div>
                  </div>
                ) : (
                  <span className="w-6 h-6 flex items-center justify-center text-xs text-gray-500">
                    {index + 1}
                  </span>
                )}
              </div>
              
              <div className="flex-1 min-w-0">
                <p className={`text-sm truncate ${index === currentIndex ? 'text-white' : 'text-gray-300'}`}>
                  {item.title}
                </p>
                <p className="text-xs text-gray-500 truncate">
                  {item.source} • {formatTime(item.audio_duration_seconds)}
                </p>
              </div>
              
              {getSentimentIcon(item.sentiment)}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
