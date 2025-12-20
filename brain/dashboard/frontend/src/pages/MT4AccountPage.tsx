import { useState, useEffect, useRef } from 'react';
import { 
  TrendingUp, TrendingDown, DollarSign, Activity, 
  BarChart2, PieChart, Calendar, RefreshCw, 
  Upload, Plus, Settings, Download, Wallet,
  Target, AlertTriangle, Award, Zap, Edit3
} from 'lucide-react';

interface AccountInfo {
  login: number;
  name: string;
  server: string;
  currency: string;
  balance: number;
  equity: number;
  leverage: number;
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

interface Trade {
  ticket: number;
  symbol: string;
  type: string;
  volume: number;
  open_price: number;
  close_price: number;
  open_time: string;
  close_time: string;
  profit: number;
  swap: number;
  commission: number;
  total_pnl: number;
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

export default function MT4AccountPage() {
  const [summary, setSummary] = useState<AccountSummary | null>(null);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [showSetup, setShowSetup] = useState(false);
  const [showAddTrade, setShowAddTrade] = useState(false);
  const [showAddDeposit, setShowAddDeposit] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Form states
  const [setupForm, setSetupForm] = useState({
    login: '',
    name: '',
    server: 'Pepperstone-Live',
    currency: 'USD',
    balance: '',
    leverage: '100',
    company: 'Pepperstone'
  });

  const [depositForm, setDepositForm] = useState({
    amount: '',
    date: new Date().toISOString().split('T')[0],
    comment: ''
  });

  const [tradeForm, setTradeForm] = useState({
    ticket: '',
    symbol: '',
    type: 'BUY',
    volume: '0.1',
    open_price: '',
    close_price: '',
    open_time: '',
    close_time: '',
    profit: '',
    swap: '0',
    commission: '0'
  });

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryRes, tradesRes] = await Promise.all([
        fetch('/api/mt4-account/summary'),
        fetch('/api/mt4-account/trades?days=30')
      ]);
      
      const summaryData = await summaryRes.json();
      const tradesData = await tradesRes.json();
      
      if (summaryData.success) {
        setSummary(summaryData);
        setLastUpdate(new Date());
      }
      
      if (tradesData.success) {
        setTrades(tradesData.data);
      }
      
