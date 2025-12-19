/**
 * VIRTUS Trading System - Página de Resumo do Mercado
 * Dashboard com visão geral do mercado brasileiro
 */

import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  TrendingDown,
  RefreshCw,
  Building2,
  Bitcoin,
  Globe,
  Percent,
  BarChart3,
  Activity,
  DollarSign,
} from 'lucide-react';
import {
  getMarketSummary,
  formatCurrency,
  formatPercent,
  formatMarketCap,
  formatNumber,
  getChangeColor,
  MarketSummary,
} from '../services/brapiService';

const MarketOverviewPage: React.FC = () => {
  const [marketData, setMarketData] = useState<MarketSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getMarketSummary();
      setMarketData(data);
    } catch (err: any) {
      console.error('Erro ao carregar resumo:', err);
      setError(err.message || 'Erro ao carregar dados');
    } finally {
      setLoading(false);
    }
  };

  const renderIndexCard = () => {
    const ibov = marketData?.ibovespa?.results?.[0];
    if (!ibov) return null;

    const change = ibov.regularMarketChangePercent ?? 0;

    return (
      <div className="bg-gradient-to-br from-blue-600 to-indigo-700 rounded-xl p-6 text-white">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Building2 className="w-6 h-6" />
            <h3 className="font-semibold">Ibovespa</h3>
          </div>
          {change >= 0 ? <TrendingUp className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />}
        </div>
        <p className="text-4xl font-bold">
          {formatNumber(ibov.regularMarketPrice ?? 0)}
        </p>
        <p className={`text-lg mt-2 ${change >= 0 ? 'text-green-300' : 'text-red-300'}`}>
          {formatPercent(change)}
        </p>
        <div className="mt-4 grid grid-cols-2 gap-4 text-sm opacity-80">
          <div>
            <p className="opacity-70">Máxima</p>
            <p className="font-medium">{formatNumber(ibov.regularMarketDayHigh ?? 0)}</p>
          </div>
          <div>
            <p className="opacity-70">Mínima</p>
            <p className="font-medium">{formatNumber(ibov.regularMarketDayLow ?? 0)}</p>
          </div>
        </div>
      </div>
    );
  };

  const renderCurrencyCards = () => {
    const currencies = marketData?.currencies?.currency || [];
    
    return currencies.slice(0, 2).map((curr) => {
      const change = parseFloat(curr.percentageChange) || 0;
      const isUSD = curr.fromCurrency === 'USD';
      
      return (
        <div
          key={`${curr.fromCurrency}-${curr.toCurrency}`}
          className={`rounded-xl p-6 text-white ${
            isUSD
              ? 'bg-gradient-to-br from-green-500 to-emerald-600'
              : 'bg-gradient-to-br from-blue-500 to-cyan-600'
          }`}
        >
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Globe className="w-6 h-6" />
              <h3 className="font-semibold">{curr.fromCurrency}/BRL</h3>
            </div>
            {change >= 0 ? <TrendingUp className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />}
          </div>
          <p className="text-3xl font-bold">
            R$ {parseFloat(curr.bidPrice).toFixed(2)}
          </p>
          <p className={`text-lg mt-2 ${change >= 0 ? 'text-green-200' : 'text-red-200'}`}>
            {change >= 0 ? '+' : ''}{change.toFixed(2)}%
          </p>
        </div>
      );
    });
  };

  const renderCryptoCards = () => {
    const cryptos = marketData?.crypto?.coins || [];
    
    return cryptos.slice(0, 2).map((crypto) => {
      const change = crypto.regularMarketChangePercent ?? 0;
      const isBTC = crypto.coin === 'BTC';
      
      return (
        <div
          key={crypto.coin}
          className={`rounded-xl p-6 text-white ${
            isBTC
              ? 'bg-gradient-to-br from-orange-500 to-yellow-500'
              : 'bg-gradient-to-br from-purple-500 to-pink-500'
          }`}
        >
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Bitcoin className="w-6 h-6" />
              <h3 className="font-semibold">{crypto.coin}</h3>
            </div>
            {change >= 0 ? <TrendingUp className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />}
          </div>
          <p className="text-3xl font-bold">
            {formatCurrency(crypto.regularMarketPrice ?? 0)}
          </p>
          <p className={`text-lg mt-2 ${change >= 0 ? 'text-green-200' : 'text-red-200'}`}>
            {formatPercent(change)}
          </p>
        </div>
      );
    });
  };

  const renderIndicators = () => {
    const inflation = marketData?.inflation?.inflation?.[0];
    const selic = marketData?.selic?.['prime-rate']?.[0];
    
    return (
      <>
        <div className="bg-gradient-to-br from-red-500 to-orange-500 rounded-xl p-6 text-white">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-6 h-6" />
            <h3 className="font-semibold">Inflação (IPCA)</h3>
          </div>
          <p className="text-3xl font-bold">
            {inflation ? `${parseFloat(inflation.value).toFixed(2)}%` : '---'}
          </p>
          <p className="text-sm mt-2 opacity-80">
            {inflation?.date || ''}
          </p>
        </div>

        <div className="bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl p-6 text-white">
          <div className="flex items-center gap-2 mb-4">
            <Percent className="w-6 h-6" />
            <h3 className="font-semibold">Taxa SELIC</h3>
          </div>
          <p className="text-3xl font-bold">
            {selic ? `${parseFloat(selic.value).toFixed(2)}%` : '---'}
          </p>
          <p className="text-sm mt-2 opacity-80">
            {selic?.date || ''}
          </p>
        </div>
      </>
    );
  };

  const renderTopMovers = () => {
    const gainers = marketData?.topGainers?.stocks || [];
    const losers = marketData?.topLosers?.stocks || [];

    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Maiores Altas */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
          <div className="p-4 border-b border-gray-100 dark:border-gray-700 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-green-500" />
            <h3 className="font-semibold text-gray-900 dark:text-white">Maiores Altas</h3>
          </div>
          <div className="p-4 space-y-3">
            {gainers.slice(0, 5).map((stock) => (
              <div
                key={stock.symbol}
                className="flex items-center justify-between p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                <div className="flex items-center gap-2">
                  {stock.logourl && (
                    <img src={stock.logourl} alt={stock.symbol} className="w-6 h-6 rounded" />
                  )}
                  <span className="font-medium text-gray-900 dark:text-white">{stock.symbol}</span>
                </div>
                <div className="text-right">
                  <p className="font-medium text-gray-900 dark:text-white">
                    {formatCurrency(stock.regularMarketPrice ?? 0)}
                  </p>
                  <p className="text-sm text-green-500">
                    {formatPercent(stock.regularMarketChangePercent ?? 0)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Maiores Quedas */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
          <div className="p-4 border-b border-gray-100 dark:border-gray-700 flex items-center gap-2">
            <TrendingDown className="w-5 h-5 text-red-500" />
            <h3 className="font-semibold text-gray-900 dark:text-white">Maiores Quedas</h3>
          </div>
          <div className="p-4 space-y-3">
            {losers.slice(0, 5).map((stock) => (
              <div
                key={stock.symbol}
                className="flex items-center justify-between p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                <div className="flex items-center gap-2">
                  {stock.logourl && (
                    <img src={stock.logourl} alt={stock.symbol} className="w-6 h-6 rounded" />
                  )}
                  <span className="font-medium text-gray-900 dark:text-white">{stock.symbol}</span>
                </div>
                <div className="text-right">
                  <p className="font-medium text-gray-900 dark:text-white">
                    {formatCurrency(stock.regularMarketPrice ?? 0)}
                  </p>
                  <p className="text-sm text-red-500">
                    {formatPercent(stock.regularMarketChangePercent ?? 0)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <BarChart3 className="w-7 h-7 text-blue-600" />
            Visão Geral do Mercado
          </h1>
          <p className="text-gray-500 dark:text-gray-400">
            Resumo completo do mercado brasileiro em tempo real
          </p>
        </div>
        <div className="flex items-center gap-3">
          {marketData?.timestamp && (
            <span className="text-sm text-gray-500 dark:text-gray-400">
              Atualizado: {new Date(marketData.timestamp).toLocaleTimeString('pt-BR')}
            </span>
          )}
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Atualizar
          </button>
        </div>
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

      {/* Conteúdo */}
      {!loading && marketData && (
        <>
          {/* Cards principais */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {renderIndexCard()}
            {renderCurrencyCards()}
          </div>

          {/* Crypto e Indicadores */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {renderCryptoCards()}
            {renderIndicators()}
          </div>

          {/* Top Movers */}
          {renderTopMovers()}
        </>
      )}
    </div>
  );
};

export default MarketOverviewPage;
