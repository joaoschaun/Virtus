/**
 * VIRTUS - Serviços para Novos Módulos v3.1
 * 
 * Paper Trading, Plugins, Auditoria, Drawdown, Reports, Metrics
 */

import api from './api';

// ============================================================================
// PAPER TRADING
// ============================================================================

export interface PaperAccount {
  login: number;
  server: string;
  balance: number;
  equity: number;
  margin: number;
  free_margin: number;
  profit: number;
  leverage: number;
  currency: string;
}

export interface PaperPosition {
  ticket: number;
  symbol: string;
  type: string;
  volume: number;
  open_price: number;
  open_time: string;
  sl?: number;
  tp?: number;
  close_price?: number;
  close_time?: string;
  profit: number;
  state: string;
  comment: string;
}

export interface PaperStats {
  total_trades: number;
  wins: number;
  losses: number;
  win_rate: number;
  profit_factor: number;
  total_profit: number;
  avg_profit: number;
  max_profit: number;
  max_loss: number;
  open_positions: number;
}

export const paperTradingService = {
  getStatus: () => api.get('/paper/status'),
  start: () => api.post('/paper/start'),
  stop: () => api.post('/paper/stop'),
  getAccount: () => api.get<PaperAccount>('/paper/account'),
  getPositions: () => api.get<PaperPosition[]>('/paper/positions'),
  getHistory: (limit = 100) => api.get<PaperPosition[]>(`/paper/history?limit=${limit}`),
  getStats: () => api.get<PaperStats>('/paper/stats'),
  openTrade: (data: { symbol: string; type: string; volume: number; sl?: number; tp?: number; comment?: string }) =>
    api.post('/paper/trade', data),
  closeTrade: (ticket: number) => api.delete(`/paper/trade/${ticket}`),
  modifyTrade: (ticket: number, data: { sl?: number; tp?: number }) =>
    api.patch(`/paper/trade/${ticket}`, data),
  getPrice: (symbol: string) => api.get(`/paper/price/${symbol}`),
};

// ============================================================================
// PLUGINS / ESTRATÉGIAS
// ============================================================================

export interface PluginInfo {
  name: string;
  version: string;
  author: string;
  description: string;
  symbols: string[];
  timeframes: string[];
  enabled: boolean;
  stats: {
    signals_generated: number;
    buy_signals: number;
    sell_signals: number;
  };
}

export interface PluginConfig {
  [key: string]: any;
}

export const pluginsService = {
  getStatus: () => api.get('/plugins/status'),
  list: () => api.get<PluginInfo[]>('/plugins/'),
  get: (name: string) => api.get<PluginInfo>(`/plugins/${name}`),
  enable: (name: string) => api.post(`/plugins/${name}/enable`),
  disable: (name: string) => api.post(`/plugins/${name}/disable`),
  configure: (name: string, config: PluginConfig) =>
    api.post(`/plugins/${name}/configure`, { config }),
  reload: () => api.post('/plugins/reload'),
};

// ============================================================================
// AUDITORIA
// ============================================================================

export interface AuditLog {
  id: string;
  timestamp: string;
  category: string;
  action: string;
  user: string;
  details: any;
  severity: string;
  ip_address?: string;
}

export interface AuditStats {
  period: { start: string; end: string };
  total_events: number;
  by_category: Record<string, number>;
  by_severity: Record<string, number>;
  top_users: Array<{ user: string; count: number }>;
}

export const auditService = {
  getStatus: () => api.get('/audit/status'),
  getLogs: (params?: {
    category?: string;
    user?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
  }) => api.get<{ count: number; logs: AuditLog[] }>('/audit/logs', { params }),
  getStats: () => api.get<AuditStats>('/audit/stats'),
  getTradeLogs: (limit = 50) => api.get<{ count: number; logs: AuditLog[] }>(`/audit/trades?limit=${limit}`),
  getAuthLogs: (limit = 50) => api.get<{ count: number; logs: AuditLog[] }>(`/audit/auth?limit=${limit}`),
  getConfigLogs: (limit = 50) => api.get<{ count: number; logs: AuditLog[] }>(`/audit/config?limit=${limit}`),
  cleanup: (days = 90) => api.post(`/audit/cleanup?days=${days}`),
};

// ============================================================================
// DRAWDOWN MONITOR
// ============================================================================

export interface DrawdownState {
  current_equity: number;
  baseline_equity: number;
  peak_equity: number;
  drawdown_amount: number;
  drawdown_percent: number;
  current_level: string;
  alerts_today: number;
  max_drawdown_today: number;
  max_drawdown_session: number;
  max_drawdown_all_time: number;
  trading_paused: boolean;
}

export interface DrawdownAlert {
  timestamp: string;
  level: string;
  drawdown_percent: number;
  drawdown_amount: number;
  equity: number;
  baseline: number;
  action_taken: string;
  message: string;
}

export interface DrawdownThresholds {
  caution: number;
  warning: number;
  critical: number;
  emergency: number;
}

export const drawdownService = {
  getStatus: () => api.get<{
    available: boolean;
    running: boolean;
    state: DrawdownState;
    alert_level: string;
  }>('/drawdown/status'),
  start: () => api.post('/drawdown/start'),
  stop: () => api.post('/drawdown/stop'),
  getState: () => api.get<DrawdownState>('/drawdown/state'),
  getAlerts: (limit = 50) => api.get<{ count: number; alerts: DrawdownAlert[] }>(`/drawdown/alerts?limit=${limit}`),
  getThresholds: () => api.get<{ thresholds: any[] }>('/drawdown/thresholds'),
  updateThresholds: (config: DrawdownThresholds) => api.post('/drawdown/thresholds', config),
  resetPeak: () => api.post('/drawdown/reset-peak'),
};

// ============================================================================
// RELATÓRIOS
// ============================================================================

export interface ReportStatus {
  available: boolean;
  pdf_available: boolean;
  supported_formats: string[];
}

export const reportsService = {
  getStatus: () => api.get<ReportStatus>('/reports/status'),
  getPerformanceReport: (period: 'week' | 'month' | 'quarter' | 'year' = 'month', format: 'html' | 'pdf' = 'html') =>
    api.get(`/reports/performance?period=${period}&format=${format}`, { responseType: format === 'pdf' ? 'blob' : 'text' }),
  getTradesReport: (startDate?: string, endDate?: string) => {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    return api.get(`/reports/trades?${params.toString()}`, { responseType: 'text' });
  },
  getSummary: () => api.get('/reports/summary'),
};

// ============================================================================
// MÉTRICAS PROMETHEUS
// ============================================================================

export interface MetricsStatus {
  available: boolean;
  metrics_count: number;
  metrics: string[];
}

export const metricsService = {
  getStatus: () => api.get<MetricsStatus>('/metrics/status'),
  getMetrics: () => api.get('/metrics', { responseType: 'text' }),
};

// Export all
export default {
  paperTrading: paperTradingService,
  plugins: pluginsService,
  audit: auditService,
  drawdown: drawdownService,
  reports: reportsService,
  metrics: metricsService,
};
