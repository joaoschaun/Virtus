import { api } from './api';

export interface Post {
  id: number;
  type: string;
  title: string;
  caption: string;
  image_file: string;
  symbol?: string;
  trend?: string;
  price?: number;
  sentiment?: string;
  created_at: string;
  posted: boolean;
  posted_at?: string;
}

export interface MarketAlertRequest {
  symbol: string;
  trend: 'bullish' | 'bearish' | 'neutral';
  price: number;
  support?: number;
  resistance?: number;
}

export interface NewsPostRequest {
  title: string;
  summary: string;
  sentiment?: string;
}

export interface NewsItem {
  id: string;
  title: string;
  summary: string;
  content?: string;
  source: string;
  category: string;
  sentiment: string;
  published_at: string;
  url?: string;
  tickers?: string[];
}

export interface SelectedNewsRequest {
  title: string;
  summary: string;
  sentiment: string;
  category: string;
  tickers: string[];
  source: string;
}

export const socialService = {
  // Status
  getStatus: async () => {
    const response = await api.get('/api/social/status');
    return response.data;
  },

  // Posts
  getPosts: async (limit: number = 20) => {
    const response = await api.get(`/api/social/posts?limit=${limit}`);
    return response.data;
  },

  // Gerar posts
  generateMarketAlert: async (data: MarketAlertRequest) => {
    const response = await api.post('/api/social/generate/market-alert', data);
    return response.data;
  },

  generateNews: async (data: NewsPostRequest) => {
    const response = await api.post('/api/social/generate/news', data);
    return response.data;
  },

  generateTip: async (type: 'trading_tip' | 'educational' = 'trading_tip') => {
    const response = await api.post('/api/social/generate/tip', { type });
    return response.data;
  },

  // Imagem - URL relativa funciona com Nginx proxy
  getImageUrl: (filename: string) => {
    const baseUrl = api.defaults.baseURL || '';
    return `${baseUrl}/api/social/image/${encodeURIComponent(filename)}`;
  },

  getDownloadUrl: (filename: string) => {
    const baseUrl = api.defaults.baseURL || '';
    return `${baseUrl}/api/social/download/${encodeURIComponent(filename)}`;
  },

  // Ações
  markAsPosted: async (postId: number) => {
    const response = await api.post(`/api/social/posts/${postId}/mark-posted`);
    return response.data;
  },

  deletePost: async (postId: number) => {
    const response = await api.delete(`/api/social/posts/${postId}`);
    return response.data;
  },

  // Geração Automática - Integração com Brain
  autoGenerateFromNews: async (limit: number = 3) => {
    const response = await api.post(`/api/social/auto/generate-from-news?limit=${limit}`);
    return response.data;
  },

  autoGenerateTip: async () => {
    const response = await api.post('/api/social/auto/generate-tip');
    return response.data;
  },

  autoGenerateSummary: async () => {
    const response = await api.post('/api/social/auto/generate-summary');
    return response.data;
  },

  getPendingPosts: async () => {
    const response = await api.get('/api/social/pending');
    return response.data;
  },

  // Notícias para seleção manual
  getBrazilNews: async (limit: number = 10): Promise<{ news: NewsItem[] }> => {
    const response = await api.get(`/api/social/news/brazil?limit=${limit}`);
    return response.data;
  },

  getAllNews: async (limit: number = 15): Promise<{ news: NewsItem[] }> => {
    const response = await api.get(`/api/social/news/all?limit=${limit}`);
    return response.data;
  },

  // Gerar post de notícia selecionada
  generateFromSelectedNews: async (data: SelectedNewsRequest) => {
    const response = await api.post('/api/social/generate/from-selected-news', data);
    return response.data;
  },
};
