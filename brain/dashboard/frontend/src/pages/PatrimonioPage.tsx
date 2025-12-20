import { useState, useEffect } from 'react';
import { 
  TrendingUp, TrendingDown, Wallet, PieChart, 
  BarChart2, DollarSign, Activity, RefreshCw,
  Building2, Landmark, Globe, Plus
} from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart as RechartsPie, Pie, Cell, Legend,
  AreaChart, Area
} from 'recharts';

interface PatrimonioResumo {
  total: number;
  mt4_balance: number;
  mt4_balance_usd: number;
  mt4_profit: number;
  mt4_profit_usd: number;
  cotacao_dolar: number;
  acoes_valor: number;
  acoes_lucro: number;
  fiis_valor: number;
  fiis_lucro: number;
  dividendos_recebidos: number;
  outros: number;
  variacao_dia: number;
  variacao_dia_pct: number;
  variacao_mes: number;
  variacao_mes_pct: number;
}

interface Composicao {
  mt4: { valor: number; valor_usd?: number; percentual: number; cotacao?: number };
  acoes: { valor: number; percentual: number };
  fiis: { valor: number; percentual: number };
  outros: { valor: number; percentual: number };
}

interface HistoricoItem {
  date: string;
  total: number;
  mt4_balance: number;
  acoes_valor: number;
  fiis_valor: number;
  outros: number;
}

const COLORS = ['#F59E0B', '#10B981', '#3B82F6', '#8B5CF6'];

