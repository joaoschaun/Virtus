import React, { useState, useEffect } from 'react';
import { 
  Instagram, 
  Download, 
  Copy, 
  Check, 
  Trash2, 
  TrendingUp, 
  TrendingDown, 
  Minus,
  Newspaper,
  Lightbulb,
  BookOpen,
  RefreshCw,
  Plus,
  Image as ImageIcon,
  X,
  Zap,
  Sparkles,
  Clock
} from 'lucide-react';
import { socialService, Post, MarketAlertRequest, NewsPostRequest } from '../services/socialService';

const SocialMedia: React.FC = () => {
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [autoGenerating, setAutoGenerating] = useState(false);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [showModal, setShowModal] = useState<string | null>(null);
  const [selectedPost, setSelectedPost] = useState<Post | null>(null);
  const [pendingCount, setPendingCount] = useState(0);
  
  // Form states
  const [alertForm, setAlertForm] = useState<MarketAlertRequest>({
    symbol: 'XAUUSD',
    trend: 'bullish',
    price: 0,
  });
  
  const [newsForm, setNewsForm] = useState<NewsPostRequest>({
    title: '',
    summary: '',
    sentiment: 'neutral',
  });

  useEffect(() => {
    loadPosts();
    loadPendingCount();
  }, []);

  const loadPosts = async () => {
    try {
      setLoading(true);
      const data = await socialService.getPosts(50);
      setPosts(data.posts || []);
    } catch (error) {
      console.error('Erro ao carregar posts:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadPendingCount = async () => {
    try {
      const data = await socialService.getPendingPosts();
      setPendingCount(data.count || 0);
    } catch (error) {
      console.error('Erro ao carregar pendentes:', error);
    }
  };

  // =============================================
  // GERAÇÃO AUTOMÁTICA - Pega notícias do Brain
  // =============================================
  const autoGenerateFromNews = async () => {
    try {
      setAutoGenerating(true);
      const result = await socialService.autoGenerateFromNews(3);
      if (result.generated > 0) {
        alert(`✅ ${result.generated} posts gerados das notícias do Brain!\n\nBaixe as imagens e poste no Instagram.`);
      } else {
        alert('Não há novas notícias para gerar posts. Tente novamente mais tarde.');
      }
      loadPosts();
      loadPendingCount();
    } catch (error: any) {
      console.error('Erro ao gerar:', error);
      alert('Erro ao gerar posts: ' + (error.response?.data?.detail || error.message));
    } finally {
      setAutoGenerating(false);
    }
  };

  const copyCaption = async (post: Post) => {
    try {
      await navigator.clipboard.writeText(post.caption);
      setCopiedId(post.id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (error) {
      console.error('Erro ao copiar:', error);
    }
  };

  const downloadImage = (post: Post) => {
    const url = socialService.getDownloadUrl(post.image_file);
    window.open(url, '_blank');
  };

  const markAsPosted = async (post: Post) => {
    try {
      await socialService.markAsPosted(post.id);
      loadPosts();
    } catch (error) {
      console.error('Erro ao marcar como postado:', error);
    }
  };

  const deletePost = async (postId: number) => {
    if (!confirm('Tem certeza que deseja excluir este post?')) return;
    
    try {
      await socialService.deletePost(postId);
      loadPosts();
    } catch (error) {
      console.error('Erro ao excluir:', error);
    }
  };

  const generateMarketAlert = async () => {
    try {
      setGenerating(true);
      await socialService.generateMarketAlert(alertForm);
      setShowModal(null);
      loadPosts();
    } catch (error) {
      console.error('Erro ao gerar:', error);
      alert('Erro ao gerar post');
    } finally {
      setGenerating(false);
    }
  };

  const generateNews = async () => {
    try {
      setGenerating(true);
      await socialService.generateNews(newsForm);
      setShowModal(null);
      loadPosts();
    } catch (error) {
      console.error('Erro ao gerar:', error);
      alert('Erro ao gerar post');
    } finally {
      setGenerating(false);
    }
  };

  const generateTip = async (type: 'trading_tip' | 'educational') => {
    try {
      setGenerating(true);
      await socialService.generateTip(type);
      loadPosts();
    } catch (error) {
      console.error('Erro ao gerar:', error);
      alert('Erro ao gerar post');
    } finally {
      setGenerating(false);
    }
  };

  const getTrendIcon = (trend?: string) => {
    switch (trend) {
      case 'bullish':
        return <TrendingUp className="w-4 h-4 text-green-500" />;
      case 'bearish':
        return <TrendingDown className="w-4 h-4 text-red-500" />;
      default:
        return <Minus className="w-4 h-4 text-gray-500" />;
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'market_alert':
        return <TrendingUp className="w-4 h-4" />;
      case 'news':
      case 'news_auto':
        return <Newspaper className="w-4 h-4" />;
      case 'trading_tip':
        return <Lightbulb className="w-4 h-4" />;
      case 'educational':
        return <BookOpen className="w-4 h-4" />;
      default:
        return <ImageIcon className="w-4 h-4" />;
    }
  };

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'market_alert':
        return 'Alerta';
      case 'news':
        return 'Notícia';
      case 'news_auto':
        return '🔥 Auto News';
      case 'trading_tip':
        return 'Dica';
      case 'educational':
        return 'Educacional';
      case 'daily_summary':
        return 'Resumo Diário';
      default:
        return type;
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Instagram className="w-8 h-8 text-pink-500" />
          <div>
            <h1 className="text-2xl font-bold text-white">Social Media</h1>
            <p className="text-gray-400">Gerencie posts para Instagram</p>
          </div>
        </div>
        
        <div className="flex gap-2">
          {pendingCount > 0 && (
            <div className="px-4 py-2 bg-orange-600/20 border border-orange-500 rounded-lg flex items-center gap-2 text-orange-400">
              <Clock className="w-4 h-4" />
              {pendingCount} para postar
            </div>
          )}
          <button
            onClick={loadPosts}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg flex items-center gap-2 text-white"
          >
            <RefreshCw className="w-4 h-4" />
            Atualizar
          </button>
        </div>
      </div>

      {/* BOTÃO PRINCIPAL - Gerar das Notícias */}
      <div className="bg-gradient-to-r from-red-900/50 to-orange-900/50 border border-red-500/30 rounded-xl p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-red-600 rounded-xl">
              <Zap className="w-8 h-8 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">🔥 Gerar Posts Automáticos</h2>
              <p className="text-gray-300">
                Pega as últimas notícias do Brain e cria posts prontos para você postar
              </p>
            </div>
          </div>
          
          <button
            onClick={autoGenerateFromNews}
            disabled={autoGenerating}
            className="px-6 py-3 bg-red-600 hover:bg-red-500 disabled:bg-red-800 rounded-xl text-white font-bold flex items-center gap-2 transition-all transform hover:scale-105"
          >
            {autoGenerating ? (
              <>
                <RefreshCw className="w-5 h-5 animate-spin" />
                Gerando...
              </>
            ) : (
              <>
                <Sparkles className="w-5 h-5" />
                Gerar das Notícias
              </>
            )}
          </button>
        </div>
        
        <div className="mt-4 p-3 bg-black/30 rounded-lg text-sm text-gray-300">
          <strong>Como funciona:</strong> O Brain busca as últimas notícias → Sistema cria imagem com branding Virtus → Você baixa e posta no Instagram!
        </div>
      </div>

      {/* Quick Actions - Geração Manual */}
      <div>
        <h3 className="text-gray-400 text-sm font-medium mb-3">Geração Manual</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <button
          onClick={() => setShowModal('market_alert')}
          disabled={generating}
          className="p-4 bg-gradient-to-r from-green-600 to-green-700 hover:from-green-500 hover:to-green-600 rounded-xl text-white flex flex-col items-center gap-2 transition-all"
        >
          <TrendingUp className="w-6 h-6" />
          <span className="font-medium">Alerta de Mercado</span>
        </button>
        
        <button
          onClick={() => setShowModal('news')}
          disabled={generating}
          className="p-4 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-500 hover:to-blue-600 rounded-xl text-white flex flex-col items-center gap-2 transition-all"
        >
          <Newspaper className="w-6 h-6" />
          <span className="font-medium">Post de Notícia</span>
        </button>
        
        <button
          onClick={() => generateTip('trading_tip')}
          disabled={generating}
          className="p-4 bg-gradient-to-r from-yellow-600 to-yellow-700 hover:from-yellow-500 hover:to-yellow-600 rounded-xl text-white flex flex-col items-center gap-2 transition-all"
        >
          <Lightbulb className="w-6 h-6" />
          <span className="font-medium">Dica de Trading</span>
        </button>
        
        <button
          onClick={() => generateTip('educational')}
          disabled={generating}
          className="p-4 bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-500 hover:to-purple-600 rounded-xl text-white flex flex-col items-center gap-2 transition-all"
        >
          <BookOpen className="w-6 h-6" />
          <span className="font-medium">Educacional</span>
        </button>
        </div>
      </div>

      {/* Loading */}
      {generating && (
        <div className="flex items-center justify-center py-4">
          <RefreshCw className="w-6 h-6 text-red-500 animate-spin" />
          <span className="ml-2 text-white">Gerando post...</span>
        </div>
      )}

      {/* Posts Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          <div className="col-span-full text-center py-12 text-gray-400">
            Carregando...
          </div>
        ) : posts.length === 0 ? (
          <div className="col-span-full text-center py-12 text-gray-400">
            <ImageIcon className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>Nenhum post gerado ainda.</p>
            <p className="text-sm">Use os botões acima para criar posts!</p>
          </div>
        ) : (
          posts.map((post) => (
            <div
              key={post.id}
              className={`bg-gray-800 rounded-xl overflow-hidden border ${
                post.posted ? 'border-green-500/30' : 'border-gray-700'
              }`}
            >
              {/* Image Preview */}
              <div 
                className="aspect-square bg-gray-900 cursor-pointer relative group"
                onClick={() => setSelectedPost(post)}
              >
                <img
                  src={socialService.getImageUrl(post.image_file)}
                  alt={post.title}
                  className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                  <span className="text-white">Clique para ampliar</span>
                </div>
                
                {post.posted && (
                  <div className="absolute top-2 right-2 bg-green-500 text-white px-2 py-1 rounded text-xs flex items-center gap-1">
                    <Check className="w-3 h-3" />
                    Postado
                  </div>
                )}
              </div>
              
              {/* Info */}
              <div className="p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {getTypeIcon(post.type)}
                    <span className="text-sm text-gray-400">{getTypeLabel(post.type)}</span>
                  </div>
                  {post.trend && getTrendIcon(post.trend)}
                </div>
                
                <h3 className="text-white font-medium line-clamp-2">{post.title}</h3>
                
                {post.symbol && (
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-gray-400">Símbolo:</span>
                    <span className="text-white font-mono">{post.symbol}</span>
                    {post.price && (
                      <span className="text-gray-400">${post.price.toLocaleString()}</span>
                    )}
                  </div>
                )}
                
                <div className="text-xs text-gray-500">
                  {new Date(post.created_at).toLocaleString('pt-BR')}
                </div>
                
                {/* Actions */}
                <div className="flex gap-2 pt-2 border-t border-gray-700">
                  <button
                    onClick={() => downloadImage(post)}
                    className="flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-white text-sm flex items-center justify-center gap-1"
                  >
                    <Download className="w-4 h-4" />
                    Baixar
                  </button>
                  
                  <button
                    onClick={() => copyCaption(post)}
                    className="flex-1 px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-white text-sm flex items-center justify-center gap-1"
                  >
                    {copiedId === post.id ? (
                      <>
                        <Check className="w-4 h-4 text-green-500" />
                        Copiado!
                      </>
                    ) : (
                      <>
                        <Copy className="w-4 h-4" />
                        Legenda
                      </>
                    )}
                  </button>
                  
                  {!post.posted ? (
                    <button
                      onClick={() => markAsPosted(post)}
                      className="px-3 py-2 bg-green-600 hover:bg-green-500 rounded-lg text-white text-sm"
                      title="Marcar como postado"
                    >
                      <Check className="w-4 h-4" />
                    </button>
                  ) : (
                    <button
                      onClick={() => deletePost(post.id)}
                      className="px-3 py-2 bg-red-600/20 hover:bg-red-600 rounded-lg text-red-400 hover:text-white text-sm"
                      title="Excluir"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Modal: Market Alert */}
      {showModal === 'market_alert' && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-white">Alerta de Mercado</h2>
              <button onClick={() => setShowModal(null)} className="text-gray-400 hover:text-white">
                <X className="w-6 h-6" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Símbolo</label>
                <select
                  value={alertForm.symbol}
                  onChange={(e) => setAlertForm({ ...alertForm, symbol: e.target.value })}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                >
                  <option value="XAUUSD">XAUUSD (Ouro)</option>
                  <option value="EURUSD">EURUSD</option>
                  <option value="GBPUSD">GBPUSD</option>
                  <option value="USDJPY">USDJPY</option>
                  <option value="BTCUSD">BTCUSD</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm text-gray-400 mb-1">Tendência</label>
                <div className="flex gap-2">
                  {['bullish', 'neutral', 'bearish'].map((t) => (
                    <button
                      key={t}
                      onClick={() => setAlertForm({ ...alertForm, trend: t as any })}
                      className={`flex-1 py-2 rounded-lg border ${
                        alertForm.trend === t
                          ? t === 'bullish'
                            ? 'bg-green-600 border-green-500'
                            : t === 'bearish'
                            ? 'bg-red-600 border-red-500'
                            : 'bg-gray-600 border-gray-500'
                          : 'bg-gray-700 border-gray-600'
                      } text-white`}
                    >
                      {t === 'bullish' ? '📈 Alta' : t === 'bearish' ? '📉 Baixa' : '➡️ Neutro'}
                    </button>
                  ))}
                </div>
              </div>
              
              <div>
                <label className="block text-sm text-gray-400 mb-1">Preço Atual</label>
                <input
                  type="number"
                  step="0.01"
                  value={alertForm.price}
                  onChange={(e) => setAlertForm({ ...alertForm, price: parseFloat(e.target.value) })}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                  placeholder="Ex: 2650.50"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Suporte (opcional)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={alertForm.support || ''}
                    onChange={(e) => setAlertForm({ ...alertForm, support: parseFloat(e.target.value) || undefined })}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Resistência (opcional)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={alertForm.resistance || ''}
                    onChange={(e) => setAlertForm({ ...alertForm, resistance: parseFloat(e.target.value) || undefined })}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                  />
                </div>
              </div>
            </div>
            
            <div className="flex gap-2 pt-4">
              <button
                onClick={() => setShowModal(null)}
                className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-white"
              >
                Cancelar
              </button>
              <button
                onClick={generateMarketAlert}
                disabled={generating || !alertForm.price}
                className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-500 rounded-lg text-white disabled:opacity-50"
              >
                {generating ? 'Gerando...' : 'Gerar Post'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: News */}
      {showModal === 'news' && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-white">Post de Notícia</h2>
              <button onClick={() => setShowModal(null)} className="text-gray-400 hover:text-white">
                <X className="w-6 h-6" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Título da Notícia</label>
                <input
                  type="text"
                  value={newsForm.title}
                  onChange={(e) => setNewsForm({ ...newsForm, title: e.target.value })}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                  placeholder="Ex: Fed mantém taxa de juros"
                />
              </div>
              
              <div>
                <label className="block text-sm text-gray-400 mb-1">Resumo</label>
                <textarea
                  value={newsForm.summary}
                  onChange={(e) => setNewsForm({ ...newsForm, summary: e.target.value })}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white h-24 resize-none"
                  placeholder="Resumo da notícia..."
                />
              </div>
              
              <div>
                <label className="block text-sm text-gray-400 mb-1">Sentimento</label>
                <div className="flex gap-2">
                  {['bullish', 'neutral', 'bearish'].map((s) => (
                    <button
                      key={s}
                      onClick={() => setNewsForm({ ...newsForm, sentiment: s })}
                      className={`flex-1 py-2 rounded-lg border ${
                        newsForm.sentiment === s
                          ? s === 'bullish'
                            ? 'bg-green-600 border-green-500'
                            : s === 'bearish'
                            ? 'bg-red-600 border-red-500'
                            : 'bg-gray-600 border-gray-500'
                          : 'bg-gray-700 border-gray-600'
                      } text-white`}
                    >
                      {s === 'bullish' ? '💚 Positivo' : s === 'bearish' ? '❤️ Negativo' : '⚪ Neutro'}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            
            <div className="flex gap-2 pt-4">
              <button
                onClick={() => setShowModal(null)}
                className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-white"
              >
                Cancelar
              </button>
              <button
                onClick={generateNews}
                disabled={generating || !newsForm.title || !newsForm.summary}
                className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-500 rounded-lg text-white disabled:opacity-50"
              >
                {generating ? 'Gerando...' : 'Gerar Post'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Image Preview */}
      {selectedPost && (
        <div 
          className="fixed inset-0 bg-black/90 flex items-center justify-center z-50 p-4"
          onClick={() => setSelectedPost(null)}
        >
          <div className="relative max-w-2xl w-full" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => setSelectedPost(null)}
              className="absolute -top-12 right-0 text-white hover:text-gray-300"
            >
              <X className="w-8 h-8" />
            </button>
            
            <img
              src={socialService.getImageUrl(selectedPost.image_file)}
              alt={selectedPost.title}
              className="w-full rounded-xl"
            />
            
            <div className="mt-4 flex gap-2">
              <button
                onClick={() => downloadImage(selectedPost)}
                className="flex-1 px-4 py-3 bg-blue-600 hover:bg-blue-500 rounded-lg text-white flex items-center justify-center gap-2"
              >
                <Download className="w-5 h-5" />
                Baixar Imagem
              </button>
              <button
                onClick={() => copyCaption(selectedPost)}
                className="flex-1 px-4 py-3 bg-gray-700 hover:bg-gray-600 rounded-lg text-white flex items-center justify-center gap-2"
              >
                <Copy className="w-5 h-5" />
                Copiar Legenda
              </button>
            </div>
            
            <div className="mt-4 bg-gray-800 rounded-lg p-4 max-h-48 overflow-y-auto">
              <p className="text-gray-300 text-sm whitespace-pre-wrap">{selectedPost.caption}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SocialMedia;
