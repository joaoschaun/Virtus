import React, { useState, useEffect, useMemo } from 'react';
import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  Calendar,
  BarChart3,
  Target,
  AlertTriangle,
  CheckCircle,
  Clock,
  RefreshCw,
  Search,
  Filter,
  Star,
  ChevronRight,
  ChevronDown,
  Loader2,
  Info,
  Wallet,
  PiggyBank,
  Banknote,
  Calculator,
  Bell,
  Eye,
  ArrowRight,
  Zap,
  Shield,
  Award,
  HelpCircle,
  BookOpen,
  TrendingUp as TrendUp,
  CircleDollarSign,
  Building2,
  Percent,
  CalendarCheck,
  CalendarClock,
  Coins,
  BadgeDollarSign,
  ChartBar,
  ListChecks,
  Sparkles
} from 'lucide-react';
import { api } from '../services/api';

// API endpoint for dividend bot
const API_URL = '/api/dividend-bot';

// ==================== TYPES ====================
interface UpcomingDividend {
  ticker: string;
  company_name: string;
  sector: string;
  current_price: number;
  dividend_type: string;
  value_per_share: number;
  ex_date: string;
  payment_date: string | null;
  dividend_yield: number;
  days_to_ex: number;
  annual_yield: number;
  recommendation: string;
  score: number;
}

interface StockAnalysis {
  ticker: string;
  company_name: string;
  sector: string;
  current_price: number;
  fundamentals: {
    dividend_yield: number;
    annual_dividend: number;
    payout_ratio: number;
    dividend_consistency: number;
    pe_ratio: number;
    pb_ratio: number;
    roe: number;
    debt_to_equity: number;
    market_cap: number;
    avg_volume: number;
    volatility_30d: number;
    price_52w_high: number;
    price_52w_low: number;
  };
  dividend_history: Array<{ date: string; value: number }>;
  source: string;
  last_update: string;
}

interface CalendarEvent {
  date: string;
  ticker: string;
  company_name: string;
  event_type: string;
  dividend_value: number;
  dividend_yield: number;
  has_position: boolean;
  buy_limit_date: string | null;
  avg_historical_dividend: number | null;
  company_score: number | null;
  sector: string | null;
}

interface HealthStatus {
  status: string;
  checks: {
    storage: boolean;
    real_data_service: boolean;
    yahoo_finance: boolean;
    brapi: boolean;
    statusinvest: boolean;
  };
  message: string;
  brapi_key_configured: boolean;
}

// ==================== UTILITIES ====================
const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL'
  }).format(value);
};

const formatPercent = (value: number) => `${value.toFixed(2)}%`;

const formatDate = (dateStr: string) => new Date(dateStr).toLocaleDateString('pt-BR');

const formatDateShort = (dateStr: string) => {
  const date = new Date(dateStr);
  return date.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' });
};