export default function PatrimonioPage() {
  const [resumo, setResumo] = useState<PatrimonioResumo | null>(null);
  const [composicao, setComposicao] = useState<Composicao | null>(null);
  const [historico, setHistorico] = useState<HistoricoItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [dias, setDias] = useState(30);
  const [showAddOutros, setShowAddOutros] = useState(false);
  const [outrosValor, setOutrosValor] = useState('');

  useEffect(() => {
    loadData();
  }, [dias]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [resumoRes, composicaoRes, historicoRes] = await Promise.all([
        fetch('/api/patrimonio/resumo'),
        fetch('/api/patrimonio/composicao'),
        fetch(`/api/patrimonio/historico?days=${dias}`)
      ]);

      const resumoData = await resumoRes.json();
      const composicaoData = await composicaoRes.json();
      const historicoData = await historicoRes.json();

      if (resumoData.success) setResumo(resumoData.data);
      if (composicaoData.success) setComposicao(composicaoData.data);
      if (historicoData.success) setHistorico(historicoData.data);
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
    } finally {
      setLoading(false);
    }
  };

  const atualizarOutros = async () => {
    try {
      const response = await fetch('/api/patrimonio/outros', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ valor: parseFloat(outrosValor) })
      });
      
      if (response.ok) {
        setShowAddOutros(false);
        setOutrosValor('');
        loadData();
      }
    } catch (error) {
      console.error('Erro ao atualizar:', error);
    }
  };

  const formatCurrency = (value: number, currency: string = 'BRL') => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: currency
    }).format(value);
  };

  const pieData = composicao ? [
    { name: 'MT4 Trading', value: composicao.mt4.valor, pct: composicao.mt4.percentual },
    { name: 'Ações', value: composicao.acoes.valor, pct: composicao.acoes.percentual },
    { name: 'FIIs', value: composicao.fiis.valor, pct: composicao.fiis.percentual },
    { name: 'Outros', value: composicao.outros.valor, pct: composicao.outros.percentual },
  ].filter(item => item.value > 0) : [];

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-amber-500 animate-spin mx-auto" />
          <p className="text-gray-400 mt-4">Carregando patrimônio...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-amber-500">Desenvolvimento Patrimonial</h1>
            <p className="text-gray-400 mt-1">Visão consolidada do seu patrimônio</p>
          </div>
          <div className="flex gap-3">
            <select
              value={dias}
              onChange={(e) => setDias(Number(e.target.value))}
              className="bg-gray-800 text-white px-4 py-2 rounded-lg border border-gray-700"
            >
              <option value={7}>7 dias</option>
              <option value={30}>30 dias</option>
              <option value={90}>90 dias</option>
              <option value={365}>1 ano</option>
            </select>
            <button
              onClick={loadData}
              className="bg-amber-600 hover:bg-amber-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Atualizar
            </button>
          </div>
        </div>

        {/* Cards principais */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Patrimônio Total */}
          <div className="bg-gradient-to-br from-amber-600 to-amber-700 rounded-xl p-6 text-white">
            <div className="flex items-center justify-between mb-4">
              <span className="text-amber-200">Patrimônio Total</span>
              <Wallet className="w-6 h-6 text-amber-200" />
            </div>
            <p className="text-3xl font-bold">
              {formatCurrency(resumo?.total || 0)}
            </p>
            <p className="text-xs text-amber-200 mt-1">
              Dólar: R$ {(resumo?.cotacao_dolar || 0).toFixed(2)}
            </p>
            <div className="flex items-center gap-2 mt-2">
              {(resumo?.variacao_mes || 0) >= 0 ? (
                <TrendingUp className="w-4 h-4 text-green-300" />
              ) : (
                <TrendingDown className="w-4 h-4 text-red-300" />
              )}
              <span className={`text-sm ${(resumo?.variacao_mes || 0) >= 0 ? 'text-green-300' : 'text-red-300'}`}>
                {formatCurrency(resumo?.variacao_mes || 0)} ({(resumo?.variacao_mes_pct || 0).toFixed(2)}%) este mês
              </span>
            </div>
          </div>

          {/* MT4 Trading */}
          <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
            <div className="flex items-center justify-between mb-4">
              <span className="text-gray-400">MT4 Trading</span>
              <Globe className="w-5 h-5 text-amber-500" />
            </div>
            <p className="text-2xl font-bold text-white">
              {formatCurrency(resumo?.mt4_balance || 0)}
            </p>
            <p className="text-sm text-gray-400 mt-1">
              {formatCurrency(resumo?.mt4_balance_usd || 0, 'USD')} × R$ {(resumo?.cotacao_dolar || 0).toFixed(2)}
            </p>
            <p className={`text-sm mt-2 ${(resumo?.mt4_profit || 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              Lucro: {formatCurrency(resumo?.mt4_profit || 0)} ({formatCurrency(resumo?.mt4_profit_usd || 0, 'USD')})
            </p>
          </div>

          {/* Ações */}
          <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
            <div className="flex items-center justify-between mb-4">
              <span className="text-gray-400">Ações</span>
              <Activity className="w-5 h-5 text-green-500" />
            </div>
            <p className="text-2xl font-bold text-white">
              {formatCurrency(resumo?.acoes_valor || 0)}
            </p>
            <p className={`text-sm mt-2 ${(resumo?.acoes_lucro || 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              {(resumo?.acoes_lucro || 0) >= 0 ? '+' : ''}{formatCurrency(resumo?.acoes_lucro || 0)}
            </p>
          </div>

          {/* FIIs */}
          <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
            <div className="flex items-center justify-between mb-4">
              <span className="text-gray-400">Fundos Imobiliários</span>
              <Building2 className="w-5 h-5 text-blue-500" />
            </div>
            <p className="text-2xl font-bold text-white">
              {formatCurrency(resumo?.fiis_valor || 0)}
            </p>
            <p className={`text-sm mt-2 ${(resumo?.fiis_lucro || 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              {(resumo?.fiis_lucro || 0) >= 0 ? '+' : ''}{formatCurrency(resumo?.fiis_lucro || 0)}
            </p>
          </div>
        </div>

        {/* Métricas adicionais */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Dividendos */}
          <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
            <div className="flex items-center justify-between mb-4">
              <span className="text-gray-400">Dividendos Recebidos</span>
              <DollarSign className="w-5 h-5 text-green-500" />
            </div>
            <p className="text-2xl font-bold text-green-500">
              {formatCurrency(resumo?.dividendos_recebidos || 0)}
            </p>
            <p className="text-sm text-gray-500 mt-2">
              Total acumulado
            </p>
          </div>

          {/* Outros */}
          <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
            <div className="flex items-center justify-between mb-4">
              <span className="text-gray-400">Outros Ativos</span>
              <button 
                onClick={() => setShowAddOutros(true)}
                className="text-amber-500 hover:text-amber-400"
              >
                <Plus className="w-5 h-5" />
              </button>
            </div>
            <p className="text-2xl font-bold text-white">
              {formatCurrency(resumo?.outros || 0)}
            </p>
            <p className="text-sm text-gray-500 mt-2">
              Poupança, CDB, etc.
            </p>
          </div>

          {/* Variação Dia */}
          <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
            <div className="flex items-center justify-between mb-4">
              <span className="text-gray-400">Variação Hoje</span>
              {(resumo?.variacao_dia || 0) >= 0 ? (
                <TrendingUp className="w-5 h-5 text-green-500" />
              ) : (
                <TrendingDown className="w-5 h-5 text-red-500" />
              )}
            </div>
            <p className={`text-2xl font-bold ${(resumo?.variacao_dia || 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              {(resumo?.variacao_dia || 0) >= 0 ? '+' : ''}{formatCurrency(resumo?.variacao_dia || 0)}
            </p>
            <p className="text-sm text-gray-500 mt-2">
              {(resumo?.variacao_dia_pct || 0).toFixed(2)}%
            </p>
          </div>
        </div>

        {/* Gráficos */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Evolução do Patrimônio */}
          <div className="lg:col-span-2 bg-gray-800 rounded-xl p-6 border border-gray-700">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <BarChart2 className="w-5 h-5 text-amber-500" />
              Evolução do Patrimônio
            </h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={historico}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis 
                    dataKey="date" 
                    stroke="#9CA3AF"
                    tickFormatter={(value) => {
                      const date = new Date(value);
                      return `${date.getDate()}/${date.getMonth() + 1}`;
                    }}
                  />
                  <YAxis 
                    stroke="#9CA3AF"
                    tickFormatter={(value) => `R$ ${(value / 1000).toFixed(0)}k`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1F2937',
                      border: '1px solid #374151',
                      borderRadius: '8px'
                    }}
                    formatter={(value: number) => [formatCurrency(value), '']}
                    labelFormatter={(label) => new Date(label).toLocaleDateString('pt-BR')}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="total" 
                    stroke="#F59E0B" 
                    fill="#F59E0B" 
                    fillOpacity={0.3}
                    name="Total"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Composição */}
          <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <PieChart className="w-5 h-5 text-amber-500" />
              Composição
            </h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <RechartsPie>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={5}
                    dataKey="value"
                    label={({ pct }) => `${pct.toFixed(1)}%`}
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1F2937',
                      border: '1px solid #374151',
                      borderRadius: '8px'
                    }}
                    formatter={(value: number) => formatCurrency(value)}
                  />
                  <Legend 
                    verticalAlign="bottom"
                    formatter={(value) => <span className="text-gray-300">{value}</span>}
                  />
                </RechartsPie>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Detalhamento por categoria */}
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">Detalhamento por Categoria</h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-gray-400 border-b border-gray-700">
                  <th className="pb-3">Categoria</th>
                  <th className="pb-3 text-right">Valor</th>
                  <th className="pb-3 text-right">% do Total</th>
                  <th className="pb-3 text-right">Lucro/Prejuízo</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-gray-700/50">
                  <td className="py-4 flex items-center gap-3">
                    <div className="w-3 h-3 rounded-full bg-amber-500"></div>
                    <span className="text-white">MT4 Trading (XAUUSD)</span>
                  </td>
                  <td className="py-4 text-right text-white">{formatCurrency(resumo?.mt4_balance || 0, 'USD')}</td>
                  <td className="py-4 text-right text-gray-400">{composicao?.mt4.percentual.toFixed(1)}%</td>
                  <td className={`py-4 text-right ${(resumo?.mt4_profit || 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {formatCurrency(resumo?.mt4_profit || 0, 'USD')}
                  </td>
                </tr>
                <tr className="border-b border-gray-700/50">
                  <td className="py-4 flex items-center gap-3">
                    <div className="w-3 h-3 rounded-full bg-green-500"></div>
                    <span className="text-white">Ações</span>
                  </td>
                  <td className="py-4 text-right text-white">{formatCurrency(resumo?.acoes_valor || 0)}</td>
                  <td className="py-4 text-right text-gray-400">{composicao?.acoes.percentual.toFixed(1)}%</td>
                  <td className={`py-4 text-right ${(resumo?.acoes_lucro || 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {formatCurrency(resumo?.acoes_lucro || 0)}
                  </td>
                </tr>
                <tr className="border-b border-gray-700/50">
                  <td className="py-4 flex items-center gap-3">
                    <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                    <span className="text-white">Fundos Imobiliários</span>
                  </td>
                  <td className="py-4 text-right text-white">{formatCurrency(resumo?.fiis_valor || 0)}</td>
                  <td className="py-4 text-right text-gray-400">{composicao?.fiis.percentual.toFixed(1)}%</td>
                  <td className={`py-4 text-right ${(resumo?.fiis_lucro || 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {formatCurrency(resumo?.fiis_lucro || 0)}
                  </td>
                </tr>
                <tr>
                  <td className="py-4 flex items-center gap-3">
                    <div className="w-3 h-3 rounded-full bg-purple-500"></div>
                    <span className="text-white">Outros</span>
                  </td>
                  <td className="py-4 text-right text-white">{formatCurrency(resumo?.outros || 0)}</td>
                  <td className="py-4 text-right text-gray-400">{composicao?.outros.percentual.toFixed(1)}%</td>
                  <td className="py-4 text-right text-gray-400">-</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Modal Outros Ativos */}
      {showAddOutros && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md border border-gray-700">
            <h3 className="text-xl font-bold text-white mb-4">Atualizar Outros Ativos</h3>
            <p className="text-gray-400 text-sm mb-4">
              Informe o valor total de outros investimentos (poupança, CDB, Tesouro, etc.)
            </p>
            <input
              type="number"
              value={outrosValor}
              onChange={(e) => setOutrosValor(e.target.value)}
              placeholder="Valor total em R$"
              className="w-full bg-gray-700 text-white px-4 py-3 rounded-lg border border-gray-600 mb-4"
            />
            <div className="flex gap-3">
              <button
                onClick={() => setShowAddOutros(false)}
                className="flex-1 bg-gray-700 hover:bg-gray-600 text-white py-3 rounded-lg"
              >
                Cancelar
              </button>
              <button
                onClick={atualizarOutros}
                className="flex-1 bg-amber-600 hover:bg-amber-700 text-white py-3 rounded-lg"
              >
                Salvar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
