/**
 * VIRTUS Dashboard - Multi-Bot Service
 * =====================================
 * 
 * Serviço para gerenciar múltiplos tipos de bots
 */

import api from './api';

export interface BotType {
  id: string;
  name: string;
  description: string;
  markets: string[];
  example_symbols: string[];
  subtypes?: string[];
}

export interface Market {
  id: string;
  name: string;
  type: string;
}

export interface BotMetrics {
  bot_id: string;
  bot_type: string;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  gross_profit: number;
  gross_loss: number;
  net_profit: number;
  profit_factor: number;
  max_drawdown: number;
  current_drawdown: number;
  sharpe_ratio: number;
  daily_trades: number;
  daily_profit: number;
  daily_win_rate: number;
  last_trade_time: string | null;
  last_update: string;
}

export interface Bot {
  id: string;
  name: string;
  type: string;
  status: 'stopped' | 'starting' | 'running' | 'paused' | 'error' | 'maintenance';
  market: string;
  symbols: string[];
  strategies: string[];
  metrics: BotMetrics;
  positions: any[];
  config: any;
}

export interface AggregatedMetrics {
  total_bots: number;
  running_bots: number;
  paused_bots: number;
  stopped_bots: number;
  error_bots: number;
  total_trades: number;
  total_profit: number;
  total_win_rate: number;
  by_type: Record<string, {
    count: number;
    running: number;
    profit: number;
    trades: number;
  }>;
  by_market: Record<string, {
    count: number;
    running: number;
    profit: number;
    trades: number;
  }>;
  last_update: string;
}

export interface DashboardState {
  bots: Bot[];
  aggregated: AggregatedMetrics;
  registered_types: string[];
  summary: {
    total: number;
    running: number;
    by_type: Record<string, number>;
  };
}

export interface CreateBotRequest {
  bot_id?: string;
  name: string;
  bot_type: string;
  market: string;
  symbols: string[];
  strategies?: string[];
  max_position_size?: number;
  max_daily_loss?: number;
  max_drawdown?: number;
  risk_per_trade?: number;
  enabled?: boolean;
  auto_start?: boolean;
  extra?: Record<string, any>;
}

class MultiBotService {
  private baseUrl = '/api/bots/v2';

  /**
   * Lista tipos de bot disponíveis
   */
  async getTypes(): Promise<{ types: BotType[]; registered: string[] }> {
    const response = await api.get(`${this.baseUrl}/types`);
    return response.data;
  }

  /**
   * Lista mercados disponíveis
   */
  async getMarkets(): Promise<{ markets: Market[] }> {
    const response = await api.get(`${this.baseUrl}/markets`);
    return response.data;
  }

  /**
   * Cria um novo bot
   */
  async createBot(request: CreateBotRequest): Promise<Bot> {
    const response = await api.post(this.baseUrl, request);
    return response.data;
  }

  /**
   * Lista todos os bots
   */
  async listBots(filters?: {
    bot_type?: string;
    status?: string;
    market?: string;
  }): Promise<Bot[]> {
    const params = new URLSearchParams();
    if (filters?.bot_type) params.append('bot_type', filters.bot_type);
    if (filters?.status) params.append('status', filters.status);
    if (filters?.market) params.append('market', filters.market);
    
    const response = await api.get(`${this.baseUrl}?${params.toString()}`);
    return response.data;
  }

  /**
   * Obtém métricas agregadas
   */
  async getAggregatedMetrics(): Promise<AggregatedMetrics> {
    const response = await api.get(`${this.baseUrl}/metrics`);
    return response.data;
  }

  /**
   * Obtém estado completo do dashboard
   */
  async getDashboardState(): Promise<DashboardState> {
    const response = await api.get(`${this.baseUrl}/dashboard`);
    return response.data;
  }

  /**
   * Obtém detalhes de um bot
   */
  async getBot(botId: string): Promise<Bot> {
    const response = await api.get(`${this.baseUrl}/${botId}`);
    return response.data;
  }

  /**
   * Controla um bot
   */
  async controlBot(botId: string, action: 'start' | 'stop' | 'pause' | 'resume'): Promise<{
    success: boolean;
    bot_id: string;
    action: string;
    new_status: string;
  }> {
    const response = await api.post(`${this.baseUrl}/${botId}/control`, { action });
    return response.data;
  }

  /**
   * Atualiza configuração de um bot
   */
  async updateBotConfig(botId: string, config: Partial<CreateBotRequest>): Promise<{
    success: boolean;
    config: any;
  }> {
    const response = await api.put(`${this.baseUrl}/${botId}/config`, config);
    return response.data;
  }

  /**
   * Remove um bot
   */
  async deleteBot(botId: string): Promise<{ success: boolean; message: string }> {
    const response = await api.delete(`${this.baseUrl}/${botId}`);
    return response.data;
  }

  /**
   * Inicia múltiplos bots
   */
  async startAll(botType?: string): Promise<{
    success: boolean;
    results: Record<string, boolean>;
    started: number;
  }> {
    const params = botType ? `?bot_type=${botType}` : '';
    const response = await api.post(`${this.baseUrl}/batch/start${params}`);
    return response.data;
  }

  /**
   * Para múltiplos bots
   */
  async stopAll(botType?: string): Promise<{
    success: boolean;
    results: Record<string, boolean>;
    stopped: number;
  }> {
    const params = botType ? `?bot_type=${botType}` : '';
    const response = await api.post(`${this.baseUrl}/batch/stop${params}`);
    return response.data;
  }
}

export const multiBotService = new MultiBotService();
export default multiBotService;
