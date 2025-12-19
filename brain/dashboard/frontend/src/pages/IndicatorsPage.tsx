/**
 * VIRTUS Trading System - Página de Indicadores Econômicos
 * Inflação (IPCA) e Taxa SELIC
 */

import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  TrendingDown,
  RefreshCw,
  Percent,
  Calendar,
  BarChart3,
  Activity,
} from 'lucide-react';
import {
  getInflation,
  getSelic,
  InflationData,
  PrimeRateData,
} from '../services/brapiService';

const IndicatorsPage: React.FC = () => {
  const [inflationData, setInflationData] = useState<InflationData[]>([]);
  const [selicData, setSelicData] = useState<PrimeRateData[]>([]);
  const [currentInflation, setCurrentInflation] = useState<InflationData | null>(null);
  const [currentSelic, setCurrentSelic] = useState<PrimeRateData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'selic' | 'inflation'>('selic');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      // Brapi API requer historical=true para inflação
      // SELIC não suporta mais historical=true, apenas retorna valor atual
      const [inflationHistory, selicCurrent] = await Promise.all([
        getInflation({ historical: true, sortBy: 'date', sortOrder: 'desc' }),
        getSelic(), // Sem parâmetros - retorna apenas valor atual
      ]);

      // Dados atuais - pegar o primeiro do histórico para inflação
      if (inflationHistory.inflation && inflationHistory.inflation.length > 0) {
        setCurrentInflation(inflationHistory.inflation[0]);
      }
      if (selicCurrent['prime-rate'] && selicCurrent['prime-rate'].length > 0) {
        setCurrentSelic(selicCurrent['prime-rate'][0]);
        // SELIC histórico não disponível na API - usar apenas valor atual
        setSelicData(selicCurrent['prime-rate']);
      }

      // Histórico da inflação
      setInflationData(inflationHistory.inflation || []);
    } catch (err: any) {
      console.error('Erro ao carregar indicadores:', err);
      setError(err.message || 'Erro ao carregar dados');
    } finally {
      setLoading(false);
    }
  };

  const renderIndicatorCard = (
    title: string,
    value: string,
    description: string,
    icon: React.ReactNode,
    color: string,
    trend?: 'up' | 'down' | 'neutral'
  ) => (
    <div className={`${color} rounded-xl p-6 text-white`}>
      <div className="flex items-center justify-between mb-4">
        <div className="p-2 bg-white/20 rounded-lg">{icon}</div>
        {trend && (
          <div className={`flex items-center gap-1 ${
            trend === 'up' ? 'text-red-200' : trend === 'down' ? 'text-green-200' : 'text-gray-200'
          }`}>
            {trend === 'up' ? <TrendingUp className="w-5 h-5" /> : 
             trend === 'down' ? <TrendingDown className="w-5 h-5" /> :
             <Activity className="w-5 h-5" />}
          </div>
        )}
      </div>
      <h3 className="text-sm opacity-80">{title}</h3>
      <p className="text-4xl font-bold mt-1">{value}</p>
      <p className="text-sm opacity-70 mt-2">{description}</p>
    </div>
  );

  const renderHistoryTable = (
    data: (InflationData | PrimeRateData)[],
    title: string
  ) => (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
      <div className="p-4 border-b border-gray-100 dark:border-gray-700">
        <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <Calendar className="w-5 h-5" />
          {title}
        </h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">
                Data
              </th>
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-500 dark:text-gray-400">
                Valor
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
            {data.slice(0, 24).map((item, idx) => (
              <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                <td className="px-4 py-3 text-sm text-gray-900 dark:text-white">
                  {item.date}
                </td>
                <td className="px-4 py-3 text-sm text-right font-semibold text-gray-900 dark:text-white">
                  {parseFloat(item.value).toFixed(2)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );

  const renderMiniChart = (data: (InflationData | PrimeRateData)[], color: string) => {
    if (data.length === 0) return null;
    
    const values = data.slice(0, 12).reverse().map(d => parseFloat(d.value));
    const max = Math.max(...values);
    const min = Math.min(...values);
    const range = max - min || 1;

    return (
      <div className="flex items-end gap-1 h-16">
        {values.map((value, idx) => {
          const height = ((value - min) / range) * 100;
          return (
            <div
              key={idx}
              className={`${color} rounded-t opacity-80 hover:opacity-100 transition-opacity`}
              style={{
                width: `${100 / values.length}%`,
                height: `${Math.max(height, 10)}%`,
              }}
              title={`${value.toFixed(2)}%`}
            />
          );
        })}
      </div>
    );
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <BarChart3 className="w-7 h-7 text-indigo-600" />
            Indicadores Econômicos
          </h1>
          <p className="text-gray-500 dark:text-gray-400">
            Taxa SELIC e Inflação (IPCA) - Brasil
          </p>
        </div>
        <button
          onClick={loadData}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Atualizar
        </button>
      </div>

      {/* Cards principais */}
      {!loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {renderIndicatorCard(
            'Taxa SELIC',
            currentSelic ? `${parseFloat(currentSelic.value).toFixed(2)}%` : '---',
            'Taxa básica de juros da economia brasileira',
            <Percent className="w-6 h-6" />,
            'bg-gradient-to-r from-blue-600 to-indigo-600',
            'neutral'
          )}
          {renderIndicatorCard(
            'Inflação (IPCA)',
            currentInflation ? `${parseFloat(currentInflation.value).toFixed(2)}%` : '---',
            'Índice de Preços ao Consumidor Amplo',
            <TrendingUp className="w-6 h-6" />,
            'bg-gradient-to-r from-orange-500 to-red-500',
            parseFloat(currentInflation?.value || '0') > 4.5 ? 'up' : 'down'
          )}
        </div>
      )}

      {/* Mini gráficos */}
      {!loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-gray-700">
            <h3 className="font-semibold text-gray-900 dark:text-white mb-4">
              SELIC - Últimos 12 meses
            </h3>
            {renderMiniChart(selicData, 'bg-blue-500')}
            <div className="flex justify-between mt-2 text-xs text-gray-500 dark:text-gray-400">
              <span>12 meses atrás</span>
              <span>Atual</span>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-gray-700">
            <h3 className="font-semibold text-gray-900 dark:text-white mb-4">
              IPCA - Últimos 12 meses
            </h3>
            {renderMiniChart(inflationData, 'bg-orange-500')}
            <div className="flex justify-between mt-2 text-xs text-gray-500 dark:text-gray-400">
              <span>12 meses atrás</span>
              <span>Atual</span>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={() => setActiveTab('selic')}
          className={`flex items-center gap-2 px-4 py-2 border-b-2 transition-colors ${
            activeTab === 'selic'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
          }`}
        >
          <Percent className="w-4 h-4" />
          Taxa SELIC
        </button>
        <button
          onClick={() => setActiveTab('inflation')}
          className={`flex items-center gap-2 px-4 py-2 border-b-2 transition-colors ${
            activeTab === 'inflation'
              ? 'border-orange-500 text-orange-500'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
          }`}
        >
          <TrendingUp className="w-4 h-4" />
          Inflação (IPCA)
        </button>
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
          <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin" />
        </div>
      )}

      {/* Tabela de histórico */}
      {!loading && activeTab === 'selic' && (
        renderHistoryTable(selicData, 'Histórico da Taxa SELIC')
      )}
      {!loading && activeTab === 'inflation' && (
        renderHistoryTable(inflationData, 'Histórico da Inflação (IPCA)')
      )}

      {/* Info adicional */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl p-6 border border-blue-200 dark:border-blue-800">
          <h3 className="font-semibold text-blue-900 dark:text-blue-300 mb-2">
            O que é a Taxa SELIC?
          </h3>
          <p className="text-sm text-blue-800 dark:text-blue-400">
            A SELIC (Sistema Especial de Liquidação e Custódia) é a taxa básica de juros da economia brasileira.
            É definida pelo COPOM (Comitê de Política Monetária) do Banco Central e serve como referência
            para todas as outras taxas de juros do país.
          </p>
        </div>

        <div className="bg-orange-50 dark:bg-orange-900/20 rounded-xl p-6 border border-orange-200 dark:border-orange-800">
          <h3 className="font-semibold text-orange-900 dark:text-orange-300 mb-2">
            O que é o IPCA?
          </h3>
          <p className="text-sm text-orange-800 dark:text-orange-400">
            O IPCA (Índice Nacional de Preços ao Consumidor Amplo) é o índice oficial de inflação do Brasil.
            Mede a variação de preços de uma cesta de produtos e serviços consumidos pelas famílias
            brasileiras com renda entre 1 e 40 salários mínimos.
          </p>
        </div>
      </div>
    </div>
  );
};

export default IndicatorsPage;
