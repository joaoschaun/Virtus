/**
 * VIRTUS Trading System - Página de Câmbio
 * Cotações de moedas em tempo real
 */

import React, { useState, useEffect } from 'react';
import {
  DollarSign,
  RefreshCw,
  ArrowRightLeft,
  TrendingUp,
  TrendingDown,
  Globe,
  Calculator,
} from 'lucide-react';
import {
  getCurrencyQuote,
  listAvailableCurrencies,
  formatNumber,
  CurrencyQuote,
} from '../services/brapiService';

const POPULAR_PAIRS = [
  'USD-BRL',
  'EUR-BRL',
  'GBP-BRL',
  'JPY-BRL',
  'CHF-BRL',
  'AUD-BRL',
  'CAD-BRL',
  'ARS-BRL',
  'CNY-BRL',
  'BTC-BRL',
];

const FLAG_EMOJIS: Record<string, string> = {
  USD: '🇺🇸',
  EUR: '🇪🇺',
  GBP: '🇬🇧',
  JPY: '🇯🇵',
  CHF: '🇨🇭',
  AUD: '🇦🇺',
  CAD: '🇨🇦',
  ARS: '🇦🇷',
  CNY: '🇨🇳',
  BRL: '🇧🇷',
  BTC: '₿',
  ETH: 'Ξ',
};

