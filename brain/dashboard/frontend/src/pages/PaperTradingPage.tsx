/**
 * VIRTUS - Página de Paper Trading
 * 
 * Simulação de trades sem dinheiro real
 */

import React, { useState, useEffect } from 'react';
import {
  Play,
  Square,
  TrendingUp,
  TrendingDown,
  DollarSign,
  BarChart2,
  RefreshCw,
  Plus,
  X,
  Target,
  Shield,
} from 'lucide-react';
import { paperTradingService, PaperAccount, PaperPosition, PaperStats } from '../services/newModulesService';

const PaperTradingPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [account, setAccount] = useState<PaperAccount | null>(null);
  const [positions, setPositions] = useState<PaperPosition[]>([]);
  const [history, setHistory] = useState<PaperPosition[]>([]);
  const [stats, setStats] = useState<PaperStats | null>(null);
  const [showNewTrade, setShowNewTrade] = useState(false);
  
  // Form state
  const [newTrade, setNewTrade] = useState({
    symbol: 'XAUUSD',
    type: 'buy',
    volume: 0.01,
    sl: '',
    tp: '',
    comment: '',
  });

  const fetchData = async () => {
    try {
      const [statusRes, posRes, histRes, statsRes] = await Promise.all([
        paperTradingService.getStatus(),
        paperTradingService.getPositions(),
        paperTradingService.getHistory(50),
        paperTradingService.getStats(),
      ]);
      
      setRunning(statusRes.data?.running ?? false);
      setAccount(statusRes.data?.account ?? null);
      setPositions(Array.isArray(posRes.data) ? posRes.data : []);
      setHistory(Array.isArray(histRes.data) ? histRes.data : []);
      setStats(statsRes.data ?? null);
    } catch (error) {
      console.error('Error fetching paper trading data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleStart = async () => {
    try {
      await paperTradingService.start();
      setRunning(true);
    } catch (error) {
      console.error('Error starting paper trading:', error);
    }
  };

  const handleStop = async () => {
    try {
      await paperTradingService.stop();
      setRunning(false);
    } catch (error) {
      console.error('Error stopping paper trading:', error);
    }
  };

  const handleOpenTrade = async () => {
    try {
      await paperTradingService.openTrade({
        symbol: newTrade.symbol,
        type: newTrade.type,
        volume: newTrade.volume,
        sl: newTrade.sl ? parseFloat(newTrade.sl) : undefined,
        tp: newTrade.tp ? parseFloat(newTrade.tp) : undefined,
        comment: newTrade.comment,
      });
      setShowNewTrade(false);
      fetchData();
    } catch (error) {
      console.error('Error opening trade:', error);
    }
  };

  const handleCloseTrade = async (ticket: number) => {
    try {
      await paperTradingService.closeTrade(ticket);
      fetchData();
    } catch (error) {
      console.error('Error closing trade:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            📄 Paper Trading
          </h1>
          <p className="text-gray-500 dark:text-gray-400">
            Simulação de trades sem dinheiro real
          </p>
        </div>
        <div className="flex gap-2">
          {!running ? (
            <button
              onClick={handleStart}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              <Play className="w-4 h-4" />
              Iniciar
            </button>
          ) : (
            <button
              onClick={handleStop}
              className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              <Square className="w-4 h-4" />
              Parar
            </button>
          )}
          <button
            onClick={() => setShowNewTrade(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <Plus className="w-4 h-4" />
            Novo Trade
          </button>
        </div>
      </div>

      {/* Account Info */}
      {account && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
            <div className="text-sm text-gray-500">Balance</div>
            <div className="text-xl font-bold text-gray-900 dark:text-white">
              ${account.balance.toLocaleString()}
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
            <div className="text-sm text-gray-500">Equity</div>
            <div className="text-xl font-bold text-gray-900 dark:text-white">
              ${account.equity.toLocaleString()}
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
            <div className="text-sm text-gray-500">Lucro</div>
            <div className={`text-xl font-bold ${account.profit >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              ${account.profit.toLocaleString()}
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
            <div className="text-sm text-gray-500">Margem</div>
            <div className="text-xl font-bold text-gray-900 dark:text-white">
              ${account.margin.toLocaleString()}
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
            <div className="text-sm text-gray-500">Margem Livre</div>
            <div className="text-xl font-bold text-gray-900 dark:text-white">
              ${account.free_margin.toLocaleString()}
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
            <div className="text-sm text-gray-500">Alavancagem</div>
            <div className="text-xl font-bold text-gray-900 dark:text-white">
              1:{account.leverage}
            </div>
          </div>
        </div>
      )}

      {/* Stats */}
      {stats && (
        <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <BarChart2 className="w-5 h-5" />
            Estatísticas
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div>
              <div className="text-sm text-gray-500">Total Trades</div>
              <div className="text-lg font-bold">{stats.total_trades}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Win Rate</div>
              <div className="text-lg font-bold text-green-500">{(stats.win_rate ?? 0).toFixed(1)}%</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Profit Factor</div>
              <div className="text-lg font-bold">{(stats.profit_factor ?? 0).toFixed(2)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Lucro Total</div>
              <div className={`text-lg font-bold ${(stats.total_profit ?? 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                ${(stats.total_profit ?? 0).toFixed(2)}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Posições Abertas</div>
              <div className="text-lg font-bold">{stats.open_positions}</div>
            </div>
          </div>
        </div>
      )}

      {/* Open Positions */}
      <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
        <h2 className="text-lg font-semibold mb-4">Posições Abertas ({positions.length})</h2>
        {positions.length === 0 ? (
          <p className="text-gray-500 text-center py-8">Nenhuma posição aberta</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b dark:border-gray-700">
                  <th className="text-left p-2">Ticket</th>
                  <th className="text-left p-2">Símbolo</th>
                  <th className="text-left p-2">Tipo</th>
                  <th className="text-right p-2">Volume</th>
                  <th className="text-right p-2">Preço</th>
                  <th className="text-right p-2">SL</th>
                  <th className="text-right p-2">TP</th>
                  <th className="text-right p-2">Lucro</th>
                  <th className="text-center p-2">Ação</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((pos) => (
                  <tr key={pos.ticket} className="border-b dark:border-gray-700">
                    <td className="p-2">{pos.ticket}</td>
                    <td className="p-2 font-medium">{pos.symbol}</td>
                    <td className="p-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        pos.type === 'buy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {pos.type.toUpperCase()}
                      </span>
                    </td>
                    <td className="p-2 text-right">{pos.volume}</td>
                    <td className="p-2 text-right">{pos.open_price}</td>
                    <td className="p-2 text-right">{pos.sl || '-'}</td>
                    <td className="p-2 text-right">{pos.tp || '-'}</td>
                    <td className={`p-2 text-right font-medium ${(pos.profit ?? 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      ${(pos.profit ?? 0).toFixed(2)}
                    </td>
                    <td className="p-2 text-center">
                      <button
                        onClick={() => handleCloseTrade(pos.ticket)}
                        className="p-1 text-red-500 hover:bg-red-100 rounded"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* History */}
      <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
        <h2 className="text-lg font-semibold mb-4">Histórico ({history.length})</h2>
        {history.length === 0 ? (
          <p className="text-gray-500 text-center py-8">Nenhum trade no histórico</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b dark:border-gray-700">
                  <th className="text-left p-2">Ticket</th>
                  <th className="text-left p-2">Símbolo</th>
                  <th className="text-left p-2">Tipo</th>
                  <th className="text-right p-2">Volume</th>
                  <th className="text-right p-2">Abertura</th>
                  <th className="text-right p-2">Fechamento</th>
                  <th className="text-right p-2">Lucro</th>
                </tr>
              </thead>
              <tbody>
                {history.slice(0, 20).map((trade) => (
                  <tr key={trade.ticket} className="border-b dark:border-gray-700">
                    <td className="p-2">{trade.ticket}</td>
                    <td className="p-2 font-medium">{trade.symbol}</td>
                    <td className="p-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        trade.type === 'buy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {trade.type.toUpperCase()}
                      </span>
                    </td>
                    <td className="p-2 text-right">{trade.volume}</td>
                    <td className="p-2 text-right">{trade.open_price}</td>
                    <td className="p-2 text-right">{trade.close_price}</td>
                    <td className={`p-2 text-right font-medium ${(trade.profit ?? 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      ${(trade.profit ?? 0).toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* New Trade Modal */}
      {showNewTrade && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Novo Trade</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm mb-1">Símbolo</label>
                <select
                  value={newTrade.symbol}
                  onChange={(e) => setNewTrade({ ...newTrade, symbol: e.target.value })}
                  className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600"
                >
                  <option value="XAUUSD">XAUUSD (Ouro)</option>
                  <option value="EURUSD">EURUSD</option>
                  <option value="GBPUSD">GBPUSD</option>
                </select>
              </div>
              <div>
                <label className="block text-sm mb-1">Tipo</label>
                <div className="flex gap-2">
                  <button
                    onClick={() => setNewTrade({ ...newTrade, type: 'buy' })}
                    className={`flex-1 p-2 rounded flex items-center justify-center gap-2 ${
                      newTrade.type === 'buy'
                        ? 'bg-green-600 text-white'
                        : 'bg-gray-200 dark:bg-gray-700'
                    }`}
                  >
                    <TrendingUp className="w-4 h-4" />
                    BUY
                  </button>
                  <button
                    onClick={() => setNewTrade({ ...newTrade, type: 'sell' })}
                    className={`flex-1 p-2 rounded flex items-center justify-center gap-2 ${
                      newTrade.type === 'sell'
                        ? 'bg-red-600 text-white'
                        : 'bg-gray-200 dark:bg-gray-700'
                    }`}
                  >
                    <TrendingDown className="w-4 h-4" />
                    SELL
                  </button>
                </div>
              </div>
              <div>
                <label className="block text-sm mb-1">Volume (Lotes)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={newTrade.volume}
                  onChange={(e) => setNewTrade({ ...newTrade, volume: parseFloat(e.target.value) })}
                  className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm mb-1">Stop Loss</label>
                  <input
                    type="number"
                    step="0.01"
                    placeholder="Opcional"
                    value={newTrade.sl}
                    onChange={(e) => setNewTrade({ ...newTrade, sl: e.target.value })}
                    className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600"
                  />
                </div>
                <div>
                  <label className="block text-sm mb-1">Take Profit</label>
                  <input
                    type="number"
                    step="0.01"
                    placeholder="Opcional"
                    value={newTrade.tp}
                    onChange={(e) => setNewTrade({ ...newTrade, tp: e.target.value })}
                    className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600"
                  />
                </div>
              </div>
              <div className="flex gap-2 pt-4">
                <button
                  onClick={() => setShowNewTrade(false)}
                  className="flex-1 p-2 bg-gray-200 dark:bg-gray-700 rounded"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleOpenTrade}
                  className="flex-1 p-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  Abrir Trade
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PaperTradingPage;
