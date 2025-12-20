import { useState, useEffect } from 'react';
import { 
  TrendingUp, TrendingDown, DollarSign, Activity, 
  BarChart2, PieChart, Calendar, RefreshCw, 
  ArrowUpCircle, ArrowDownCircle, Target, AlertTriangle,
  Wallet, Clock, Award, Zap
} from 'lucide-react';

interface AccountInfo {
  login: number;
  name: string;
  server: string;
  currency: string;
  balance: number;
  equity: number;
  margin: number;
  free_margin: number;
  margin_level: number;
  profit: number;
  leverage: number;
  trade_allowed: boolean;
}

interface Metrics {
  balance: number;
  equity: number;
  profit: number;
  total_deposits: number;
  total_withdrawals: number;
  total_trades: number;
  total_profit: number;
  real_profit: number;
  avg_daily_profit: number;
  avg_trade_profit: number;
  wins: number;
  losses: number;
  win_rate: number;
  max_drawdown: number;
  max_drawdown_pct: number;
  current_drawdown: number;
  current_drawdown_pct: number;
  profit_factor: number;
  sharpe_ratio: number;
  recovery_factor: number;
  profit_today: number;
  profit_week: number;
  profit_month: number;
  profit_year: number;
  best_trade: number;
  worst_trade: number;
  best_day: number;
  worst_day: number;
  current_streak: number;
  max_win_streak: number;
  max_loss_streak: number;
}

interface Position {
  ticket: number;
  symbol: string;
  type: string;
  volume: number;
  price_open: number;
  price_current: number;
  profit: number;
  swap: number;
  time: string;
  sl: number;
  tp: number;
}

interface DailyStat {
  date: string;
  trades: number;
  profit: number;
  volume: number;
  win_rate: number;
  wins: number;
  losses: number;
}

interface SymbolStat {
  trades: number;
  profit: number;
  volume: number;
  wins: number;
  losses: number;
  win_rate: number;
  avg_profit: number;
}

interface AccountSummary {
  success: boolean;
  timestamp: string;
  account: AccountInfo | null;
  metrics: Metrics;
  positions: {
    count: number;
    total_profit: number;
    data: Position[];
  };
  pending_orders: {
    count: number;
    data: any[];
  };
  deposits_withdrawals: {
    total_deposits: number;
    total_withdrawals: number;
    net: number;
  };
  daily_performance: {
    count: number;
    data: DailyStat[];
  };
  symbols: {
    count: number;
    top_5: Record<string, SymbolStat>;
  };
}