      // Se não tem conta configurada, mostrar setup
      if (!summaryData.account) {
        setShowSetup(true);
      }
    } catch (err) {
      setError('Erro de conexão com o servidor');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSetupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await fetch('/api/mt4-account/setup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          login: parseInt(setupForm.login),
          name: setupForm.name,
          server: setupForm.server,
          currency: setupForm.currency,
          balance: parseFloat(setupForm.balance),
          leverage: parseInt(setupForm.leverage),
          company: setupForm.company
        })
      });
      
      const data = await response.json();
      if (data.success) {
        setShowSetup(false);
        fetchData();
      }
    } catch (err) {
      alert('Erro ao configurar conta');
    }
  };

  const handleDepositSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await fetch('/api/mt4-account/deposit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount: parseFloat(depositForm.amount),
          date: depositForm.date,
          comment: depositForm.comment
        })
      });
      
      const data = await response.json();
      if (data.success) {
        setShowAddDeposit(false);
        setDepositForm({ amount: '', date: new Date().toISOString().split('T')[0], comment: '' });
        fetchData();
      }
    } catch (err) {
      alert('Erro ao adicionar depósito');
    }
  };

  const handleTradeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await fetch('/api/mt4-account/add-trade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticket: parseInt(tradeForm.ticket),
          symbol: tradeForm.symbol,
          type: tradeForm.type,
          volume: parseFloat(tradeForm.volume),
          open_price: parseFloat(tradeForm.open_price),
          close_price: parseFloat(tradeForm.close_price),
          open_time: tradeForm.open_time,
          close_time: tradeForm.close_time,
          profit: parseFloat(tradeForm.profit),
          swap: parseFloat(tradeForm.swap),
          commission: parseFloat(tradeForm.commission)
        })
      });
      
      const data = await response.json();
      if (data.success) {
        setShowAddTrade(false);
        setTradeForm({
          ticket: '', symbol: '', type: 'BUY', volume: '0.1',
          open_price: '', close_price: '', open_time: '', close_time: '',
          profit: '', swap: '0', commission: '0'
        });
        fetchData();
      }
    } catch (err) {
      alert('Erro ao adicionar trade');
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/mt4-account/import/csv', {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      if (data.success) {
        alert(`${data.trades_imported} trades importados com sucesso!`);
        fetchData();
      } else {
        alert('Erro ao importar arquivo');
      }
    } catch (err) {
      alert('Erro ao fazer upload');
    }
  };

  const handleExport = async () => {
    try {
      const response = await fetch('/api/mt4-account/export', { method: 'POST' });
      const data = await response.json();
      
      if (data.success) {
        const blob = new Blob([JSON.stringify(data.data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `mt4_export_${new Date().toISOString().split('T')[0]}.json`;
        a.click();
      }
    } catch (err) {
      alert('Erro ao exportar');
    }
  };

  const formatCurrency = (value: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 2
    }).format(value);
  };

  if (loading && !summary) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-12 h-12 text-amber-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Carregando dados MT4...</p>
        </div>
      </div>
    );
  }

  const account = summary?.account;
  const metrics = summary?.metrics;
  const currency = account?.currency || 'USD';

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-amber-500">Conta MT4 Real</h1>
          <p className="text-gray-400 mt-1">
            {account ? `${account.name} • ${account.login} @ ${account.server}` : 'Conta não configurada'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {lastUpdate && (
            <span className="text-gray-500 text-sm">
              Atualizado: {lastUpdate.toLocaleTimeString()}
            </span>
          )}
          <button 
            onClick={() => setShowSetup(true)}
            className="p-2 bg-gray-800 rounded-lg hover:bg-gray-700"
            title="Configurar Conta"
          >
            <Settings className="w-5 h-5" />
          </button>
          <button 
            onClick={() => fileInputRef.current?.click()}
            className="p-2 bg-gray-800 rounded-lg hover:bg-gray-700"
            title="Importar CSV"
          >
            <Upload className="w-5 h-5" />
          </button>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept=".csv"
            className="hidden"
          />
          <button 
            onClick={handleExport}
            className="p-2 bg-gray-800 rounded-lg hover:bg-gray-700"
            title="Exportar Dados"
          >
            <Download className="w-5 h-5" />
          </button>
          <button 
            onClick={fetchData}
            disabled={loading}
            className="p-2 bg-gray-800 rounded-lg hover:bg-gray-700 disabled:opacity-50"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Setup Modal */}
      {showSetup && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Configurar Conta MT4</h2>
            <form onSubmit={handleSetupSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-gray-400">Login (Número da conta)</label>
                  <input
                    type="number"
                    value={setupForm.login}
                    onChange={(e) => setSetupForm({...setupForm, login: e.target.value})}
                    className="w-full bg-gray-700 rounded-lg px-3 py-2 mt-1"
                    required
                  />
                </div>
                <div>
                  <label className="text-sm text-gray-400">Nome</label>
                  <input
                    type="text"
                    value={setupForm.name}
                    onChange={(e) => setSetupForm({...setupForm, name: e.target.value})}
                    className="w-full bg-gray-700 rounded-lg px-3 py-2 mt-1"
                    required
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-gray-400">Servidor</label>
                  <select
                    value={setupForm.server}
                    onChange={(e) => setSetupForm({...setupForm, server: e.target.value})}
                    className="w-full bg-gray-700 rounded-lg px-3 py-2 mt-1"
                  >
                    <option value="Pepperstone-Live">Pepperstone Live</option>
                    <option value="Pepperstone-Demo">Pepperstone Demo</option>
                    <option value="XM-Real">XM Real</option>
                    <option value="IC Markets-Live">IC Markets Live</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm text-gray-400">Moeda</label>
                  <select
                    value={setupForm.currency}
                    onChange={(e) => setSetupForm({...setupForm, currency: e.target.value})}
                    className="w-full bg-gray-700 rounded-lg px-3 py-2 mt-1"
                  >
                    <option value="USD">USD</option>
                    <option value="EUR">EUR</option>
                    <option value="BRL">BRL</option>
                    <option value="GBP">GBP</option>
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-gray-400">Saldo Atual</label>
                  <input
                    type="number"
                    step="0.01"
                    value={setupForm.balance}
                    onChange={(e) => setSetupForm({...setupForm, balance: e.target.value})}
                    className="w-full bg-gray-700 rounded-lg px-3 py-2 mt-1"
                    required
                  />
                </div>
                <div>
                  <label className="text-sm text-gray-400">Alavancagem</label>
                  <select
                    value={setupForm.leverage}
                    onChange={(e) => setSetupForm({...setupForm, leverage: e.target.value})}
                    className="w-full bg-gray-700 rounded-lg px-3 py-2 mt-1"
                  >
                    <option value="30">1:30</option>
                    <option value="50">1:50</option>
                    <option value="100">1:100</option>
                    <option value="200">1:200</option>
                    <option value="400">1:400</option>
                    <option value="500">1:500</option>
                  </select>
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button
                  type="button"
                  onClick={() => setShowSetup(false)}
                  className="flex-1 px-4 py-2 bg-gray-700 rounded-lg hover:bg-gray-600"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-amber-500 text-black rounded-lg hover:bg-amber-400"
                >
                  Salvar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Deposit Modal */}
      {showAddDeposit && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Adicionar Depósito</h2>
            <form onSubmit={handleDepositSubmit} className="space-y-4">
              <div>
                <label className="text-sm text-gray-400">Valor</label>
                <input
                  type="number"
                  step="0.01"
                  value={depositForm.amount}
                  onChange={(e) => setDepositForm({...depositForm, amount: e.target.value})}
                  className="w-full bg-gray-700 rounded-lg px-3 py-2 mt-1"
                  required
                />
              </div>
              <div>
                <label className="text-sm text-gray-400">Data</label>
                <input
                  type="date"
                  value={depositForm.date}
                  onChange={(e) => setDepositForm({...depositForm, date: e.target.value})}
                  className="w-full bg-gray-700 rounded-lg px-3 py-2 mt-1"
                />
              </div>
              <div>
                <label className="text-sm text-gray-400">Comentário</label>
                <input
                  type="text"
                  value={depositForm.comment}
                  onChange={(e) => setDepositForm({...depositForm, comment: e.target.value})}
                  className="w-full bg-gray-700 rounded-lg px-3 py-2 mt-1"
                />
              </div>
              <div className="flex gap-3 mt-6">
                <button
                  type="button"
                  onClick={() => setShowAddDeposit(false)}
                  className="flex-1 px-4 py-2 bg-gray-700 rounded-lg hover:bg-gray-600"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-400"
                >
                  Adicionar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Trade Modal */}
      {showAddTrade && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 overflow-y-auto py-10">
          <div className="bg-gray-800 rounded-xl p-6 w-full max-w-lg mx-4">
            <h2 className="text-xl font-bold mb-4">Adicionar Trade</h2>
            <form onSubmit={handleTradeSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-gray-400">Ticket</label>
                  <input
                    type="number"
                    value={tradeForm.ticket}
                    onChange={(e) => setTradeForm({...tradeForm, ticket: e.target.value})}
                    className="w-full bg-gray-700 rounded-lg px-3 py-2 mt-1"
                    required
                  />
                </div>
                <div>
                  <label className="text-sm text-gray-400">Símbolo</label>
                  <input
                    type="text"
                    value={tradeForm.symbol}
                    onChange={(e) => setTradeForm({...tradeForm, symbol: e.target.value.toUpperCase()})}
                    className="w-full bg-gray-700 rounded-lg px-3 py-2 mt-1"
                    placeholder="EURUSD"
                    required
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-gray-400">Tipo</label>
                  <select
                    value={tradeForm.type}
                    onChange={(e) => setTradeForm({...tradeForm, type: e.target.value})}
                    className="w-full bg-gray-700 rounded-lg px-3 py-2 mt-1"
                  >
                    <option value="BUY">BUY</option>
                    <option value="SELL">SELL</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm text-gray-400">Volume (Lotes)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={tradeForm.volume}
                    onChange={(e) => setTradeForm({...tradeForm, volume: e.target.value})}
                    className="w-full bg-gray-700 rounded-lg px-3 py-2 mt-1"
                    required
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-gray-400">Preço Abertura</label>
                  <input
                    type="number"
                    step="0.00001"
                    value={tradeForm.open_price}
                    onChange={(e) => setTradeForm({...tradeForm, open_price: e.target.value})}
                    className="w-full bg-gray-700 rounded-lg px-3 py-2 mt-1"
                    required
                  />
                </div>
                <div>
                  <label className="text-sm text-gray-400">Preço Fechamento</label>
                  <input
                    type="number"
                    step="0.00001"
                    value={tradeForm.close_price}
                    onChange={(e) => setTradeForm({...tradeForm, close_price: e.target.value})}
                    className="w-full bg-gray-700 rounded-lg px-3 py-2 mt-1"
                    required
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-gray-400">Abertura</label>
                  <input
                    type="datetime-local"
                    value={tradeForm.open_time}
                    onChange={(e) => setTradeForm({...tradeForm, open_time: e.target.value})}
                    className="w-full bg-gray-700 rounded-lg px-3 py-2 mt-1"
                    required
                  />
                </div>
                <div>
                  <label className="text-sm text-gray-400">Fechamento</label>
                  <input
                    type="datetime-local"
                    value={tradeForm.close_time}
                    onChange={(e) => setTradeForm({...tradeForm, close_time: e.target.value})}
                    className="w-full bg-gray-700 rounded-lg px-3 py-2 mt-1"
                    required
                  />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="text-sm text-gray-400">Lucro/Prejuízo</label>
                  <input
                    type="number"
                    step="0.01"
                    value={tradeForm.profit}
                    onChange={(e) => setTradeForm({...tradeForm, profit: e.target.value})}
                    className="w-full bg-gray-700 rounded-lg px-3 py-2 mt-1"
                    required
                  />
                </div>
                <div>
                  <label className="text-sm text-gray-400">Swap</label>
                  <input
                    type="number"
                    step="0.01"
                    value={tradeForm.swap}
                    onChange={(e) => setTradeForm({...tradeForm, swap: e.target.value})}
                    className="w-full bg-gray-700 rounded-lg px-3 py-2 mt-1"
                  />
                </div>
                <div>
                  <label className="text-sm text-gray-400">Comissão</label>
                  <input
                    type="number"
                    step="0.01"
                    value={tradeForm.commission}
                    onChange={(e) => setTradeForm({...tradeForm, commission: e.target.value})}
                    className="w-full bg-gray-700 rounded-lg px-3 py-2 mt-1"
                  />
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button
                  type="button"
                  onClick={() => setShowAddTrade(false)}
                  className="flex-1 px-4 py-2 bg-gray-700 rounded-lg hover:bg-gray-600"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-amber-500 text-black rounded-lg hover:bg-amber-400"
                >
                  Adicionar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Se não tem conta configurada */}
      {!account && !showSetup && (
        <div className="bg-gray-800 rounded-xl p-8 text-center mb-8">
          <AlertTriangle className="w-16 h-16 text-yellow-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold mb-2">Conta MT4 não configurada</h2>
          <p className="text-gray-400 mb-6">
            Configure sua conta para começar a rastrear seus trades
          </p>
          <button
            onClick={() => setShowSetup(true)}
            className="px-6 py-3 bg-amber-500 text-black rounded-lg hover:bg-amber-400"
          >
            Configurar Conta
          </button>
        </div>
      )}

      {/* Conteúdo principal - só mostra se tem conta */}
      {account && metrics && (
        <>
          {/* Ações rápidas */}
          <div className="flex gap-3 mb-6">
            <button
              onClick={() => setShowAddDeposit(true)}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-500"
            >
              <Plus className="w-4 h-4" />
              Depósito
            </button>
            <button
              onClick={() => setShowAddTrade(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500"
            >
              <Edit3 className="w-4 h-4" />
              Adicionar Trade
            </button>
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
                Depósitos: {formatCurrency(summary.deposits_withdrawals.total_deposits, currency)}
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
                {metrics.total_trades} trades | Trades sync: {formatCurrency(metrics.total_profit, currency)}
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

            {/* Drawdown */}
            <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
              <div className="flex items-center justify-between mb-4">
                <span className="text-gray-400">Max Drawdown</span>
                <AlertTriangle className="w-5 h-5 text-red-500" />
              </div>
              <p className="text-2xl font-bold text-red-400">
                {formatCurrency(metrics.max_drawdown, currency)}
              </p>
              <p className="text-sm text-gray-500 mt-2">
                {metrics.max_drawdown_pct.toFixed(2)}% do peak
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

          {/* Grid de métricas */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            {/* Métricas de Risco */}
            <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <BarChart2 className="w-5 h-5 text-amber-500" />
                Métricas de Risco
              </h3>
              <div className="space-y-4">
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
                <div className="flex justify-between">
                  <span className="text-gray-400">Lucro Médio/Trade</span>
                  <span>{formatCurrency(metrics.avg_trade_profit, currency)}</span>
                </div>
              </div>
            </div>

            {/* Extremos */}
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
                    {metrics.current_streak > 0 ? `${metrics.current_streak} wins` : 
                     metrics.current_streak < 0 ? `${Math.abs(metrics.current_streak)} losses` : 'Neutro'}
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
                  <span className="text-gray-400">Lucro Médio Diário</span>
                  <span>{formatCurrency(metrics.avg_daily_profit, currency)}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Histórico de Trades */}
          {trades.length > 0 && (
            <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 mb-8">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Activity className="w-5 h-5 text-amber-500" />
                Últimos Trades ({trades.length})
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="text-gray-400 text-sm border-b border-gray-700">
                      <th className="text-left py-2">Ticket</th>
                      <th className="text-left py-2">Símbolo</th>
                      <th className="text-left py-2">Tipo</th>
                      <th className="text-right py-2">Volume</th>
                      <th className="text-right py-2">Abertura</th>
                      <th className="text-right py-2">Fechamento</th>
                      <th className="text-right py-2">Lucro</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trades.slice(0, 20).map((trade) => (
                      <tr key={trade.ticket} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                        <td className="py-3 text-gray-500">{trade.ticket}</td>
                        <td className="font-medium">{trade.symbol}</td>
                        <td className={trade.type === 'BUY' ? 'text-green-500' : 'text-red-500'}>
                          {trade.type}
                        </td>
                        <td className="text-right">{trade.volume}</td>
                        <td className="text-right text-gray-400">{trade.open_price}</td>
                        <td className="text-right text-gray-400">{trade.close_price}</td>
                        <td className={`text-right font-medium ${trade.total_pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                          {formatCurrency(trade.total_pnl, currency)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Performance por Símbolo e Dias */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Top Símbolos */}
            <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <PieChart className="w-5 h-5 text-amber-500" />
                Performance por Símbolo
              </h3>
              <div className="space-y-3">
                {Object.entries(summary.symbols.top_5).map(([symbol, stats]) => (
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
                {summary.daily_performance.data.map((day) => (
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
        </>
      )}

      {/* Info sobre como usar */}
      <div className="mt-8 bg-gray-800/50 rounded-xl p-6 border border-gray-700/50">
        <h3 className="text-lg font-semibold mb-3 text-amber-500">Como importar seus trades do MT4</h3>
        <ol className="list-decimal list-inside space-y-2 text-gray-400">
          <li>Abra o MetaTrader 4 e vá para a aba <strong>Account History</strong></li>
          <li>Clique com botão direito → <strong>Save as Report</strong> ou <strong>Save as Detailed Report</strong></li>
          <li>Salve como arquivo <strong>.htm</strong> ou <strong>.csv</strong></li>
          <li>Clique no botão <Upload className="w-4 h-4 inline" /> acima para fazer upload</li>
          <li>Ou adicione trades manualmente clicando em <strong>Adicionar Trade</strong></li>
        </ol>
      </div>
    </div>
  );
}
