/**
 * VIRTUS Trading System - Página de Ações B3
 * Cotações, histórico e análise fundamentalista
 */

import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Search,
  RefreshCw,
  BarChart3,
  DollarSign,
  Activity,
  Building2,
  ChevronUp,
  ChevronDown,
  Star,
  Info,
} from 'lucide-react';
import {
  getQuote,
  getStockList,
  getTopGainers,
  getTopLosers,
  getMostTraded,
  formatCurrency,
  formatPercent,
  formatMarketCap,
  formatNumber,
  getChangeColor,
  getChangeBgColor,
  StockQuote,
} from '../services/brapiService';

const StocksPage: React.FC = () => {
  const [stocks, setStocks] = useState<StockQuote[]>([]);
  const [topGainers, setTopGainers] = useState<StockQuote[]>([]);
  const [topLosers, setTopLosers] = useState<StockQuote[]>([]);
  const [mostTraded, setMostTraded] = useState<StockQuote[]>([]);
  const [selectedStock, setSelectedStock] = useState<StockQuote | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'all' | 'gainers' | 'losers' | 'volume'>('all');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [stocksRes, gainersRes, losersRes, tradedRes] = await Promise.all([
        getStockList({ limit: 50, sortBy: 'volume', sortOrder: 'desc' }),
        getTopGainers(10),
        getTopLosers(10),
        getMostTraded(10),
      ]);

      setStocks(stocksRes.stocks || []);
      setTopGainers(gainersRes.stocks || []);
      setTopLosers(losersRes.stocks || []);
      setMostTraded(tradedRes.stocks || []);
    } catch (err: any) {
      console.error('Erro ao carregar dados:', err);
      setError(err.message || 'Erro ao carregar dados');
    } finally {
      setLoading(false);
    }
  };

  const searchStock = async () => {
    if (!searchTerm.trim()) return;
    
    setLoading(true);
    try {
      const result = await getQuote([searchTerm.toUpperCase()], {
        fundamental: true,
        dividends: true,
      });
      
      if (result.results && result.results.length > 0) {
        setSelectedStock(result.results[0]);
      } else {
        setError('Ação não encontrada');
      }
    } catch (err: any) {
      setError(err.message || 'Erro ao buscar ação');
    } finally {
      setLoading(false);
    }
  };

  const renderStockCard = (stock: StockQuote) => {
    const change = stock.regularMarketChangePercent ?? 0;
    const isPositive = change >= 0;

    return (
      <div
        key={stock.symbol}
        className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow cursor-pointer border border-gray-100 dark:border-gray-700"
        onClick={() => setSelectedStock(stock)}
      >
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            {stock.logourl && (
              <img src={stock.logourl} alt={stock.symbol} className="w-8 h-8 rounded" />
            )}
            <div>
              <h3 className="font-bold text-gray-900 dark:text-white">{stock.symbol}</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-[150px]">
                {stock.shortName || stock.longName}
              </p>
            </div>
          </div>
          {isPositive ? (
            <ChevronUp className="w-5 h-5 text-green-500" />
          ) : (
            <ChevronDown className="w-5 h-5 text-red-500" />
          )}
        </div>

        <div className="flex items-center justify-between">
          <span className="text-lg font-semibold text-gray-900 dark:text-white">
            {formatCurrency(stock.regularMarketPrice ?? 0)}
          </span>
          <span className={`text-sm font-medium px-2 py-1 rounded ${getChangeBgColor(change)}`}>
            {formatPercent(change)}
          </span>
        </div>

        <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
          Vol: {formatNumber(stock.regularMarketVolume ?? 0)}
        </div>
      </div>
    );
  };

  const renderStockDetail = () => {
    if (!selectedStock) return null;

    const stock = selectedStock;
    const change = stock.regularMarketChangePercent ?? 0;

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white dark:bg-gray-800 rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                {stock.logourl && (
                  <img src={stock.logourl} alt={stock.symbol} className="w-12 h-12 rounded" />
                )}
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                    {stock.symbol}
                  </h2>
                  <p className="text-gray-500 dark:text-gray-400">{stock.longName || stock.shortName}</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedStock(null)}
                className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
              >
                ✕
              </button>
            </div>

            {/* Preço e Variação */}
            <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 mb-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Preço Atual</p>
                  <p className="text-3xl font-bold text-gray-900 dark:text-white">
                    {formatCurrency(stock.regularMarketPrice ?? 0)}
                  </p>
                </div>
                <div className={`text-right ${getChangeColor(change)}`}>
                  <p className="text-2xl font-bold">{formatPercent(change)}</p>
                  <p className="text-sm">
                    {change >= 0 ? '+' : ''}{formatCurrency(stock.regularMarketChange ?? 0)}
                  </p>
                </div>
              </div>
            </div>

            {/* Grid de informações */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
                <p className="text-xs text-gray-500 dark:text-gray-400">Abertura</p>
                <p className="font-semibold text-gray-900 dark:text-white">
                  {formatCurrency(stock.regularMarketOpen ?? 0)}
                </p>
              </div>
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
                <p className="text-xs text-gray-500 dark:text-gray-400">Máxima</p>
                <p className="font-semibold text-green-600">
                  {formatCurrency(stock.regularMarketDayHigh ?? 0)}
                </p>
              </div>
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
                <p className="text-xs text-gray-500 dark:text-gray-400">Mínima</p>
                <p className="font-semibold text-red-600">
                  {formatCurrency(stock.regularMarketDayLow ?? 0)}
                </p>
              </div>
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
                <p className="text-xs text-gray-500 dark:text-gray-400">Fech. Anterior</p>
                <p className="font-semibold text-gray-900 dark:text-white">
                  {formatCurrency(stock.regularMarketPreviousClose ?? 0)}
                </p>
              </div>
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
                <p className="text-xs text-gray-500 dark:text-gray-400">Volume</p>
                <p className="font-semibold text-gray-900 dark:text-white">
                  {formatNumber(stock.regularMarketVolume ?? 0)}
                </p>
              </div>
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
                <p className="text-xs text-gray-500 dark:text-gray-400">Market Cap</p>
                <p className="font-semibold text-gray-900 dark:text-white">
                  {formatMarketCap(stock.marketCap ?? 0)}
                </p>
              </div>
            </div>

            {/* 52 semanas */}
            <div className="mb-6">
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">Variação 52 semanas</p>
              <div className="flex items-center gap-2">
                <span className="text-sm text-red-600">{formatCurrency(stock.fiftyTwoWeekLow ?? 0)}</span>
                <div className="flex-1 h-2 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500"
                    style={{
                      width: `${
                        ((stock.regularMarketPrice - (stock.fiftyTwoWeekLow ?? 0)) /
                          ((stock.fiftyTwoWeekHigh ?? 1) - (stock.fiftyTwoWeekLow ?? 0))) *
                        100
                      }%`,
                    }}
                  />
                </div>
                <span className="text-sm text-green-600">{formatCurrency(stock.fiftyTwoWeekHigh ?? 0)}</span>
              </div>
            </div>

            {/* Indicadores Fundamentalistas */}
            {(stock.priceEarnings || stock.earningsPerShare) && (
              <div className="border-t border-gray-200 dark:border-gray-600 pt-4">
                <h3 className="font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                  <BarChart3 className="w-5 h-5" />
                  Indicadores Fundamentalistas
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  {stock.priceEarnings && (
                    <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3">
                      <p className="text-xs text-blue-600 dark:text-blue-400">P/L</p>
                      <p className="font-semibold text-blue-800 dark:text-blue-300">
                        {(stock.priceEarnings ?? 0).toFixed(2)}
                      </p>
                    </div>
                  )}
                  {stock.earningsPerShare && (
                    <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-3">
                      <p className="text-xs text-purple-600 dark:text-purple-400">LPA</p>
                      <p className="font-semibold text-purple-800 dark:text-purple-300">
                        {formatCurrency(stock.earningsPerShare ?? 0)}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Dividendos */}
            {stock.dividendsData?.cashDividends && stock.dividendsData.cashDividends.length > 0 && (
              <div className="border-t border-gray-200 dark:border-gray-600 pt-4 mt-4">
                <h3 className="font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                  <DollarSign className="w-5 h-5" />
                  Últimos Dividendos
                </h3>
                <div className="space-y-2">
                  {stock.dividendsData.cashDividends.slice(0, 5).map((div, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between bg-gray-50 dark:bg-gray-700 rounded-lg p-3"
                    >
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white">{div.label}</p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {new Date(div.paymentDate).toLocaleDateString('pt-BR')}
                        </p>
                      </div>
                      <p className="font-semibold text-green-600">
                        {formatCurrency(div.rate)}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  const getCurrentStocks = () => {
    switch (activeTab) {
      case 'gainers':
        return topGainers;
      case 'losers':
        return topLosers;
      case 'volume':
        return mostTraded;
      default:
        return stocks;
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Building2 className="w-7 h-7 text-blue-600" />
            Ações B3
          </h1>
          <p className="text-gray-500 dark:text-gray-400">
            Cotações em tempo real do mercado brasileiro
          </p>
        </div>
        <button
          onClick={loadData}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Atualizar
        </button>
      </div>

      {/* Busca */}
      <div className="flex gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar ação (ex: PETR4, VALE3)"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value.toUpperCase())}
            onKeyPress={(e) => e.key === 'Enter' && searchStock()}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <button
          onClick={searchStock}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Buscar
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-200 dark:border-gray-700">
        {[
          { id: 'all', label: 'Todas', icon: Activity },
          { id: 'gainers', label: 'Maiores Altas', icon: TrendingUp },
          { id: 'losers', label: 'Maiores Quedas', icon: TrendingDown },
          { id: 'volume', label: 'Mais Negociadas', icon: BarChart3 },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`flex items-center gap-2 px-4 py-2 border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-600 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="w-8 h-8 text-blue-600 animate-spin" />
        </div>
      )}

      {/* Grid de Ações */}
      {!loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {getCurrentStocks().map(renderStockCard)}
        </div>
      )}

      {/* Modal de Detalhes */}
      {selectedStock && renderStockDetail()}
    </div>
  );
};

export default StocksPage;