const CurrencyPage: React.FC = () => {
  const [currencies, setCurrencies] = useState<CurrencyQuote[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Conversor
  const [fromCurrency, setFromCurrency] = useState('USD');
  const [toCurrency, setToCurrency] = useState('BRL');
  const [amount, setAmount] = useState<number>(1);
  const [convertedValue, setConvertedValue] = useState<number | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    calculateConversion();
  }, [amount, fromCurrency, toCurrency, currencies]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getCurrencyQuote(POPULAR_PAIRS);
      setCurrencies(result.currency || []);
    } catch (err: any) {
      console.error('Erro ao carregar moedas:', err);
      setError(err.message || 'Erro ao carregar dados');
    } finally {
      setLoading(false);
    }
  };

  const calculateConversion = () => {
    const pair = `${fromCurrency}-${toCurrency}`;
    const currency = currencies.find((c) => `${c.fromCurrency}-${c.toCurrency}` === pair);
    
    if (currency) {
      const rate = parseFloat(currency.bidPrice);
      setConvertedValue(amount * rate);
    } else if (fromCurrency === toCurrency) {
      setConvertedValue(amount);
    } else {
      setConvertedValue(null);
    }
  };

  const swapCurrencies = () => {
    setFromCurrency(toCurrency);
    setToCurrency(fromCurrency);
  };

  const getFlag = (currency: string) => FLAG_EMOJIS[currency] || '💱';

  const renderCurrencyCard = (currency: CurrencyQuote) => {
    const change = parseFloat(currency.percentageChange) || 0;
    const isPositive = change >= 0;

    return (
      <div
        key={`${currency.fromCurrency}-${currency.toCurrency}`}
        className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm hover:shadow-lg transition-all border border-gray-100 dark:border-gray-700"
      >
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="text-3xl">
              {getFlag(currency.fromCurrency)}
            </div>
            <div>
              <h3 className="font-bold text-lg text-gray-900 dark:text-white">
                {currency.fromCurrency}/{currency.toCurrency}
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">{currency.name}</p>
            </div>
          </div>
          {isPositive ? (
            <TrendingUp className="w-5 h-5 text-green-500" />
          ) : (
            <TrendingDown className="w-5 h-5 text-red-500" />
          )}
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-2xl font-bold text-gray-900 dark:text-white">
              R$ {parseFloat(currency.bidPrice).toFixed(4)}
            </span>
            <span className={`text-sm font-medium px-2 py-1 rounded ${
              isPositive ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
            }`}>
              {isPositive ? '+' : ''}{change.toFixed(2)}%
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <p className="text-gray-500 dark:text-gray-400">Compra</p>
              <p className="font-medium text-gray-900 dark:text-white">
                R$ {parseFloat(currency.bidPrice).toFixed(4)}
              </p>
            </div>
            <div>
              <p className="text-gray-500 dark:text-gray-400">Venda</p>
              <p className="font-medium text-gray-900 dark:text-white">
                R$ {parseFloat(currency.askPrice).toFixed(4)}
              </p>
            </div>
            <div>
              <p className="text-gray-500 dark:text-gray-400">Máxima</p>
              <p className="font-medium text-green-600">
                R$ {parseFloat(currency.high).toFixed(4)}
              </p>
            </div>
            <div>
              <p className="text-gray-500 dark:text-gray-400">Mínima</p>
              <p className="font-medium text-red-600">
                R$ {parseFloat(currency.low).toFixed(4)}
              </p>
            </div>
          </div>

          <div className="pt-2 border-t border-gray-100 dark:border-gray-700 text-xs text-gray-500 dark:text-gray-400">
            Atualizado: {currency.updatedAtDate}
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
            <Globe className="w-7 h-7 text-green-600" />
            Câmbio / Moedas
          </h1>
          <p className="text-gray-500 dark:text-gray-400">
            Cotações de moedas em tempo real
          </p>
        </div>
        <button
          onClick={loadData}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Atualizar
        </button>
      </div>

      {/* Conversor */}
      <div className="bg-gradient-to-r from-green-500 to-teal-500 rounded-xl p-6 text-white">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Calculator className="w-5 h-5" />
          Conversor de Moedas
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 items-center">
          <div className="md:col-span-2">
            <label className="block text-sm opacity-80 mb-1">De</label>
            <div className="flex gap-2">
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(parseFloat(e.target.value) || 0)}
                className="flex-1 px-4 py-2 rounded-lg bg-white/20 border border-white/30 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-white/50"
              />
              <select
                value={fromCurrency}
                onChange={(e) => setFromCurrency(e.target.value)}
                className="px-3 py-2 rounded-lg bg-white/20 border border-white/30 text-white focus:outline-none"
              >
                {['USD', 'EUR', 'GBP', 'BRL', 'JPY', 'CHF', 'AUD', 'CAD'].map((c) => (
                  <option key={c} value={c} className="text-gray-900">
                    {c}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex justify-center">
            <button
              onClick={swapCurrencies}
              className="p-2 rounded-full bg-white/20 hover:bg-white/30 transition-colors"
            >
              <ArrowRightLeft className="w-5 h-5" />
            </button>
          </div>

          <div className="md:col-span-2">
            <label className="block text-sm opacity-80 mb-1">Para</label>
            <div className="flex gap-2">
              <div className="flex-1 px-4 py-2 rounded-lg bg-white/20 border border-white/30 text-white font-bold text-xl">
                {convertedValue !== null ? convertedValue.toFixed(2) : '---'}
              </div>
              <select
                value={toCurrency}
                onChange={(e) => setToCurrency(e.target.value)}
                className="px-3 py-2 rounded-lg bg-white/20 border border-white/30 text-white focus:outline-none"
              >
                {['BRL', 'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD'].map((c) => (
                  <option key={c} value={c} className="text-gray-900">
                    {c}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Destaques */}
      {!loading && currencies.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {currencies.slice(0, 4).map((currency) => (
            <div
              key={`highlight-${currency.fromCurrency}`}
              className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-100 dark:border-gray-700"
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="text-2xl">{getFlag(currency.fromCurrency)}</span>
                <span className="font-bold text-gray-900 dark:text-white">
                  {currency.fromCurrency}/BRL
                </span>
              </div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                R$ {parseFloat(currency.bidPrice).toFixed(2)}
              </p>
              <p className={`text-sm ${parseFloat(currency.percentageChange) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {parseFloat(currency.percentageChange) >= 0 ? '+' : ''}
                {parseFloat(currency.percentageChange).toFixed(2)}%
              </p>
            </div>
          ))}
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
          <RefreshCw className="w-8 h-8 text-green-600 animate-spin" />
        </div>
      )}

      {/* Grid de Moedas */}
      {!loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {currencies.map(renderCurrencyCard)}
        </div>
      )}
    </div>
  );
};

export default CurrencyPage;