export default function MT5AccountPage() {
  const [summary, setSummary] = useState<AccountSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/mt5-account/summary');
      const data = await response.json();
      
      if (data.success) {
        setSummary(data);
        setLastUpdate(new Date());
      } else {
        setError(data.detail || 'Erro ao carregar dados');
      }
    } catch (err) {
      setError('Erro de conexão com o servidor');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // Atualiza a cada 30s
    return () => clearInterval(interval);
  }, []);

  const formatCurrency = (value: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 2
    }).format(value);
  };

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  if (loading && !summary) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-12 h-12 text-amber-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Conectando ao MT5...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <p className="text-red-400 mb-4">{error}</p>
          <button 
            onClick={fetchData}
            className="px-4 py-2 bg-amber-500 text-black rounded-lg hover:bg-amber-400"
          >
            Tentar novamente
          </button>
        </div>
      </div>
    );
  }

  if (!summary || !summary.account) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-yellow-500 mx-auto mb-4" />
          <p className="text-yellow-400">MT5 não conectado</p>
          <p className="text-gray-500 text-sm mt-2">Abra o terminal MT5 e faça login na sua conta</p>
        </div>
      </div>
    );
  }

  const { account, metrics, positions, daily_performance, symbols, deposits_withdrawals } = summary;
  const currency = account.currency;

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-amber-500">Conta MT5 Real</h1>
          <p className="text-gray-400 mt-1">
            {account.name} • {account.login} @ {account.server}
          </p>
        </div>
        <div className="flex items-center gap-4">
          {lastUpdate && (
            <span className="text-gray-500 text-sm">
              Atualizado: {lastUpdate.toLocaleTimeString()}
            </span>
          )}
          <button 
            onClick={fetchData}
            disabled={loading}
            className="p-2 bg-gray-800 rounded-lg hover:bg-gray-700 disabled:opacity-50"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Cards principais */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {/* Balance */}
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <span className="text-gray-400">Balance</span>
            <Wallet className="w-5 h-5 text-amber-500" />
          </div>
          <p className="text-2xl font-bold">{formatCurrency(metrics.balance, currency)}</p>
          <p className="text-sm text-gray-500 mt-2">
            Depósitos: {formatCurrency(deposits_withdrawals.total_deposits, currency)}
          </p>
        </div>

        {/* Equity */}
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <span className="text-gray-400">Equity</span>
            <Activity className="w-5 h-5 text-blue-500" />
          </div>
          <p className="text-2xl font-bold">{formatCurrency(metrics.equity, currency)}</p>
          <p className={`text-sm mt-2 ${account.profit >= 0 ? 'text-green-500' : 'text-red-500'}`}>
            Flutuante: {formatCurrency(account.profit, currency)}
          </p>
        </div>

        {/* Lucro Total */}
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <span className="text-gray-400">Lucro Total</span>
            {(metrics.real_profit || metrics.total_profit) >= 0 ? (
              <TrendingUp className="w-5 h-5 text-green-500" />
            ) : (
              <TrendingDown className="w-5 h-5 text-red-500" />
            )}
          </div>
          <p className={`text-2xl font-bold ${(metrics.real_profit || metrics.total_profit) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
            {formatCurrency(metrics.real_profit || metrics.total_profit, currency)}
          </p>
          <p className="text-sm text-gray-500 mt-2">
            {metrics.total_trades} trades | Trades: {formatCurrency(metrics.total_profit, currency)}
          </p>
        </div>

        {/* Win Rate */}
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <span className="text-gray-400">Win Rate</span>
            <Target className="w-5 h-5 text-purple-500" />
          </div>
          <p className="text-2xl font-bold">{metrics.win_rate.toFixed(1)}%</p>
          <p className="text-sm text-gray-500 mt-2">
            {metrics.wins}W / {metrics.losses}L
          </p>
        </div>
      </div>

      {/* Lucros por período */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/50">
          <span className="text-gray-500 text-sm">Hoje</span>
          <p className={`text-xl font-bold ${metrics.profit_today >= 0 ? 'text-green-500' : 'text-red-500'}`}>
            {formatCurrency(metrics.profit_today, currency)}
          </p>
        </div>
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/50">
          <span className="text-gray-500 text-sm">Esta Semana</span>
          <p className={`text-xl font-bold ${metrics.profit_week >= 0 ? 'text-green-500' : 'text-red-500'}`}>
            {formatCurrency(metrics.profit_week, currency)}
          </p>
        </div>
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/50">
          <span className="text-gray-500 text-sm">Este Mês</span>
          <p className={`text-xl font-bold ${metrics.profit_month >= 0 ? 'text-green-500' : 'text-red-500'}`}>
            {formatCurrency(metrics.profit_month, currency)}
          </p>
        </div>
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/50">
          <span className="text-gray-500 text-sm">Este Ano</span>
          <p className={`text-xl font-bold ${metrics.profit_year >= 0 ? 'text-green-500' : 'text-red-500'}`}>
            {formatCurrency(metrics.profit_year, currency)}
          </p>
        </div>
      </div>

      {/* Grid de métricas e posições */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Métricas de Risco */}
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <BarChart2 className="w-5 h-5 text-amber-500" />
            Métricas de Risco
          </h3>
          <div className="space-y-4">
            <div className="flex justify-between">
              <span className="text-gray-400">Drawdown Máx.</span>
              <span className="text-red-400">
                {formatCurrency(metrics.max_drawdown, currency)} ({metrics.max_drawdown_pct.toFixed(2)}%)
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Drawdown Atual</span>
              <span className={metrics.current_drawdown > 0 ? 'text-yellow-400' : 'text-green-400'}>
                {formatCurrency(metrics.current_drawdown, currency)} ({metrics.current_drawdown_pct.toFixed(2)}%)
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Profit Factor</span>
              <span className={metrics.profit_factor >= 1.5 ? 'text-green-400' : metrics.profit_factor >= 1 ? 'text-yellow-400' : 'text-red-400'}>
                {metrics.profit_factor.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Sharpe Ratio</span>
              <span className={metrics.sharpe_ratio >= 1 ? 'text-green-400' : 'text-yellow-400'}>
                {metrics.sharpe_ratio.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Recovery Factor</span>
              <span>{metrics.recovery_factor.toFixed(2)}</span>
            </div>
          </div>
        </div>

        {/* Melhores/Piores */}
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Award className="w-5 h-5 text-amber-500" />
            Extremos
          </h3>
          <div className="space-y-4">
            <div className="flex justify-between">
              <span className="text-gray-400">Melhor Trade</span>
              <span className="text-green-400">{formatCurrency(metrics.best_trade, currency)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Pior Trade</span>
              <span className="text-red-400">{formatCurrency(metrics.worst_trade, currency)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Melhor Dia</span>
              <span className="text-green-400">{formatCurrency(metrics.best_day, currency)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Pior Dia</span>
              <span className="text-red-400">{formatCurrency(metrics.worst_day, currency)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Lucro Médio Diário</span>
              <span className={metrics.avg_daily_profit >= 0 ? 'text-green-400' : 'text-red-400'}>
                {formatCurrency(metrics.avg_daily_profit, currency)}
              </span>
            </div>
          </div>
        </div>

        {/* Sequências */}
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-amber-500" />
            Sequências
          </h3>
          <div className="space-y-4">
            <div className="flex justify-between">
              <span className="text-gray-400">Sequência Atual</span>
              <span className={metrics.current_streak >= 0 ? 'text-green-400' : 'text-red-400'}>
                {metrics.current_streak > 0 ? `${metrics.current_streak} wins` : metrics.current_streak < 0 ? `${Math.abs(metrics.current_streak)} losses` : 'Neutro'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Máx. Wins Seguidos</span>
              <span className="text-green-400">{metrics.max_win_streak}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Máx. Losses Seguidos</span>
              <span className="text-red-400">{metrics.max_loss_streak}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Lucro Médio/Trade</span>
              <span>{formatCurrency(metrics.avg_trade_profit, currency)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Alavancagem</span>
              <span>1:{account.leverage}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Posições Abertas */}
      {positions.count > 0 && (
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 mb-8">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-amber-500" />
            Posições Abertas ({positions.count})
            <span className={`ml-auto text-sm ${positions.total_profit >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              Total: {formatCurrency(positions.total_profit, currency)}
            </span>
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-gray-400 text-sm border-b border-gray-700">
                  <th className="text-left py-2">Símbolo</th>
                  <th className="text-left py-2">Tipo</th>
                  <th className="text-right py-2">Volume</th>
                  <th className="text-right py-2">Preço Entrada</th>
                  <th className="text-right py-2">Preço Atual</th>
                  <th className="text-right py-2">Lucro</th>
                  <th className="text-right py-2">SL</th>
                  <th className="text-right py-2">TP</th>
                </tr>
              </thead>
              <tbody>
                {positions.data.map((pos) => (
                  <tr key={pos.ticket} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                    <td className="py-3 font-medium">{pos.symbol}</td>
                    <td className={pos.type === 'BUY' ? 'text-green-500' : 'text-red-500'}>
                      {pos.type}
                    </td>
                    <td className="text-right">{pos.volume}</td>
                    <td className="text-right">{pos.price_open.toFixed(5)}</td>
                    <td className="text-right">{pos.price_current.toFixed(5)}</td>
                    <td className={`text-right font-medium ${pos.profit >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {formatCurrency(pos.profit, currency)}
                    </td>
                    <td className="text-right text-red-400">{pos.sl > 0 ? pos.sl.toFixed(5) : '-'}</td>
                    <td className="text-right text-green-400">{pos.tp > 0 ? pos.tp.toFixed(5) : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Performance por Símbolo */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Símbolos */}
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <PieChart className="w-5 h-5 text-amber-500" />
            Performance por Símbolo
          </h3>
          <div className="space-y-3">
            {Object.entries(symbols.top_5).map(([symbol, stats]) => (
              <div key={symbol} className="flex items-center justify-between p-3 bg-gray-700/30 rounded-lg">
                <div>
                  <span className="font-medium">{symbol}</span>
                  <span className="text-gray-500 text-sm ml-2">({stats.trades} trades)</span>
                </div>
                <div className="text-right">
                  <p className={stats.profit >= 0 ? 'text-green-500' : 'text-red-500'}>
                    {formatCurrency(stats.profit, currency)}
                  </p>
                  <p className="text-gray-500 text-sm">
                    WR: {stats.win_rate.toFixed(1)}%
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Últimos dias */}
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Calendar className="w-5 h-5 text-amber-500" />
            Últimos 7 Dias
          </h3>
          <div className="space-y-2">
            {daily_performance.data.map((day) => (
              <div key={day.date} className="flex items-center justify-between p-3 bg-gray-700/30 rounded-lg">
                <div>
                  <span className="font-medium">
                    {new Date(day.date).toLocaleDateString('pt-BR', { weekday: 'short', day: '2-digit', month: '2-digit' })}
                  </span>
                  <span className="text-gray-500 text-sm ml-2">
                    {day.trades} trades • WR: {day.win_rate.toFixed(0)}%
                  </span>
                </div>
                <span className={day.profit >= 0 ? 'text-green-500 font-medium' : 'text-red-500 font-medium'}>
                  {formatCurrency(day.profit, currency)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