const getDaysUntil = (dateStr: string): number => {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(dateStr);
  target.setHours(0, 0, 0, 0);
  return Math.ceil((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
};

const getUrgencyLevel = (days: number): { color: string; bg: string; label: string; icon: React.ReactNode } => {
  if (days < 0) return { color: 'text-gray-400', bg: 'bg-gray-500/20', label: 'Expirado', icon: null };
  if (days === 0) return { color: 'text-red-400', bg: 'bg-red-500/20', label: '🔥 HOJE!', icon: <Zap className="w-4 h-4" /> };
  if (days === 1) return { color: 'text-orange-400', bg: 'bg-orange-500/20', label: 'Amanhã', icon: <AlertTriangle className="w-4 h-4" /> };
  if (days <= 3) return { color: 'text-yellow-400', bg: 'bg-yellow-500/20', label: `${days} dias`, icon: <Clock className="w-4 h-4" /> };
  if (days <= 7) return { color: 'text-blue-400', bg: 'bg-blue-500/20', label: `${days} dias`, icon: <Calendar className="w-4 h-4" /> };
  return { color: 'text-green-400', bg: 'bg-green-500/20', label: `${days} dias`, icon: <CalendarCheck className="w-4 h-4" /> };
};

const getScoreInfo = (score: number): { color: string; bg: string; label: string } => {
  if (score >= 80) return { color: 'text-green-400', bg: 'bg-green-500/20', label: 'Excelente' };
  if (score >= 65) return { color: 'text-emerald-400', bg: 'bg-emerald-500/20', label: 'Muito Bom' };
  if (score >= 50) return { color: 'text-yellow-400', bg: 'bg-yellow-500/20', label: 'Bom' };
  if (score >= 35) return { color: 'text-orange-400', bg: 'bg-orange-500/20', label: 'Regular' };
  return { color: 'text-red-400', bg: 'bg-red-500/20', label: 'Risco' };
};

const getRecommendation = (rec: string): { color: string; bg: string; label: string; icon: React.ReactNode } => {
  switch (rec.toLowerCase()) {
    case 'buy': return { color: 'text-green-400', bg: 'bg-green-500/20', label: 'COMPRAR', icon: <TrendingUp className="w-4 h-4" /> };
    case 'wait': return { color: 'text-yellow-400', bg: 'bg-yellow-500/20', label: 'AGUARDAR', icon: <Clock className="w-4 h-4" /> };
    case 'avoid': return { color: 'text-red-400', bg: 'bg-red-500/20', label: 'EVITAR', icon: <AlertTriangle className="w-4 h-4" /> };
    default: return { color: 'text-gray-400', bg: 'bg-gray-500/20', label: rec.toUpperCase(), icon: null };
  }
};

// ==================== COMPONENTS ====================

// Header com Boas-vindas
const WelcomeHeader: React.FC<{ onRefresh: () => void; loading: boolean }> = ({ onRefresh, loading }) => (
  <div className="bg-gradient-to-r from-green-600/20 via-emerald-600/10 to-transparent rounded-2xl p-6 mb-6 border border-green-500/20">
    <div className="flex items-start justify-between">
      <div className="flex items-center gap-4">
        <div className="p-3 bg-green-500/20 rounded-xl">
          <Wallet className="w-8 h-8 text-green-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            Central de Dividendos
            <span className="text-xs px-2 py-1 bg-green-500/20 text-green-400 rounded-full">B3</span>
          </h1>
          <p className="text-virtus-text-secondary mt-1">
            Encontre as melhores oportunidades para receber dividendos
          </p>
        </div>
      </div>
      <button
        onClick={onRefresh}
        disabled={loading}
        className="flex items-center gap-2 px-4 py-2 bg-green-500/20 hover:bg-green-500/30 text-green-400 rounded-lg transition-all"
      >
        <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        Atualizar
      </button>
    </div>
  </div>
);

// Card de Estatísticas Melhorado
const StatCard: React.FC<{
  icon: React.ElementType;
  label: string;
  value: string | number;
  subtitle?: string;
  trend?: 'up' | 'down' | 'neutral';
  color?: string;
  highlight?: boolean;
}> = ({ icon: Icon, label, value, subtitle, trend, color = 'text-green-400', highlight }) => (
  <div className={`card p-5 transition-all hover:scale-[1.02] ${highlight ? 'ring-2 ring-green-500/50' : ''}`}>
    <div className="flex items-start justify-between">
      <div className="flex-1">
        <p className="text-sm text-virtus-text-muted flex items-center gap-1.5">
          {label}
          {trend === 'up' && <TrendingUp className="w-3 h-3 text-green-400" />}
          {trend === 'down' && <TrendingDown className="w-3 h-3 text-red-400" />}
        </p>
        <p className={`text-2xl font-bold mt-1.5 ${color}`}>{value}</p>
        {subtitle && (
          <p className="text-xs text-virtus-text-secondary mt-1">{subtitle}</p>
        )}
      </div>
      <div className={`p-3 rounded-xl ${color.replace('text-', 'bg-').replace('400', '500/20')}`}>
        <Icon className={`w-5 h-5 ${color}`} />
      </div>
    </div>
  </div>
);

// Explicação Educacional
const EducationalBanner: React.FC = () => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  return (
    <div className="card overflow-hidden mb-6">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-4 flex items-center justify-between hover:bg-virtus-bg-hover transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-500/20 rounded-lg">
            <BookOpen className="w-5 h-5 text-blue-400" />
          </div>
          <div className="text-left">
            <p className="font-medium text-white">Como funciona o investimento em dividendos?</p>
            <p className="text-sm text-virtus-text-secondary">Aprenda as datas importantes e como receber seus proventos</p>
          </div>
        </div>
        <ChevronDown className={`w-5 h-5 text-virtus-text-muted transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
      </button>
      
      {isExpanded && (
        <div className="p-4 pt-0 border-t border-virtus-border-primary">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
            <div className="p-4 bg-yellow-500/10 rounded-xl border border-yellow-500/20">
              <div className="flex items-center gap-2 mb-2">
                <CalendarClock className="w-5 h-5 text-yellow-400" />
                <span className="font-bold text-yellow-400">1. Data Limite de Compra</span>
              </div>
              <p className="text-sm text-virtus-text-secondary">
                É o <strong className="text-white">último dia</strong> para comprar a ação e ter direito ao dividendo. 
                Compre <strong className="text-yellow-400">até esta data</strong> para garantir o provento.
              </p>
            </div>
            
            <div className="p-4 bg-orange-500/10 rounded-xl border border-orange-500/20">
              <div className="flex items-center gap-2 mb-2">
                <Calendar className="w-5 h-5 text-orange-400" />
                <span className="font-bold text-orange-400">2. Data Ex-Dividendo</span>
              </div>
              <p className="text-sm text-virtus-text-secondary">
                A partir desta data, quem comprar <strong className="text-white">não receberá</strong> o dividendo anunciado. 
                Você pode <strong className="text-orange-400">vender depois desta data</strong> se quiser.
              </p>
            </div>
            
            <div className="p-4 bg-green-500/10 rounded-xl border border-green-500/20">
              <div className="flex items-center gap-2 mb-2">
                <Banknote className="w-5 h-5 text-green-400" />
                <span className="font-bold text-green-400">3. Data de Pagamento</span>
              </div>
              <p className="text-sm text-virtus-text-secondary">
                O dia em que o dividendo será <strong className="text-white">creditado na sua conta</strong> da corretora. 
                Geralmente ocorre <strong className="text-green-400">algumas semanas</strong> após a data ex.
              </p>
            </div>
          </div>
          
          <div className="mt-4 p-3 bg-virtus-bg-hover rounded-lg flex items-start gap-2">
            <Info className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-virtus-text-secondary">
              <strong className="text-white">Dica:</strong> O preço da ação geralmente <strong>cai</strong> no dia ex-dividendo 
              aproximadamente o valor do dividendo pago. Por isso, estratégias de "dividend capture" precisam considerar 
              este ajuste natural do mercado.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

// Card de Oportunidade de Dividendo (Redesenhado)
const OpportunityCard: React.FC<{
  dividend: UpcomingDividend;
  onAnalyze: (ticker: string) => void;
}> = ({ dividend, onAnalyze }) => {
  const daysToEx = getDaysUntil(dividend.ex_date);
  const urgency = getUrgencyLevel(daysToEx);
  const scoreInfo = getScoreInfo(dividend.score);
  const recommendation = getRecommendation(dividend.recommendation);
  const buyLimitDate = new Date(new Date(dividend.ex_date).getTime() - 86400000);
  
  return (
    <div 
      className="card overflow-hidden hover:border-green-500/50 transition-all cursor-pointer group"
      onClick={() => onAnalyze(dividend.ticker)}
    >
      {/* Header com Ticker e Score */}
      <div className="p-4 pb-3 border-b border-virtus-border-primary">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-bold text-white group-hover:text-green-400 transition-colors">
                {dividend.ticker}
              </span>
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${recommendation.bg} ${recommendation.color} flex items-center gap-1`}>
                {recommendation.icon}
                {recommendation.label}
              </span>
            </div>
            <p className="text-sm text-virtus-text-secondary mt-0.5 truncate max-w-[180px]">
              {dividend.company_name}
            </p>
            <p className="text-xs text-virtus-text-muted">{dividend.sector}</p>
          </div>
          <div className="text-right">
            <div className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg ${scoreInfo.bg}`}>
              <Award className={`w-4 h-4 ${scoreInfo.color}`} />
              <span className={`font-bold ${scoreInfo.color}`}>{dividend.score.toFixed(0)}</span>
            </div>
            <p className="text-xs text-virtus-text-muted mt-1">{scoreInfo.label}</p>
          </div>
        </div>
      </div>
      
      {/* Informações Principais */}
      <div className="p-4 space-y-3">
        {/* Preço e Dividendo */}
        <div className="grid grid-cols-2 gap-3">
          <div className="p-2 bg-virtus-bg-hover rounded-lg">
            <p className="text-xs text-virtus-text-muted">Preço Atual</p>
            <p className="font-bold text-white">{formatCurrency(dividend.current_price)}</p>
          </div>
          <div className="p-2 bg-green-500/10 rounded-lg">
            <p className="text-xs text-virtus-text-muted">Dividendo/Ação</p>
            <p className="font-bold text-green-400">{formatCurrency(dividend.value_per_share)}</p>
          </div>
        </div>
        
        {/* Yield */}
        <div className="flex items-center justify-between p-2 bg-yellow-500/10 rounded-lg">
          <div className="flex items-center gap-2">
            <Percent className="w-4 h-4 text-yellow-400" />
            <span className="text-sm text-virtus-text-secondary">Dividend Yield</span>
          </div>
          <span className="font-bold text-yellow-400">{formatPercent(dividend.dividend_yield)}</span>
        </div>
        
        {/* Datas */}
        <div className="space-y-2">
          {/* Data Limite */}
          <div className={`flex items-center justify-between p-2 rounded-lg ${urgency.bg}`}>
            <div className="flex items-center gap-2">
              {urgency.icon}
              <span className={`text-sm ${urgency.color}`}>Comprar até</span>
            </div>
            <div className="text-right">
              <span className={`font-bold ${urgency.color}`}>{formatDate(buyLimitDate.toISOString())}</span>
              <span className={`text-xs ml-2 ${urgency.color}`}>({urgency.label})</span>
            </div>
          </div>
          
          {/* Data Pagamento */}
          <div className="flex items-center justify-between p-2 bg-virtus-bg-hover rounded-lg">
            <div className="flex items-center gap-2">
              <Banknote className="w-4 h-4 text-green-400" />
              <span className="text-sm text-virtus-text-secondary">Recebe em</span>
            </div>
            <span className="font-medium text-green-400">
              {dividend.payment_date ? formatDate(dividend.payment_date) : 'A definir'}
            </span>
          </div>
        </div>
      </div>
      
      {/* Footer */}
      <div className="px-4 py-3 bg-virtus-bg-hover flex items-center justify-between">
        <span className="text-xs text-virtus-text-muted">{dividend.dividend_type.toUpperCase()}</span>
        <span className="text-xs text-virtus-accent-primary flex items-center gap-1 group-hover:gap-2 transition-all">
          Ver análise completa
          <ChevronRight className="w-4 h-4" />
        </span>
      </div>
    </div>
  );
};

// Calculadora de Investimento Melhorada
const InvestmentCalculator: React.FC<{
  dividends: UpcomingDividend[];
}> = ({ dividends }) => {
  const [amount, setAmount] = useState<number>(1000);
  const [selectedTicker, setSelectedTicker] = useState<string>('');
  
  const selectedStock = useMemo(() => {
    return dividends.find(d => d.ticker === selectedTicker);
  }, [selectedTicker, dividends]);
  
  const calculation = useMemo(() => {
    if (!selectedStock || amount <= 0 || selectedStock.current_price <= 0) return null;
    
    const shares = Math.floor(amount / selectedStock.current_price);
    const actualInvestment = shares * selectedStock.current_price;
    const dividendReceived = shares * selectedStock.value_per_share;
    const annualDividend = dividendReceived * 4; // Estimativa
    const change = amount - actualInvestment;
    const yieldOnInvestment = actualInvestment > 0 ? (dividendReceived / actualInvestment) * 100 : 0;
    
    return { shares, actualInvestment, dividendReceived, annualDividend, change, yieldOnInvestment };
  }, [selectedStock, amount]);
  
  return (
    <div className="card overflow-hidden">
      <div className="p-4 border-b border-virtus-border-primary bg-gradient-to-r from-green-500/10 to-transparent">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-green-500/20 rounded-lg">
            <Calculator className="w-5 h-5 text-green-400" />
          </div>
          <div>
            <h3 className="font-bold text-white">Calculadora de Dividendos</h3>
            <p className="text-sm text-virtus-text-secondary">Simule quanto você pode receber</p>
          </div>
        </div>
      </div>
      
      <div className="p-4 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="select-ticker" className="block text-sm text-virtus-text-muted mb-2">Selecione a Ação</label>
            <select
              id="select-ticker"
              value={selectedTicker}
              onChange={(e) => setSelectedTicker(e.target.value)}
              className="input w-full"
              title="Selecione uma ação para calcular"
            >
              <option value="">Escolha uma ação...</option>
              {dividends.map(d => (
                <option key={d.ticker} value={d.ticker}>
                  {d.ticker} - {d.company_name} (DY: {formatPercent(d.dividend_yield)})
                </option>
              ))}
            </select>
          </div>
          
          <div>
            <label htmlFor="investment-amount" className="block text-sm text-virtus-text-muted mb-2">Valor a Investir (R$)</label>
            <input
              id="investment-amount"
              type="number"
              value={amount}
              onChange={(e) => setAmount(Number(e.target.value))}
              className="input w-full text-lg font-bold"
              min={0}
              step={100}
              placeholder="1000"
              title="Valor a investir em reais"
            />
          </div>
        </div>
        
        {selectedStock && calculation && (
          <>
            {/* Info da Ação */}
            <div className="p-4 bg-virtus-bg-hover rounded-xl">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <span className="text-xl font-bold text-green-400">{selectedStock.ticker}</span>
                  <p className="text-sm text-virtus-text-secondary">{selectedStock.company_name}</p>
                </div>
                <div className="text-right">
                  <p className="text-xl font-bold text-white">{formatCurrency(selectedStock.current_price)}</p>
                  <p className="text-xs text-virtus-text-muted">Preço atual</p>
                </div>
              </div>
              
              <div className="grid grid-cols-3 gap-3">
                <div className="text-center p-2 bg-virtus-bg-card rounded-lg">
                  <p className="text-lg font-bold text-green-400">{formatCurrency(selectedStock.value_per_share)}</p>
                  <p className="text-xs text-virtus-text-muted">Dividendo/Ação</p>
                </div>
                <div className="text-center p-2 bg-virtus-bg-card rounded-lg">
                  <p className="text-lg font-bold text-yellow-400">{formatPercent(selectedStock.dividend_yield)}</p>
                  <p className="text-xs text-virtus-text-muted">DY Próximo</p>
                </div>
                <div className="text-center p-2 bg-virtus-bg-card rounded-lg">
                  <p className="text-lg font-bold text-purple-400">{formatPercent(selectedStock.annual_yield)}</p>
                  <p className="text-xs text-virtus-text-muted">DY Anual (est.)</p>
                </div>
              </div>
            </div>
            
            {/* Resultado */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="p-3 bg-blue-500/10 rounded-xl text-center border border-blue-500/20">
                <p className="text-2xl font-bold text-blue-400">{calculation.shares}</p>
                <p className="text-xs text-virtus-text-muted">Ações para comprar</p>
              </div>
              <div className="p-3 bg-virtus-bg-hover rounded-xl text-center">
                <p className="text-2xl font-bold text-white">{formatCurrency(calculation.actualInvestment)}</p>
                <p className="text-xs text-virtus-text-muted">Investimento real</p>
                {calculation.change > 0 && (
                  <p className="text-xs text-yellow-400 mt-1">Sobra: {formatCurrency(calculation.change)}</p>
                )}
              </div>
              <div className="p-3 bg-green-500/10 rounded-xl text-center border border-green-500/20">
                <p className="text-2xl font-bold text-green-400">{formatCurrency(calculation.dividendReceived)}</p>
                <p className="text-xs text-virtus-text-muted">Próximo dividendo</p>
              </div>
              <div className="p-3 bg-purple-500/10 rounded-xl text-center border border-purple-500/20">
                <p className="text-2xl font-bold text-purple-400">{formatCurrency(calculation.annualDividend)}</p>
                <p className="text-xs text-virtus-text-muted">Estimativa anual</p>
                <p className="text-xs text-purple-400 mt-1">~{formatCurrency(calculation.annualDividend / 12)}/mês</p>
              </div>
            </div>
            
            {/* Resumo */}
            <div className="p-4 bg-gradient-to-r from-green-500/10 to-purple-500/10 rounded-xl border border-green-500/20">
              <div className="flex items-start gap-3">
                <Sparkles className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-virtus-text-secondary">
                  <p className="mb-2">
                    Investindo <strong className="text-white">{formatCurrency(amount)}</strong> em <strong className="text-green-400">{selectedStock.ticker}</strong>:
                  </p>
                  <ul className="space-y-1">
                    <li>→ Compra <strong className="text-white">{calculation.shares} ações</strong> a ~{formatCurrency(selectedStock.current_price)} cada</li>
                    <li>→ Recebe <strong className="text-green-400">{formatCurrency(calculation.dividendReceived)}</strong> no próximo pagamento</li>
                    <li>→ Estimativa de <strong className="text-purple-400">{formatCurrency(calculation.annualDividend)}</strong> por ano</li>
                    <li>→ Yield de <strong className="text-yellow-400">{calculation.yieldOnInvestment.toFixed(2)}%</strong> sobre o investimento</li>
                  </ul>
                </div>
              </div>
            </div>
          </>
        )}
        
        {!selectedTicker && (
          <div className="py-8 text-center text-virtus-text-muted">
            <Calculator className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>Selecione uma ação para simular o investimento</p>
          </div>
        )}
      </div>
    </div>
  );
};

// Tabela de Calendário Melhorada
const CalendarTable: React.FC<{
  events: CalendarEvent[];
  allEvents: CalendarEvent[];
  onAnalyze: (ticker: string) => void;
}> = ({ events, allEvents, onAnalyze }) => {
  return (
    <div className="space-y-4">
      {/* Tabela */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-virtus-bg-hover">
              <tr>
                <th className="text-left p-4 text-sm font-medium text-virtus-text-muted">Ação</th>
                <th className="text-left p-4 text-sm font-medium text-virtus-text-muted">Empresa</th>
                <th className="text-center p-4">
                  <div className="flex flex-col items-center">
                    <span className="text-sm font-medium text-yellow-400">🛒 Comprar até</span>
                    <span className="text-xs text-virtus-text-muted">(Data limite)</span>
                  </div>
                </th>
                <th className="text-center p-4">
                  <div className="flex flex-col items-center">
                    <span className="text-sm font-medium text-green-400">💰 Pagamento</span>
                    <span className="text-xs text-virtus-text-muted">(Recebimento)</span>
                  </div>
                </th>
                <th className="text-right p-4 text-sm font-medium text-virtus-text-muted">Dividendo</th>
                <th className="text-right p-4 text-sm font-medium text-virtus-text-muted">DY</th>
                <th className="text-center p-4 text-sm font-medium text-virtus-text-muted">Nota</th>
                <th className="text-center p-4 text-sm font-medium text-virtus-text-muted">Ação</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-virtus-border-primary">
              {events.map((event, idx) => {
                const paymentEvent = allEvents.find(
                  e => e.ticker === event.ticker && e.event_type === 'payment_date'
                );
                const daysToLimit = event.buy_limit_date ? getDaysUntil(event.buy_limit_date) : 999;
                const urgency = getUrgencyLevel(daysToLimit);
                const scoreInfo = event.company_score ? getScoreInfo(event.company_score) : null;
                
                return (
                  <tr key={idx} className={`hover:bg-virtus-bg-hover transition-colors ${event.has_position ? 'bg-green-500/5' : ''}`}>
                    <td className="p-4">
                      <button 
                        onClick={() => onAnalyze(event.ticker)}
                        className="font-bold text-virtus-accent-primary hover:underline text-lg"
                      >
                        {event.ticker}
                      </button>
                      {event.has_position && (
                        <span className="ml-2 text-xs bg-green-500/20 text-green-400 px-1.5 py-0.5 rounded">
                          Na carteira
                        </span>
                      )}
                    </td>
                    <td className="p-4">
                      <div className="text-virtus-text-secondary">{event.company_name}</div>
                      {event.sector && (
                        <div className="text-xs text-virtus-text-muted">{event.sector}</div>
                      )}
                    </td>
                    <td className="p-4 text-center">
                      {event.buy_limit_date ? (
                        <div className="inline-flex flex-col items-center">
                          <span className={`font-bold px-3 py-1 rounded-lg ${urgency.bg} ${urgency.color}`}>
                            {formatDate(event.buy_limit_date)}
                          </span>
                          <span className={`text-xs mt-1 flex items-center gap-1 ${urgency.color}`}>
                            {urgency.icon}
                            {urgency.label}
                          </span>
                        </div>
                      ) : (
                        <span className="text-virtus-text-muted">-</span>
                      )}
                    </td>
                    <td className="p-4 text-center">
                      {paymentEvent ? (
                        <span className="font-medium text-green-400 bg-green-500/10 px-3 py-1 rounded-lg">
                          {formatDate(paymentEvent.date)}
                        </span>
                      ) : (
                        <span className="text-virtus-text-muted">A definir</span>
                      )}
                    </td>
                    <td className="p-4 text-right">
                      <span className="font-bold text-green-400">{formatCurrency(event.dividend_value)}</span>
                    </td>
                    <td className="p-4 text-right">
                      <span className="font-medium text-yellow-400">{formatPercent(event.dividend_yield)}</span>
                    </td>
                    <td className="p-4 text-center">
                      {scoreInfo ? (
                        <span className={`px-2 py-1 rounded-lg text-sm font-bold ${scoreInfo.bg} ${scoreInfo.color}`}>
                          {event.company_score?.toFixed(0)}
                        </span>
                      ) : (
                        <span className="text-virtus-text-muted">-</span>
                      )}
                    </td>
                    <td className="p-4 text-center">
                      <button
                        onClick={() => onAnalyze(event.ticker)}
                        className="p-2 hover:bg-virtus-bg-hover rounded-lg transition-colors"
                        title={`Ver análise de ${event.ticker}`}
                        aria-label={`Ver análise completa de ${event.ticker}`}
                      >
                        <Eye className="w-4 h-4 text-virtus-text-secondary" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        
        {/* Legenda */}
        <div className="p-4 bg-virtus-bg-hover border-t border-virtus-border-primary">
          <div className="flex flex-wrap items-center gap-4 text-xs">
            <span className="text-virtus-text-muted">Notas:</span>
            <div className="flex items-center gap-1.5">
              <span className="px-2 py-0.5 rounded bg-green-500/20 text-green-400 font-bold">80+</span>
              <span className="text-virtus-text-muted">Excelente</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="px-2 py-0.5 rounded bg-yellow-500/20 text-yellow-400 font-bold">50-79</span>
              <span className="text-virtus-text-muted">Bom</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="px-2 py-0.5 rounded bg-red-500/20 text-red-400 font-bold">&lt;50</span>
              <span className="text-virtus-text-muted">Atenção</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Análise de Ação (Modal-like)
const StockAnalysisView: React.FC<{
  stock: StockAnalysis | null;
  loading: boolean;
  searchTicker: string;
  onSearch: (ticker: string) => void;
  onSearchChange: (value: string) => void;
}> = ({ stock, loading, searchTicker, onSearch, onSearchChange }) => (
  <div className="space-y-6">
    {/* Busca */}
    <div className="flex gap-4">
      <div className="flex-1 relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-virtus-text-muted" />
        <input
          type="text"
          placeholder="Digite o código da ação (ex: PETR4, VALE3)..."
          value={searchTicker}
          onChange={(e) => onSearchChange(e.target.value.toUpperCase())}
          onKeyDown={(e) => e.key === 'Enter' && searchTicker && onSearch(searchTicker)}
          className="input pl-10 w-full text-lg"
        />
      </div>
      <button
        onClick={() => searchTicker && onSearch(searchTicker)}
        disabled={!searchTicker || loading}
        className="btn-primary px-6"
      >
        {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Analisar'}
      </button>
    </div>
    
    {/* Resultado */}
    {stock && (
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Info Principal */}
        <div className="lg:col-span-2 space-y-6">
          <div className="card p-6">
            <div className="flex items-start justify-between mb-6">
              <div>
                <div className="flex items-center gap-3">
                  <h2 className="text-3xl font-bold text-white">{stock.ticker}</h2>
                  <span className="px-2 py-1 bg-virtus-bg-hover rounded text-sm text-virtus-text-secondary">
                    {stock.sector}
                  </span>
                </div>
                <p className="text-virtus-text-secondary mt-1">{stock.company_name}</p>
              </div>
              <div className="text-right">
                <p className="text-3xl font-bold text-white">{formatCurrency(stock.current_price)}</p>
                <p className="text-sm text-virtus-text-muted">Fonte: {stock.source}</p>
              </div>
            </div>
            
            {/* Indicadores */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-3 bg-green-500/10 rounded-xl">
                <p className="text-xs text-virtus-text-muted">Dividend Yield</p>
                <p className="text-xl font-bold text-green-400">
                  {formatPercent(stock.fundamentals.dividend_yield)}
                </p>
              </div>
              <div className="p-3 bg-virtus-bg-hover rounded-xl">
                <p className="text-xs text-virtus-text-muted">Payout</p>
                <p className="text-xl font-bold text-white">
                  {formatPercent(stock.fundamentals.payout_ratio)}
                </p>
              </div>
              <div className="p-3 bg-virtus-bg-hover rounded-xl">
                <p className="text-xs text-virtus-text-muted">P/L</p>
                <p className="text-xl font-bold text-white">
                  {stock.fundamentals.pe_ratio.toFixed(1)}x
                </p>
              </div>
              <div className="p-3 bg-virtus-bg-hover rounded-xl">
                <p className="text-xs text-virtus-text-muted">P/VP</p>
                <p className="text-xl font-bold text-white">
                  {stock.fundamentals.pb_ratio.toFixed(2)}x
                </p>
              </div>
              <div className="p-3 bg-yellow-500/10 rounded-xl">
                <p className="text-xs text-virtus-text-muted">ROE</p>
                <p className="text-xl font-bold text-yellow-400">
                  {formatPercent(stock.fundamentals.roe)}
                </p>
              </div>
              <div className="p-3 bg-virtus-bg-hover rounded-xl">
                <p className="text-xs text-virtus-text-muted">Dív/PL</p>
                <p className="text-xl font-bold text-white">
                  {stock.fundamentals.debt_to_equity.toFixed(1)}%
                </p>
              </div>
              <div className="p-3 bg-virtus-bg-hover rounded-xl">
                <p className="text-xs text-virtus-text-muted">Vol. 30d</p>
                <p className="text-xl font-bold text-white">
                  {stock.fundamentals.volatility_30d.toFixed(1)}%
                </p>
              </div>
              <div className="p-3 bg-blue-500/10 rounded-xl">
                <p className="text-xs text-virtus-text-muted">Consistência</p>
                <p className="text-xl font-bold text-blue-400">
                  {stock.fundamentals.dividend_consistency.toFixed(0)}%
                </p>
              </div>
            </div>
          </div>
          
          {/* Faixa de Preço */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <ChartBar className="w-5 h-5 text-virtus-accent-primary" />
              Faixa de Preço (52 semanas)
            </h3>
            <div className="relative h-8 bg-virtus-bg-hover rounded-full overflow-hidden">
              <div 
                className="absolute inset-0 bg-gradient-to-r from-red-500/30 via-yellow-500/30 to-green-500/30"
              />
              <div 
                className="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-white rounded-full border-2 border-green-400 shadow-lg z-10"
                style={{ 
                  left: `calc(${((stock.current_price - stock.fundamentals.price_52w_low) / 
                         (stock.fundamentals.price_52w_high - stock.fundamentals.price_52w_low)) * 100}% - 8px)` 
                }}
              />
            </div>
            <div className="flex justify-between mt-2 text-sm">
              <span className="text-red-400">Mín: {formatCurrency(stock.fundamentals.price_52w_low)}</span>
              <span className="text-green-400">Máx: {formatCurrency(stock.fundamentals.price_52w_high)}</span>
            </div>
          </div>
        </div>
        
        {/* Histórico de Dividendos */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <ListChecks className="w-5 h-5 text-green-400" />
            Histórico de Dividendos
          </h3>
          <div className="space-y-2">
            {stock.dividend_history.slice(0, 10).map((div, idx) => (
              <div key={idx} className="flex justify-between items-center py-2 px-3 bg-virtus-bg-hover rounded-lg">
                <span className="text-sm text-virtus-text-muted">
                  {formatDate(div.date)}
                </span>
                <span className="font-medium text-green-400">
                  {formatCurrency(div.value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    )}
    
    {!stock && !loading && (
      <div className="card p-12 text-center">
        <Search className="w-12 h-12 text-virtus-text-muted mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-white mb-2">Busque uma ação para analisar</h3>
        <p className="text-virtus-text-secondary">
          Digite o código da ação acima (ex: PETR4, VALE3, ITUB4) para ver a análise completa.
        </p>
      </div>
    )}
  </div>
);

// ==================== MAIN COMPONENT ====================
const DividendsPageV2: React.FC = () => {
  // State
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'oportunidades' | 'calendario' | 'calculadora' | 'analise'>('oportunidades');
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  
  // Data
  const [upcomingDividends, setUpcomingDividends] = useState<UpcomingDividend[]>([]);
  const [calendarEvents, setCalendarEvents] = useState<CalendarEvent[]>([]);
  const [selectedStock, setSelectedStock] = useState<StockAnalysis | null>(null);
  
  // Filters
  const [minYield, setMinYield] = useState(3);
  const [daysAhead, setDaysAhead] = useState(30);
  const [searchTicker, setSearchTicker] = useState('');
  const [sortBy, setSortBy] = useState<'score' | 'yield' | 'days'>('score');

  // Computed
  const exDateEvents = useMemo(() => 
    calendarEvents.filter(e => e.event_type === 'ex_date'), 
    [calendarEvents]
  );
  
  const sortedDividends = useMemo(() => {
    const sorted = [...upcomingDividends];
    switch (sortBy) {
      case 'score': return sorted.sort((a, b) => b.score - a.score);
      case 'yield': return sorted.sort((a, b) => b.dividend_yield - a.dividend_yield);
      case 'days': return sorted.sort((a, b) => a.days_to_ex - b.days_to_ex);
      default: return sorted;
    }
  }, [upcomingDividends, sortBy]);
  
  const stats = useMemo(() => ({
    total: upcomingDividends.length,
    buyRecommendations: upcomingDividends.filter(d => d.recommendation === 'buy').length,
    maxYield: upcomingDividends.length > 0 ? Math.max(...upcomingDividends.map(d => d.dividend_yield)) : 0,
    avgScore: upcomingDividends.length > 0 
      ? upcomingDividends.reduce((sum, d) => sum + d.score, 0) / upcomingDividends.length 
      : 0,
  }), [upcomingDividends]);

  // Load data
  useEffect(() => {
    loadAll();
  }, []);

  useEffect(() => {
    loadUpcomingDividends();
  }, [minYield, daysAhead]);

  const loadAll = () => {
    loadHealth();
    loadUpcomingDividends();
    loadCalendar();
  };

  const loadHealth = async () => {
    try {
      const { data } = await api.get(`${API_URL}/health`);
      setHealthStatus(data);
    } catch (err) {
      console.error('Erro ao verificar saúde:', err);
    }
  };

  const loadUpcomingDividends = async () => {
    setLoading(true);
    try {
      // Tenta endpoint com dados reais primeiro
      let data;
      try {
        const response = await api.get(`${API_URL}/real/upcoming`, {
          params: { days_ahead: daysAhead, min_yield: minYield }
        });
        data = response.data;
      } catch {
        // Fallback para endpoint simulado
        const response = await api.get(`${API_URL}/upcoming`, {
          params: { days_ahead: daysAhead, min_yield: minYield }
        });
        data = response.data;
      }
      setUpcomingDividends(data.dividends || []);
      setError(null);
    } catch (err) {
      setError('Erro ao carregar dividendos. Verifique se o backend está rodando.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadCalendar = async () => {
    try {
      const { data } = await api.get(`${API_URL}/calendar`, {
        params: { days_ahead: 30 }
      });
      setCalendarEvents(data.events || []);
    } catch (err) {
      console.error('Erro ao carregar calendário:', err);
    }
  };

  const analyzeStock = async (ticker: string) => {
    setLoading(true);
    try {
      let data;
      try {
        const response = await api.get(`${API_URL}/real/analyze/${ticker}`);
        data = response.data;
      } catch {
        const response = await api.get(`${API_URL}/analyze/${ticker}`);
        data = response.data;
      }
      setSelectedStock(data);
      setActiveTab('analise');
      setSearchTicker(ticker);
    } catch (err) {
      console.error('Erro ao analisar ação:', err);
    } finally {
      setLoading(false);
    }
  };

  // Tabs
  const tabs = [
    { id: 'oportunidades', label: 'Oportunidades', icon: Target, count: stats.buyRecommendations },
    { id: 'calendario', label: 'Calendário', icon: Calendar, count: exDateEvents.length },
    { id: 'calculadora', label: 'Calculadora', icon: Calculator },
    { id: 'analise', label: 'Análise', icon: BarChart3 },
  ];

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto">
      {/* Header */}
      <WelcomeHeader onRefresh={loadAll} loading={loading} />
      
      {/* Educacional */}
      <EducationalBanner />
      
      {/* Status Banner */}
      {healthStatus && !healthStatus.checks.real_data_service && (
        <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-xl flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-yellow-400">Modo de demonstração</p>
            <p className="text-sm text-virtus-text-secondary">{healthStatus.message}</p>
          </div>
        </div>
      )}
      
      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          icon={Calendar}
          label="Dividendos Próximos"
          value={stats.total}
          subtitle={`Nos próximos ${daysAhead} dias`}
          color="text-blue-400"
        />
        <StatCard
          icon={Target}
          label="Oportunidades de Compra"
          value={stats.buyRecommendations}
          subtitle="Recomendação: Comprar"
          color="text-green-400"
          highlight
        />
        <StatCard
          icon={Percent}
          label="Maior Dividend Yield"
          value={formatPercent(stats.maxYield)}
          subtitle="Melhor rendimento encontrado"
          color="text-yellow-400"
        />
        <StatCard
          icon={Award}
          label="Score Médio"
          value={stats.avgScore.toFixed(0)}
          subtitle="Qualidade das oportunidades"
          color="text-purple-400"
        />
      </div>
      
      {/* Tabs */}
      <div className="flex gap-2 border-b border-virtus-border-primary pb-4 overflow-x-auto">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl transition-all whitespace-nowrap ${
              activeTab === tab.id
                ? 'bg-green-500 text-white shadow-lg shadow-green-500/25'
                : 'text-virtus-text-secondary hover:bg-virtus-bg-hover'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
            {tab.count !== undefined && (
              <span className={`px-1.5 py-0.5 text-xs rounded-full ${
                activeTab === tab.id ? 'bg-white/20' : 'bg-virtus-bg-hover'
              }`}>
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>
      
      {/* Error */}
      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5" />
          {error}
        </div>
      )}
      
      {/* Content */}
      {activeTab === 'oportunidades' && (
        <div className="space-y-6">
          {/* Filtros */}
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-virtus-text-muted" />
              <span className="text-sm text-virtus-text-muted">Filtros:</span>
            </div>
            
            <div className="flex items-center gap-2">
              <label htmlFor="min-yield" className="text-sm text-virtus-text-secondary">DY mínimo:</label>
              <input
                id="min-yield"
                type="number"
                value={minYield}
                onChange={(e) => setMinYield(Number(e.target.value))}
                className="input w-20 text-sm"
                min={0}
                max={20}
                step={0.5}
                title="Dividend Yield mínimo"
                placeholder="3"
              />
              <span className="text-sm text-virtus-text-muted">%</span>
            </div>
            
            <div className="flex items-center gap-2">
              <label htmlFor="period-select" className="text-sm text-virtus-text-secondary">Período:</label>
              <select
                id="period-select"
                value={daysAhead}
                onChange={(e) => setDaysAhead(Number(e.target.value))}
                className="input w-28 text-sm"
                title="Período de busca"
              >
                <option value={7}>7 dias</option>
                <option value={14}>14 dias</option>
                <option value={30}>30 dias</option>
                <option value={60}>60 dias</option>
              </select>
            </div>
            
            <div className="flex items-center gap-2 ml-auto">
              <label htmlFor="sort-select" className="text-sm text-virtus-text-secondary">Ordenar:</label>
              <select
                id="sort-select"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="input w-32 text-sm"
                title="Ordenar resultados"
              >
                <option value="score">Maior Score</option>
                <option value="yield">Maior Yield</option>
                <option value="days">Mais Próximo</option>
              </select>
            </div>
          </div>
          
          {/* Grid de Oportunidades */}
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="w-8 h-8 animate-spin text-green-400" />
            </div>
          ) : sortedDividends.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {sortedDividends.map((dividend, idx) => (
                <OpportunityCard key={idx} dividend={dividend} onAnalyze={analyzeStock} />
              ))}
            </div>
          ) : (
            <div className="card p-12 text-center">
              <Target className="w-12 h-12 text-virtus-text-muted mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-white mb-2">Nenhuma oportunidade encontrada</h3>
              <p className="text-virtus-text-secondary">
                Tente ajustar o DY mínimo ou o período de busca.
              </p>
            </div>
          )}
        </div>
      )}
      
      {activeTab === 'calendario' && (
        <CalendarTable 
          events={exDateEvents} 
          allEvents={calendarEvents}
          onAnalyze={analyzeStock} 
        />
      )}
      
      {activeTab === 'calculadora' && (
        <InvestmentCalculator dividends={upcomingDividends} />
      )}
      
      {activeTab === 'analise' && (
        <StockAnalysisView 
          stock={selectedStock}
          loading={loading}
          searchTicker={searchTicker}
          onSearch={analyzeStock}
          onSearchChange={setSearchTicker}
        />
      )}
    </div>
  );
};

export default DividendsPageV2;
