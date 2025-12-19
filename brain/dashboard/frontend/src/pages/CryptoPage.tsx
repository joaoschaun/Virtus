/**
 * VIRTUS Trading System - Página de Criptomoedas
 * Cotações e dados de criptomoedas via Brapi
 */

import React, { useState, useEffect } from 'react';
import {
  Bitcoin,
  RefreshCw,
  Search,
  TrendingUp,
  TrendingDown,
  DollarSign,
  BarChart3,
} from 'lucide-react';
import {
  getCryptoQuote,
  listAvailableCryptos,
  formatCurrency,
  formatPercent,
  formatMarketCap,
  formatNumber,
  getChangeColor,
  getChangeBgColor,
  CryptoQuote,
} from '../services/brapiService';

const POPULAR_CRYPTOS = ['BTC', 'ETH', 'BNB', 'XRP', 'ADA', 'SOL', 'DOGE', 'DOT', 'MATIC', 'AVAX'];

const CryptoPage: React.FC = () => {
  const [cryptos, setCryptos] = useState<CryptoQuote[]>([]);
  const [availableCryptos, setAvailableCryptos] = useState<string[]>([]);
  const [selectedCrypto, setSelectedCrypto] = useState<CryptoQuote | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [currency, setCurrency] = useState<'BRL' | 'USD'>('BRL');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, [currency]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [cryptosRes, availableRes] = await Promise.all([
        getCryptoQuote(POPULAR_CRYPTOS, currency),
        listAvailableCryptos().catch(() => ({ coins: [] })),
      ]);

      setCryptos(cryptosRes.coins || []);
      setAvailableCryptos(availableRes.coins || []);
    } catch (err: any) {
      console.error('Erro ao carregar dados:', err);
      setError(err.message || 'Erro ao carregar dados');
    } finally {
      setLoading(false);
    }
  };

  const searchCrypto = async () => {
    if (!searchTerm.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const result = await getCryptoQuote([searchTerm.toUpperCase()], currency);
      if (result.coins && result.coins.length > 0) {
        setSelectedCrypto(result.coins[0]);
      } else {
        setError('Criptomoeda não encontrada');
      }
    } catch (err: any) {
      setError(err.message || 'Erro ao buscar criptomoeda');
    } finally {
      setLoading(false);
    }
  };

  const renderCryptoCard = (crypto: CryptoQuote) => {
    const change = crypto.regularMarketChangePercent ?? 0;
    const isPositive = change >= 0;

    return (
      <div
        key={crypto.coin}
        className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm hover:shadow-lg transition-all cursor-pointer border border-gray-100 dark:border-gray-700"
        onClick={() => setSelectedCrypto(crypto)}
      >
        <div className="flex items-center gap-3 mb-4">
          {crypto.coinImageUrl && (
            <img src={crypto.coinImageUrl} alt={crypto.coin} className="w-10 h-10 rounded-full" />
          )}
          <div>
            <h3 className="font-bold text-lg text-gray-900 dark:text-white">{crypto.coin}</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">{crypto.coinName}</p>
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-2xl font-bold text-gray-900 dark:text-white">
              {formatCurrency(crypto.regularMarketPrice ?? 0, currency)}
            </span>
            <div className={`flex items-center gap-1 ${getChangeColor(change)}`}>
              {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
              <span className="font-semibold">{formatPercent(change)}</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <p className="text-gray-500 dark:text-gray-400">Máxima 24h</p>
              <p className="font-medium text-green-600">
                {formatCurrency(crypto.regularMarketDayHigh ?? 0, currency)}
              </p>
            </div>
            <div>
              <p className="text-gray-500 dark:text-gray-400">Mínima 24h</p>
              <p className="font-medium text-red-600">
                {formatCurrency(crypto.regularMarketDayLow ?? 0, currency)}
              </p>
            </div>
          </div>

          <div className="pt-2 border-t border-gray-100 dark:border-gray-700">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Market Cap: {formatMarketCap(crypto.marketCap ?? 0)}
            </p>
          </div>
        </div>
      </div>
    );
  };

  const renderCryptoDetail = () => {
    if (!selectedCrypto) return null;

    const crypto = selectedCrypto;
    const change = crypto.regularMarketChangePercent ?? 0;

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white dark:bg-gray-800 rounded-xl max-w-lg w-full">
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                {crypto.coinImageUrl && (
                  <img src={crypto.coinImageUrl} alt={crypto.coin} className="w-12 h-12 rounded-full" />
                )}
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 dark:text-white">{crypto.coin}</h2>
                  <p className="text-gray-500 dark:text-gray-400">{crypto.coinName}</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedCrypto(null)}
                className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
              >
                ✕
              </button>
            </div>

            <div className="bg-gradient-to-r from-orange-500 to-yellow-500 rounded-lg p-5 mb-6 text-white">
              <p className="text-sm opacity-80">Preço Atual ({currency})</p>
              <p className="text-4xl font-bold">
                {formatCurrency(crypto.regularMarketPrice ?? 0, currency)}
              </p>
              <p className={`text-lg mt-1 ${change >= 0 ? 'text-green-200' : 'text-red-200'}`}>
                {formatPercent(change)} ({change >= 0 ? '+' : ''}
                {formatCurrency(crypto.regularMarketChange ?? 0, currency)})
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                <p className="text-xs text-gray-500 dark:text-gray-400">Máxima 24h</p>
                <p className="text-lg font-semibold text-green-600">
                  {formatCurrency(crypto.regularMarketDayHigh ?? 0, currency)}
                </p>
              </div>
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                <p className="text-xs text-gray-500 dark:text-gray-400">Mínima 24h</p>
                <p className="text-lg font-semibold text-red-600">
                  {formatCurrency(crypto.regularMarketDayLow ?? 0, currency)}
                </p>
              </div>
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                <p className="text-xs text-gray-500 dark:text-gray-400">Volume 24h</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-white">
                  {formatNumber(crypto.regularMarketVolume ?? 0)}
                </p>
              </div>
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                <p className="text-xs text-gray-500 dark:text-gray-400">Market Cap</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-white">
                  {formatMarketCap(crypto.marketCap ?? 0)}
                </p>
              </div>
            </div>

            <div className="text-center text-sm text-gray-500 dark:text-gray-400">
              Dados via Brapi API
            </div>
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
            <Bitcoin className="w-7 h-7 text-orange-500" />
            Criptomoedas
          </h1>
          <p className="text-gray-500 dark:text-gray-400">
            Cotações em tempo real das principais criptomoedas
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={currency}
            onChange={(e) => setCurrency(e.target.value as 'BRL' | 'USD')}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
          >
            <option value="BRL">R$ (BRL)</option>
            <option value="USD">$ (USD)</option>
          </select>
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Atualizar
          </button>
        </div>
      </div>

      {/* Busca */}
      <div className="flex gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar criptomoeda (ex: BTC, ETH, SOL)"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value.toUpperCase())}
            onKeyPress={(e) => e.key === 'Enter' && searchCrypto()}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-orange-500"
          />
        </div>
        <button
          onClick={searchCrypto}
          className="px-6 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600"
        >
          Buscar
        </button>
      </div>

      {/* Resumo */}
      {!loading && cryptos.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-gradient-to-r from-orange-500 to-yellow-500 rounded-lg p-4 text-white">
            <p className="text-sm opacity-80">Bitcoin (BTC)</p>
            <p className="text-xl font-bold">
              {formatCurrency(cryptos.find((c) => c.coin === 'BTC')?.regularMarketPrice ?? 0, currency)}
            </p>
          </div>
          <div className="bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg p-4 text-white">
            <p className="text-sm opacity-80">Ethereum (ETH)</p>
            <p className="text-xl font-bold">
              {formatCurrency(cryptos.find((c) => c.coin === 'ETH')?.regularMarketPrice ?? 0, currency)}
            </p>
          </div>
          <div className="bg-gradient-to-r from-yellow-500 to-orange-500 rounded-lg p-4 text-white">
            <p className="text-sm opacity-80">Total de Cryptos</p>
            <p className="text-xl font-bold">{cryptos.length}</p>
          </div>
          <div className="bg-gradient-to-r from-green-500 to-teal-500 rounded-lg p-4 text-white">
            <p className="text-sm opacity-80">Moeda</p>
            <p className="text-xl font-bold">{currency}</p>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-600 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="w-8 h-8 text-orange-500 animate-spin" />
        </div>
      )}

      {/* Grid de Criptomoedas */}
      {!loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {cryptos.map(renderCryptoCard)}
        </div>
      )}

      {/* Modal de Detalhes */}
      {selectedCrypto && renderCryptoDetail()}
    </div>
  );
};

export default CryptoPage;
