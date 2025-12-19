/**
 * VIRTUS Trading System - Página de FIIs
 * Fundos Imobiliários com cotações e dividendos
 */

import React, { useState, useEffect } from 'react';
import {
  Building,
  RefreshCw,
  Search,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Percent,
  Calendar,
} from 'lucide-react';
import {
  getFIIQuote,
  searchFIIs,
  formatCurrency,
  formatPercent,
  formatNumber,
  getChangeColor,
  getChangeBgColor,
  StockQuote,
} from '../services/brapiService';

const POPULAR_FIIS = [
  'HGLG11', 'MXRF11', 'XPLG11', 'XPML11', 'VISC11',
  'HGRE11', 'KNRI11', 'BCFF11', 'KNCR11', 'VRTA11',
  'BTLG11', 'VILG11', 'RBRP11', 'HGBS11', 'VINO11',
];

const FIIsPage: React.FC = () => {
  const [fiis, setFiis] = useState<StockQuote[]>([]);
  const [selectedFII, setSelectedFII] = useState<StockQuote | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getFIIQuote(POPULAR_FIIS, true);
      setFiis(result.results || []);
    } catch (err: any) {
      console.error('Erro ao carregar FIIs:', err);
      setError(err.message || 'Erro ao carregar dados');
    } finally {
      setLoading(false);
    }
  };

  const searchFII = async () => {
    if (!searchTerm.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const result = await getFIIQuote([searchTerm.toUpperCase()], true);
      if (result.results && result.results.length > 0) {
        setSelectedFII(result.results[0]);
      } else {
        setError('FII não encontrado');
      }
    } catch (err: any) {
      setError(err.message || 'Erro ao buscar FII');
    } finally {
      setLoading(false);
    }
  };

  const calculateDividendYield = (fii: StockQuote): number | null => {
    if (!fii.dividendsData?.cashDividends || fii.dividendsData.cashDividends.length === 0) {
      return null;
    }

    // Soma dos últimos 12 dividendos ou menos se não houver
    const lastDividends = fii.dividendsData.cashDividends.slice(0, 12);
    const totalDividends = lastDividends.reduce((sum, div) => sum + div.rate, 0);
    const annualizedDividends = (totalDividends / lastDividends.length) * 12;

    if (fii.regularMarketPrice && fii.regularMarketPrice > 0) {
      return (annualizedDividends / fii.regularMarketPrice) * 100;
    }
    return null;
  };

  const renderFIICard = (fii: StockQuote) => {
    const change = fii.regularMarketChangePercent ?? 0;
    const isPositive = change >= 0;
    const dividendYield = calculateDividendYield(fii);
    const lastDividend = fii.dividendsData?.cashDividends?.[0];

    return (
      <div
        key={fii.symbol}
        className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm hover:shadow-lg transition-all cursor-pointer border border-gray-100 dark:border-gray-700"
        onClick={() => setSelectedFII(fii)}
      >
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-purple-100 dark:bg-purple-900 flex items-center justify-center">
              <Building className="w-6 h-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h3 className="font-bold text-lg text-gray-900 dark:text-white">{fii.symbol}</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-[150px]">
                {fii.shortName || fii.longName}
              </p>
            </div>
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-2xl font-bold text-gray-900 dark:text-white">
              {formatCurrency(fii.regularMarketPrice ?? 0)}
            </span>
            <div className={`flex items-center gap-1 ${getChangeColor(change)}`}>
              {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
              <span className="font-semibold">{formatPercent(change)}</span>
            </div>
          </div>

          {/* Dividend Yield */}
          {dividendYield !== null && (
            <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-green-700 dark:text-green-400 flex items-center gap-1">
                  <Percent className="w-4 h-4" />
                  DY (12m)
                </span>
                <span className="font-bold text-green-700 dark:text-green-400">
                  {dividendYield.toFixed(2)}%
                </span>
              </div>
            </div>
          )}

          {/* Último Rendimento */}
          {lastDividend && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-500 dark:text-gray-400">Último Rendimento</span>
              <span className="font-medium text-green-600">
                {formatCurrency(lastDividend.rate)} / cota
              </span>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderFIIDetail = () => {
    if (!selectedFII) return null;

    const fii = selectedFII;
    const change = fii.regularMarketChangePercent ?? 0;
    const dividendYield = calculateDividendYield(fii);

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white dark:bg-gray-800 rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-lg bg-purple-100 dark:bg-purple-900 flex items-center justify-center">
                  <Building className="w-7 h-7 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 dark:text-white">{fii.symbol}</h2>
                  <p className="text-gray-500 dark:text-gray-400">{fii.longName || fii.shortName}</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedFII(null)}
                className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
              >
                ✕
              </button>
            </div>

            {/* Preço e Variação */}
            <div className="bg-gradient-to-r from-purple-500 to-indigo-500 rounded-lg p-5 mb-6 text-white">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm opacity-80">Cotação Atual</p>
                  <p className="text-4xl font-bold">
                    {formatCurrency(fii.regularMarketPrice ?? 0)}
                  </p>
                </div>
                <div className="text-right">
                  <p className={`text-2xl font-bold ${change >= 0 ? 'text-green-200' : 'text-red-200'}`}>
                    {formatPercent(change)}
                  </p>
                  {dividendYield !== null && (
                    <p className="text-sm opacity-80">DY: {dividendYield.toFixed(2)}% a.a.</p>
                  )}
                </div>
              </div>
            </div>

            {/* Grid de informações */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
                <p className="text-xs text-gray-500 dark:text-gray-400">Abertura</p>
                <p className="font-semibold text-gray-900 dark:text-white">
                  {formatCurrency(fii.regularMarketOpen ?? 0)}
                </p>
              </div>
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
                <p className="text-xs text-gray-500 dark:text-gray-400">Máxima</p>
                <p className="font-semibold text-green-600">
                  {formatCurrency(fii.regularMarketDayHigh ?? 0)}
                </p>
              </div>
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
                <p className="text-xs text-gray-500 dark:text-gray-400">Mínima</p>
                <p className="font-semibold text-red-600">
                  {formatCurrency(fii.regularMarketDayLow ?? 0)}
                </p>
              </div>
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
                <p className="text-xs text-gray-500 dark:text-gray-400">Volume</p>
                <p className="font-semibold text-gray-900 dark:text-white">
                  {formatNumber(fii.regularMarketVolume ?? 0)}
                </p>
              </div>
            </div>

            {/* Histórico de Rendimentos */}
            {fii.dividendsData?.cashDividends && fii.dividendsData.cashDividends.length > 0 && (
              <div className="border-t border-gray-200 dark:border-gray-600 pt-4">
                <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                  <DollarSign className="w-5 h-5 text-green-500" />
                  Histórico de Rendimentos
                </h3>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {fii.dividendsData.cashDividends.slice(0, 12).map((div, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between bg-gray-50 dark:bg-gray-700 rounded-lg p-3"
                    >
                      <div className="flex items-center gap-3">
                        <Calendar className="w-4 h-4 text-gray-400" />
                        <div>
                          <p className="font-medium text-gray-900 dark:text-white">
                            {new Date(div.paymentDate).toLocaleDateString('pt-BR')}
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">{div.label}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="font-bold text-green-600">
                          {formatCurrency(div.rate)}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">por cota</p>
                      </div>
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

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Building className="w-7 h-7 text-purple-600" />
            Fundos Imobiliários (FIIs)
          </h1>
          <p className="text-gray-500 dark:text-gray-400">
            Cotações e rendimentos dos principais FIIs da B3
          </p>
        </div>
        <button
          onClick={loadData}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
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
            placeholder="Buscar FII (ex: HGLG11, MXRF11)"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value.toUpperCase())}
            onKeyPress={(e) => e.key === 'Enter' && searchFII()}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500"
          />
        </div>
        <button
          onClick={searchFII}
          className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
        >
          Buscar
        </button>
      </div>

      {/* Resumo */}
      {!loading && fiis.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-gradient-to-r from-purple-500 to-indigo-500 rounded-lg p-4 text-white">
            <p className="text-sm opacity-80">FIIs Monitorados</p>
            <p className="text-2xl font-bold">{fiis.length}</p>
          </div>
          <div className="bg-gradient-to-r from-green-500 to-emerald-500 rounded-lg p-4 text-white">
            <p className="text-sm opacity-80">Em Alta</p>
            <p className="text-2xl font-bold">
              {fiis.filter((f) => (f.regularMarketChangePercent ?? 0) > 0).length}
            </p>
          </div>
          <div className="bg-gradient-to-r from-red-500 to-pink-500 rounded-lg p-4 text-white">
            <p className="text-sm opacity-80">Em Baixa</p>
            <p className="text-2xl font-bold">
              {fiis.filter((f) => (f.regularMarketChangePercent ?? 0) < 0).length}
            </p>
          </div>
          <div className="bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg p-4 text-white">
            <p className="text-sm opacity-80">Estáveis</p>
            <p className="text-2xl font-bold">
              {fiis.filter((f) => (f.regularMarketChangePercent ?? 0) === 0).length}
            </p>
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
          <RefreshCw className="w-8 h-8 text-purple-600 animate-spin" />
        </div>
      )}

      {/* Grid de FIIs */}
      {!loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {fiis.map(renderFIICard)}
        </div>
      )}

      {/* Modal de Detalhes */}
      {selectedFII && renderFIIDetail()}
    </div>
  );
};

export default FIIsPage;
