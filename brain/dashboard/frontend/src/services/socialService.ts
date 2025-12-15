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

  // Imagem
  getImageUrl: (filename: string) => {
    return `${api.defaults.baseURL}/api/social/image/${filename}`;
  },

  getDownloadUrl: (filename: string) => {
    return `${api.defaults.baseURL}/api/social/download/${filename}`;
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
};
