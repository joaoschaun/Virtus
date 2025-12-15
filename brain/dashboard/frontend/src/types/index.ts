/**
 * VIRTUS Trading System - Type Definitions
 * =========================================
 * Complete TypeScript type definitions for the trading dashboard
 */

// =============================================================================
// AUTHENTICATION
// =============================================================================

export interface User {
  id: number;
  username: string;
  email: string;
  role: 'admin' | 'trader' | 'viewer';
  created_at: string;
  last_login?: string;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface TokenPayload {
  sub: string;
  exp: number;
  iat: number;
  role: string;
}

// =============================================================================
// ACCOUNT & METRICS
// =============================================================================

export interface AccountInfo {
  balance: number;
  equity: number;
  margin: number;
  free_margin: number;
  margin_level: number;
  profit: number;
  currency: string;
}

export interface DashboardMetrics {
  total_trades: number;
  win_rate: number;
  profit_factor: number;
  roi: number;
  max_drawdown: number;
  sharpe_ratio: number;
  average_win: number;
  average_loss: number;
  expectancy: number;
}

export interface TodayStats {
  trades: number;
  profit: number;
  wins: number;
  losses: number;
  volume: number;
}

export interface DashboardOverview {
  account: AccountInfo;
  metrics: DashboardMetrics;
  today: TodayStats;
}

export interface EquityPoint {
  timestamp: string;
  equity: number;
  balance?: number;
  profit?: number;
}

// =============================================================================
// BOTS
// =============================================================================

export type BotStatus = 'running' | 'stopped' | 'paused' | 'error';

export interface Bot {
  id: string;
  name: string;
  symbol: string;
  status: BotStatus;
  profit_today: number;
  profit_total: number;
  trades_today: number;
  trades_total: number;
  win_rate: number;
  uptime: string;
  last_trade?: string;
  strategies: string[];
  health: BotHealth;
}

export interface BotHealth {
  status: 'healthy' | 'warning' | 'critical';
  cpu_usage: number;
  memory_usage: number;
  last_heartbeat: string;
  errors_count: number;
}

export interface BotConfig {
  max_trades_per_day: number;
  max_lot_size: number;
  min_lot_size: number;
  stop_loss_pips: number;
  take_profit_pips: number;
  use_trailing_stop: boolean;
  trailing_stop_distance: number;
  risk_per_trade: number;
  max_spread: number;
  slippage_tolerance: number;
  magic_number: number;
}

export interface BotControlRequest {
  action: 'start' | 'stop' | 'pause' | 'restart';
}

export interface BotControlResponse {
  success: boolean;
  bot_id: string;
  new_status: BotStatus;
  message: string;
}

// =============================================================================
// STRATEGIES
// =============================================================================

export interface Strategy {
  name: string;
  display_name: string;
  description?: string;
  enabled: boolean;
  symbols: string[];
  win_rate: number;
  profit: number;
  trades: number;
  setups: Setup[];
}

export interface Setup {
  name: string;
  enabled: boolean;
  win_rate: number;
  profit: number;
  trades: number;
}

export interface SymbolConfig {
  symbol: string;
  enabled: boolean;
  strategies: string[];
  profit: number;
  trades: number;
  win_rate: number;
}

// =============================================================================
// POSITIONS & ORDERS
// =============================================================================

export type PositionType = 'buy' | 'sell';
export type OrderType = 'buy_limit' | 'sell_limit' | 'buy_stop' | 'sell_stop';

export interface Position {
  ticket: number;
  symbol: string;
  type: PositionType;
  volume: number;
  open_price: number;
  current_price: number;
  sl: number;
  tp: number;
  profit: number;
  swap: number;
  commission: number;
  open_time: string;
  magic: number;
  comment?: string;
  strategy?: string;
  setup?: string;
}

export interface Order {
  ticket: number;
  symbol: string;
  type: OrderType;
  volume: number;
  price: number;
  sl: number;
  tp: number;
  created_time: string;
  expiration?: string;
  magic: number;
  comment?: string;
}

export interface ClosePositionResponse {
  success: boolean;
  ticket: number;
  close_price: number;
  profit: number;
  message: string;
}

export interface CancelOrderResponse {
  success: boolean;
  ticket: number;
  message: string;
}

// =============================================================================
// TRADES
// =============================================================================

export interface Trade {
  ticket: number;
  symbol: string;
  type: PositionType;
  volume: number;
  open_price: number;
  close_price: number;
  sl: number;
  tp: number;
  profit: number;
  swap: number;
  commission: number;
  open_time: string;
  close_time: string;
  duration_minutes: number;
  magic: number;
  comment?: string;
  strategy?: string;
  setup?: string;
  result: 'win' | 'loss' | 'breakeven';
}

export interface TradesResponse {
  trades: Trade[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface TradesFilter {
  symbol?: string;
  strategy?: string;
  setup?: string;
  result?: 'win' | 'loss' | 'breakeven';
  start_date?: string;
  end_date?: string;
  page?: number;
  page_size?: number;
}

export interface TradeStats {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_profit: number;
  total_loss: number;
  net_profit: number;
  profit_factor: number;
  average_win: number;
  average_loss: number;
  largest_win: number;
  largest_loss: number;
  average_trade_duration: string;
  best_day: { date: string; profit: number };
  worst_day: { date: string; profit: number };
  consecutive_wins: number;
  consecutive_losses: number;
}

// =============================================================================
// ANALYSIS
// =============================================================================

export interface HourlyPerformance {
  hour: number;
  trades: number;
  profit: number;
  win_rate: number;
  volume: number;
}

export interface WeekdayPerformance {
  day: string;
  trades: number;
  profit: number;
  win_rate: number;
  volume: number;
}

export interface AttributionItem {
  name: string;
  trades: number;
  profit: number;
  contribution: number;
  win_rate: number;
}

export interface PerformanceAnalysis {
  hourly: HourlyPerformance[];
  weekday: WeekdayPerformance[];
}

export interface AttributionAnalysis {
  by_strategy: AttributionItem[];
  by_setup: AttributionItem[];
  by_symbol: AttributionItem[];
}

// =============================================================================
// SETTINGS
// =============================================================================

export interface RiskSettings {
  max_daily_loss: number;
  max_daily_loss_percent: number;
  max_drawdown: number;
  max_drawdown_percent: number;
  max_position_size: number;
  max_concurrent_trades: number;
  risk_per_trade: number;
}

export interface TradingSettings {
  trading_hours_start: string;
  trading_hours_end: string;
  allowed_days: string[];
  default_stop_loss: number;
  default_take_profit: number;
  use_trailing_stop: boolean;
  trailing_stop_distance: number;
  partial_close_enabled: boolean;
  partial_close_percent: number;
  breakeven_enabled: boolean;
  breakeven_trigger: number;
}

export interface NotificationSettings {
  telegram_enabled: boolean;
  email_enabled: boolean;
  notify_on_trade: boolean;
  notify_on_daily_summary: boolean;
  notify_on_error: boolean;
  notify_on_drawdown: boolean;
  drawdown_alert_threshold: number;
}

export interface SystemSettings {
  auto_restart: boolean;
  log_level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
  data_retention_days: number;
  backup_enabled: boolean;
  backup_frequency: 'daily' | 'weekly';
}

export interface AllSettings {
  risk: RiskSettings;
  trading: TradingSettings;
  notifications: NotificationSettings;
  system: SystemSettings;
}

// =============================================================================
// MT5 INTEGRATION
// =============================================================================

export interface MT5Status {
  connected: boolean;
  account: number;
  server: string;
  company: string;
  ping_ms: number;
  trade_allowed: boolean;
  expert_allowed: boolean;
}

export interface MT5ConnectRequest {
  account: number;
  password: string;
  server: string;
}

export interface MT5SyncResponse {
  success: boolean;
  synced_trades: number;
  synced_positions: number;
  last_sync: string;
}

// =============================================================================
// SYSTEM
// =============================================================================

export interface ComponentStatus {
  database: 'healthy' | 'degraded' | 'unhealthy';
  mt5: 'healthy' | 'degraded' | 'unhealthy';
  redis: 'healthy' | 'degraded' | 'unhealthy';
  telegram: 'healthy' | 'degraded' | 'unhealthy';
}

export interface SystemStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  uptime: string;
  version: string;
  components: ComponentStatus;
  memory_usage_mb: number;
  cpu_usage_percent: number;
  disk_usage_percent: number;
}

export interface LogEntry {
  timestamp: string;
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
  module: string;
  message: string;
}

// =============================================================================
// WEBSOCKET
// =============================================================================

export type WSMessageType = 
  | 'auth'
  | 'auth_success'
  | 'auth_error'
  | 'subscribe'
  | 'unsubscribe'
  | 'subscribed'
  | 'unsubscribed'
  | 'metrics'
  | 'position_update'
  | 'order_update'
  | 'trade_closed'
  | 'alert'
  | 'error'
  | 'ping'
  | 'pong';

export type WSChannel = 'metrics' | 'positions' | 'orders' | 'alerts';

export interface WSMessage {
  type: WSMessageType;
  channel?: WSChannel;
  data?: unknown;
  token?: string;
  timestamp?: string;
}

export interface WSMetricsData {
  balance: number;
  equity: number;
  profit: number;
  open_positions: number;
  pending_orders: number;
  timestamp: string;
}

export interface WSPositionUpdate {
  action: 'opened' | 'closed' | 'modified';
  position: Position;
}

export interface WSOrderUpdate {
  action: 'created' | 'triggered' | 'cancelled';
  order: Order;
}

export interface WSAlert {
  severity: 'info' | 'warning' | 'error' | 'critical';
  message: string;
  timestamp: string;
}

// =============================================================================
// API RESPONSES
// =============================================================================

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ErrorResponse {
  detail: string;
  status_code?: number;
}

// =============================================================================
// UTILITY TYPES
// =============================================================================

export type Currency = 'USD' | 'EUR' | 'GBP' | 'BRL';

export type TimeFrame = 
  | 'M1' | 'M5' | 'M15' | 'M30' 
  | 'H1' | 'H4' 
  | 'D1' | 'W1' | 'MN1';

export type Symbol = 'EURUSD' | 'GBPUSD' | 'XAUUSD' | string;

export interface DateRange {
  start: Date | string;
  end: Date | string;
}

export interface ChartDataPoint {
  name: string;
  value: number;
  [key: string]: string | number;
}
