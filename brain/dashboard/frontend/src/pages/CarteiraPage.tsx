import { useState, useEffect } from 'react';
import { 
  TrendingUp, TrendingDown, Plus, DollarSign, Activity, 
  RefreshCw, Building2, PieChart, BarChart2, History,
  ShoppingCart, Banknote, Calculator, X, ArrowUpRight, ArrowDownRight
} from 'lucide-react';
import {
  PieChart as RechartsPie, Pie, Cell, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend
} from 'recharts';

interface Ativo {
  ticker: string;
  tipo: string;
  nome: string;
  setor: string;
  quantidade: number;
  preco_medio: number;
  valor_investido: number;
  preco_atual?: number;
  valor_atual?: number;
  lucro_prejuizo?: number;
  lucro_prejuizo_pct?: number;
  dividendos_recebidos: number;
  yield_on_cost?: number;
}

interface Operacao {
  id: string;
  ticker: string;
  tipo_ativo: string;
  tipo_operacao: string;
  data: string;
  quantidade: number;
  preco_unitario: number;
  valor_total: number;
  lucro_prejuizo?: number;
  lucro_prejuizo_pct?: number;
}

interface Resumo {
  total_investido: number;
  valor_atual: number;
  lucro_prejuizo: number;
  lucro_prejuizo_pct: number;
  dividendos_total: number;
  quantidade_ativos: number;
  retorno_total: number;
  retorno_total_pct: number;
}

interface SimulacaoCompra {
  valor_investir: number;
  preco_acao: number;
  quantidade_comprar: number;
  valor_real_investido: number;
  sobra: number;
  dividend_yield: number;
  dividendo_anual_esperado: number;
  dividendo_mensal_esperado: number;
  payback_anos: number;
}

interface SimulacaoVenda {
  ticker: string;
  quantidade: number;
  preco_medio: number;
  preco_venda: number;
  custo_total: number;
  valor_venda: number;
  lucro_prejuizo: number;
  lucro_prejuizo_pct: number;
  resultado: string;
  dividendos_recebidos: number;
  retorno_total: number;
  retorno_total_pct: number;
}

const COLORS = ['#F59E0B', '#10B981', '#3B82F6', '#8B5CF6', '#EF4444', '#06B6D4', '#EC4899'];

export default function CarteiraPage() {
  const [activeTab, setActiveTab] = useState<'acoes' | 'fiis'>('acoes');
  const [ativos, setAtivos] = useState<Ativo[]>([]);
  const [resumo, setResumo] = useState<Resumo | null>(null);
  const [operacoes, setOperacoes] = useState<Operacao[]>([]);
  const [dividendosMensal, setDividendosMensal] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  
  // Modais
  const [showCompra, setShowCompra] = useState(false);
  const [showVenda, setShowVenda] = useState(false);
  const [showDividendo, setShowDividendo] = useState(false);
  const [showSimulador, setShowSimulador] = useState(false);
  
  // Forms
  const [formCompra, setFormCompra] = useState({
    ticker: '', quantidade: '', preco_unitario: '', nome: '', setor: '', taxas: '0'
  });
  const [formVenda, setFormVenda] = useState({
    ticker: '', quantidade: '', preco_unitario: '', taxas: '0'
  });
  const [formDividendo, setFormDividendo] = useState({
    ticker: '', valor_por_cota: '', data_pagamento: ''
  });
  const [formSimulacao, setFormSimulacao] = useState({
    valor_investir: '', preco_acao: '', dividend_yield: ''
  });
  
  // Resultados
  const [simulacaoCompra, setSimulacaoCompra] = useState<SimulacaoCompra | null>(null);
  const [simulacaoVenda, setSimulacaoVenda] = useState<SimulacaoVenda | null>(null);
  const [ativoSelecionado, setAtivoSelecionado] = useState<Ativo | null>(null);

  useEffect(() => {
    loadData();
  }, [activeTab]);

  const loadData = async () => {
    try {
      setLoading(true);
      const tipo = activeTab === 'acoes' ? 'acao' : 'fii';
      
      const [ativosRes, resumoRes, operacoesRes, dividendosRes] = await Promise.all([
        fetch(`/api/carteira/ativos?tipo=${tipo}`),
        fetch(`/api/carteira/resumo?tipo=${tipo}`),
        fetch(`/api/carteira/operacoes?tipo=${tipo}&limit=20`),
        fetch('/api/carteira/dividendos/mensal')
      ]);

      const ativosData = await ativosRes.json();
      const resumoData = await resumoRes.json();
      const operacoesData = await operacoesRes.json();
      const dividendosData = await dividendosRes.json();

      if (ativosData.success) setAtivos(ativosData.data);
      if (resumoData.success) setResumo(resumoData.data);
      if (operacoesData.success) setOperacoes(operacoesData.data);
      if (dividendosData.success) setDividendosMensal(dividendosData.data);
    } catch (error) {
      console.error('Erro ao carregar:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(value);
  };

  const handleCompra = async () => {
    try {
      const response = await fetch('/api/carteira/comprar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker: formCompra.ticker.toUpperCase(),
          tipo: activeTab === 'acoes' ? 'acao' : 'fii',
          quantidade: parseInt(formCompra.quantidade),
          preco_unitario: parseFloat(formCompra.preco_unitario),
          nome: formCompra.nome,
          setor: formCompra.setor,
          taxas: parseFloat(formCompra.taxas || '0')
        })
      });
      
      const data = await response.json();
      if (data.success) {
        setShowCompra(false);
        setFormCompra({ ticker: '', quantidade: '', preco_unitario: '', nome: '', setor: '', taxas: '0' });
        loadData();
      }
    } catch (error) {
      console.error('Erro na compra:', error);
    }
  };

  const handleVenda = async () => {
    try {
      const response = await fetch('/api/carteira/vender', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker: formVenda.ticker.toUpperCase(),
          tipo: activeTab === 'acoes' ? 'acao' : 'fii',
          quantidade: parseInt(formVenda.quantidade),
          preco_unitario: parseFloat(formVenda.preco_unitario),
          taxas: parseFloat(formVenda.taxas || '0')
        })
      });
      
      const data = await response.json();
      if (data.success) {
        setSimulacaoVenda({
          ...data,
          ticker: formVenda.ticker.toUpperCase()
        });
        setShowVenda(false);
        loadData();
      }
    } catch (error) {
      console.error('Erro na venda:', error);
    }
  };

  const handleDividendo = async () => {
    try {
      const response = await fetch('/api/carteira/dividendo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker: formDividendo.ticker.toUpperCase(),
          tipo: activeTab === 'acoes' ? 'acao' : 'fii',
          valor_por_cota: parseFloat(formDividendo.valor_por_cota),
          data_pagamento: formDividendo.data_pagamento || undefined
        })
      });
      
      const data = await response.json();
      if (data.success) {
        setShowDividendo(false);
        setFormDividendo({ ticker: '', valor_por_cota: '', data_pagamento: '' });
        loadData();
      }
    } catch (error) {
      console.error('Erro no dividendo:', error);
    }
  };

  const handleSimularCompra = async () => {
    try {
      const response = await fetch('/api/carteira/simular/compra', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          valor_investir: parseFloat(formSimulacao.valor_investir),
          preco_acao: parseFloat(formSimulacao.preco_acao),
          dividend_yield: parseFloat(formSimulacao.dividend_yield)
        })
      });
      
      const data = await response.json();
      if (data.success) {
        setSimulacaoCompra(data.data);
      }
    } catch (error) {
      console.error('Erro na simulação:', error);
    }
  };

  const handleSimularVenda = async (ativo: Ativo, precoVenda: number) => {
    try {
      const response = await fetch('/api/carteira/simular/venda', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker: ativo.ticker,
          tipo: ativo.tipo,
          preco_venda: precoVenda
        })
      });
      
      const data = await response.json();
      if (data.success) {
        setSimulacaoVenda(data.data);
      }
    } catch (error) {
      console.error('Erro na simulação:', error);
    }
  };

  // Dados para gráficos
  const pieData = ativos.map((a, i) => ({
    name: a.ticker,
    value: a.valor_investido,
    color: COLORS[i % COLORS.length]
  }));

  const dividendosChartData = Object.entries(dividendosMensal).map(([mes, valor]) => ({
    mes: mes.split('-')[1] + '/' + mes.split('-')[0].slice(2),
    valor
  }));

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <RefreshCw className="w-8 h-8 text-amber-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-3xl font-bold text-amber-500">Carteira de Investimentos</h1>
            <p className="text-gray-400 mt-1">Gerencie suas ações e fundos imobiliários</p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => setShowSimulador(true)}
              className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
            >
              <Calculator className="w-4 h-4" />
              Simulador
            </button>
            <button
              onClick={() => setShowCompra(true)}
              className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
            >
              <ShoppingCart className="w-4 h-4" />
              Comprar
            </button>
            <button
              onClick={() => setShowVenda(true)}
              className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
            >
              <Banknote className="w-4 h-4" />
              Vender
            </button>
            <button
              onClick={() => setShowDividendo(true)}
              className="bg-amber-600 hover:bg-amber-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
            >
              <DollarSign className="w-4 h-4" />
              Dividendo
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-4 border-b border-gray-700">
          <button
            onClick={() => setActiveTab('acoes')}
            className={`pb-3 px-4 font-medium flex items-center gap-2 ${
              activeTab === 'acoes' 
                ? 'text-amber-500 border-b-2 border-amber-500' 
                : 'text-gray-400 hover:text-white'
            }`}
          >
            <Activity className="w-4 h-4" />
            Ações
          </button>
          <button
            onClick={() => setActiveTab('fiis')}
            className={`pb-3 px-4 font-medium flex items-center gap-2 ${
              activeTab === 'fiis' 
                ? 'text-amber-500 border-b-2 border-amber-500' 
                : 'text-gray-400 hover:text-white'
            }`}
          >
            <Building2 className="w-4 h-4" />
            Fundos Imobiliários
          </button>
        </div>

        {/* Cards Resumo */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
            <p className="text-gray-400 text-sm">Total Investido</p>
            <p className="text-2xl font-bold text-white mt-1">
              {formatCurrency(resumo?.total_investido || 0)}
            </p>
            <p className="text-gray-500 text-sm mt-1">{resumo?.quantidade_ativos || 0} ativos</p>
          </div>

          <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
            <p className="text-gray-400 text-sm">Valor Atual</p>
            <p className="text-2xl font-bold text-white mt-1">
              {formatCurrency(resumo?.valor_atual || resumo?.total_investido || 0)}
            </p>
          </div>

          <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
            <p className="text-gray-400 text-sm">Lucro/Prejuízo</p>
            <p className={`text-2xl font-bold mt-1 ${(resumo?.lucro_prejuizo || 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              {formatCurrency(resumo?.lucro_prejuizo || 0)}
            </p>
            <p className={`text-sm ${(resumo?.lucro_prejuizo_pct || 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              {(resumo?.lucro_prejuizo_pct || 0).toFixed(2)}%
            </p>
          </div>

          <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
            <p className="text-gray-400 text-sm">Dividendos Recebidos</p>
            <p className="text-2xl font-bold text-green-500 mt-1">
              {formatCurrency(resumo?.dividendos_total || 0)}
            </p>
          </div>
        </div>

        {/* Grid principal */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Lista de Ativos */}
          <div className="lg:col-span-2 bg-gray-800 rounded-xl p-6 border border-gray-700">
            <h3 className="text-lg font-semibold text-white mb-4">
              {activeTab === 'acoes' ? 'Minhas Ações' : 'Meus FIIs'}
            </h3>
            
            {ativos.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-gray-400">Nenhum ativo cadastrado</p>
                <button
                  onClick={() => setShowCompra(true)}
                  className="mt-4 bg-amber-600 hover:bg-amber-700 text-white px-6 py-2 rounded-lg"
                >
                  Adicionar primeiro ativo
                </button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="text-left text-gray-400 border-b border-gray-700">
                      <th className="pb-3">Ticker</th>
                      <th className="pb-3 text-right">Qtd</th>
                      <th className="pb-3 text-right">PM</th>
                      <th className="pb-3 text-right">Investido</th>
                      <th className="pb-3 text-right">Dividendos</th>
                      <th className="pb-3 text-right">YoC</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ativos.map((ativo) => (
                      <tr 
                        key={ativo.ticker} 
                        className="border-b border-gray-700/50 hover:bg-gray-700/30 cursor-pointer"
                        onClick={() => setAtivoSelecionado(ativo)}
                      >
                        <td className="py-3">
                          <div>
                            <p className="text-white font-medium">{ativo.ticker}</p>
                            <p className="text-gray-500 text-xs">{ativo.nome || ativo.setor}</p>
                          </div>
                        </td>
                        <td className="py-3 text-right text-white">{ativo.quantidade}</td>
                        <td className="py-3 text-right text-white">{formatCurrency(ativo.preco_medio)}</td>
                        <td className="py-3 text-right text-white">{formatCurrency(ativo.valor_investido)}</td>
                        <td className="py-3 text-right text-green-500">{formatCurrency(ativo.dividendos_recebidos)}</td>
                        <td className="py-3 text-right text-amber-500">
                          {(ativo.yield_on_cost || 0).toFixed(2)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Gráfico Composição */}
          <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <PieChart className="w-5 h-5 text-amber-500" />
              Composição
            </h3>
            {pieData.length > 0 ? (
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <RechartsPie>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      dataKey="value"
                      label={({ name }) => name}
                    >
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                      formatter={(value: number) => formatCurrency(value)}
                    />
                  </RechartsPie>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="text-gray-400 text-center py-8">Sem dados</p>
            )}
          </div>
        </div>

        {/* Dividendos por Mês */}
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <BarChart2 className="w-5 h-5 text-green-500" />
            Dividendos por Mês
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={dividendosChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="mes" stroke="#9CA3AF" />
                <YAxis stroke="#9CA3AF" tickFormatter={(v) => `R$ ${v}`} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                  formatter={(value: number) => formatCurrency(value)}
                />
                <Bar dataKey="valor" fill="#10B981" name="Dividendos" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Últimas Operações */}
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <History className="w-5 h-5 text-amber-500" />
            Últimas Operações
          </h3>
          {operacoes.length === 0 ? (
            <p className="text-gray-400 text-center py-4">Nenhuma operação registrada</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left text-gray-400 border-b border-gray-700">
                    <th className="pb-3">Data</th>
                    <th className="pb-3">Tipo</th>
                    <th className="pb-3">Ticker</th>
                    <th className="pb-3 text-right">Qtd</th>
                    <th className="pb-3 text-right">Preço</th>
                    <th className="pb-3 text-right">Total</th>
                    <th className="pb-3 text-right">Resultado</th>
                  </tr>
                </thead>
                <tbody>
                  {operacoes.map((op) => (
                    <tr key={op.id} className="border-b border-gray-700/50">
                      <td className="py-3 text-gray-400">
                        {new Date(op.data).toLocaleDateString('pt-BR')}
                      </td>
                      <td className="py-3">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          op.tipo_operacao === 'compra' ? 'bg-green-500/20 text-green-400' :
                          op.tipo_operacao === 'venda' ? 'bg-red-500/20 text-red-400' :
                          'bg-amber-500/20 text-amber-400'
                        }`}>
                          {op.tipo_operacao.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-3 text-white font-medium">{op.ticker}</td>
                      <td className="py-3 text-right text-white">{op.quantidade}</td>
                      <td className="py-3 text-right text-white">{formatCurrency(op.preco_unitario)}</td>
                      <td className="py-3 text-right text-white">{formatCurrency(op.valor_total)}</td>
                      <td className="py-3 text-right">
                        {op.lucro_prejuizo !== undefined ? (
                          <span className={op.lucro_prejuizo >= 0 ? 'text-green-500' : 'text-red-500'}>
                            {formatCurrency(op.lucro_prejuizo)} ({op.lucro_prejuizo_pct?.toFixed(2)}%)
                          </span>
                        ) : (
                          <span className="text-gray-500">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Modal Compra */}
      {showCompra && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md border border-gray-700">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-white">Registrar Compra</h3>
              <button onClick={() => setShowCompra(false)} className="text-gray-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Ticker</label>
                  <input
                    type="text"
                    value={formCompra.ticker}
                    onChange={(e) => setFormCompra({...formCompra, ticker: e.target.value})}
                    placeholder="Ex: PETR4"
                    className="w-full bg-gray-700 text-white px-4 py-2 rounded-lg border border-gray-600"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Quantidade</label>
                  <input
                    type="number"
                    value={formCompra.quantidade}
                    onChange={(e) => setFormCompra({...formCompra, quantidade: e.target.value})}
                    className="w-full bg-gray-700 text-white px-4 py-2 rounded-lg border border-gray-600"
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-sm text-gray-400 mb-1">Preço Unitário (R$)</label>
                <input
                  type="number"
                  step="0.01"
                  value={formCompra.preco_unitario}
                  onChange={(e) => setFormCompra({...formCompra, preco_unitario: e.target.value})}
                  className="w-full bg-gray-700 text-white px-4 py-2 rounded-lg border border-gray-600"
                />
              </div>
              
              <div>
                <label className="block text-sm text-gray-400 mb-1">Nome (opcional)</label>
                <input
                  type="text"
                  value={formCompra.nome}
                  onChange={(e) => setFormCompra({...formCompra, nome: e.target.value})}
                  placeholder="Ex: Petrobras PN"
                  className="w-full bg-gray-700 text-white px-4 py-2 rounded-lg border border-gray-600"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1">Taxas (R$)</label>
                <input
                  type="number"
                  step="0.01"
                  value={formCompra.taxas}
                  onChange={(e) => setFormCompra({...formCompra, taxas: e.target.value})}
                  className="w-full bg-gray-700 text-white px-4 py-2 rounded-lg border border-gray-600"
                />
              </div>

              {formCompra.quantidade && formCompra.preco_unitario && (
                <div className="bg-gray-700 rounded-lg p-4">
                  <p className="text-gray-400 text-sm">Total da compra:</p>
                  <p className="text-xl font-bold text-white">
                    {formatCurrency(
                      parseInt(formCompra.quantidade) * parseFloat(formCompra.preco_unitario) + 
                      parseFloat(formCompra.taxas || '0')
                    )}
                  </p>
                </div>
              )}
            </div>
            
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowCompra(false)}
                className="flex-1 bg-gray-700 hover:bg-gray-600 text-white py-3 rounded-lg"
              >
                Cancelar
              </button>
              <button
                onClick={handleCompra}
                className="flex-1 bg-green-600 hover:bg-green-700 text-white py-3 rounded-lg"
              >
                Confirmar Compra
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Venda */}
      {showVenda && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md border border-gray-700">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-white">Registrar Venda</h3>
              <button onClick={() => setShowVenda(false)} className="text-gray-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Ticker</label>
                <select
                  value={formVenda.ticker}
                  onChange={(e) => setFormVenda({...formVenda, ticker: e.target.value})}
                  className="w-full bg-gray-700 text-white px-4 py-2 rounded-lg border border-gray-600"
                >
                  <option value="">Selecione...</option>
                  {ativos.map(a => (
                    <option key={a.ticker} value={a.ticker}>
                      {a.ticker} - {a.quantidade} unidades (PM: {formatCurrency(a.preco_medio)})
                    </option>
                  ))}
                </select>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Quantidade</label>
                  <input
                    type="number"
                    value={formVenda.quantidade}
                    onChange={(e) => setFormVenda({...formVenda, quantidade: e.target.value})}
                    className="w-full bg-gray-700 text-white px-4 py-2 rounded-lg border border-gray-600"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Preço Venda (R$)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formVenda.preco_unitario}
                    onChange={(e) => setFormVenda({...formVenda, preco_unitario: e.target.value})}
                    className="w-full bg-gray-700 text-white px-4 py-2 rounded-lg border border-gray-600"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1">Taxas (R$)</label>
                <input
                  type="number"
                  step="0.01"
                  value={formVenda.taxas}
                  onChange={(e) => setFormVenda({...formVenda, taxas: e.target.value})}
                  className="w-full bg-gray-700 text-white px-4 py-2 rounded-lg border border-gray-600"
                />
              </div>
            </div>
            
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowVenda(false)}
                className="flex-1 bg-gray-700 hover:bg-gray-600 text-white py-3 rounded-lg"
              >
                Cancelar
              </button>
              <button
                onClick={handleVenda}
                className="flex-1 bg-red-600 hover:bg-red-700 text-white py-3 rounded-lg"
              >
                Confirmar Venda
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Dividendo */}
      {showDividendo && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md border border-gray-700">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-white">Registrar Dividendo</h3>
              <button onClick={() => setShowDividendo(false)} className="text-gray-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Ticker</label>
                <select
                  value={formDividendo.ticker}
                  onChange={(e) => setFormDividendo({...formDividendo, ticker: e.target.value})}
                  className="w-full bg-gray-700 text-white px-4 py-2 rounded-lg border border-gray-600"
                >
                  <option value="">Selecione...</option>
                  {ativos.map(a => (
                    <option key={a.ticker} value={a.ticker}>
                      {a.ticker} - {a.quantidade} unidades
                    </option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-sm text-gray-400 mb-1">Valor por Cota (R$)</label>
                <input
                  type="number"
                  step="0.01"
                  value={formDividendo.valor_por_cota}
                  onChange={(e) => setFormDividendo({...formDividendo, valor_por_cota: e.target.value})}
                  className="w-full bg-gray-700 text-white px-4 py-2 rounded-lg border border-gray-600"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1">Data Pagamento</label>
                <input
                  type="date"
                  value={formDividendo.data_pagamento}
                  onChange={(e) => setFormDividendo({...formDividendo, data_pagamento: e.target.value})}
                  className="w-full bg-gray-700 text-white px-4 py-2 rounded-lg border border-gray-600"
                />
              </div>

              {formDividendo.ticker && formDividendo.valor_por_cota && (
                <div className="bg-green-500/20 rounded-lg p-4">
                  <p className="text-gray-400 text-sm">Total a receber:</p>
                  <p className="text-xl font-bold text-green-500">
                    {formatCurrency(
                      (ativos.find(a => a.ticker === formDividendo.ticker)?.quantidade || 0) * 
                      parseFloat(formDividendo.valor_por_cota)
                    )}
                  </p>
                </div>
              )}
            </div>
            
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowDividendo(false)}
                className="flex-1 bg-gray-700 hover:bg-gray-600 text-white py-3 rounded-lg"
              >
                Cancelar
              </button>
              <button
                onClick={handleDividendo}
                className="flex-1 bg-amber-600 hover:bg-amber-700 text-white py-3 rounded-lg"
              >
                Registrar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Simulador */}
      {showSimulador && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-xl p-6 w-full max-w-lg border border-gray-700">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-white">Simulador de Compra</h3>
              <button onClick={() => {setShowSimulador(false); setSimulacaoCompra(null);}} className="text-gray-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Quanto você quer investir (R$)?</label>
                <input
                  type="number"
                  value={formSimulacao.valor_investir}
                  onChange={(e) => setFormSimulacao({...formSimulacao, valor_investir: e.target.value})}
                  placeholder="Ex: 1000"
                  className="w-full bg-gray-700 text-white px-4 py-2 rounded-lg border border-gray-600"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Preço da Ação (R$)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formSimulacao.preco_acao}
                    onChange={(e) => setFormSimulacao({...formSimulacao, preco_acao: e.target.value})}
                    className="w-full bg-gray-700 text-white px-4 py-2 rounded-lg border border-gray-600"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Dividend Yield (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={formSimulacao.dividend_yield}
                    onChange={(e) => setFormSimulacao({...formSimulacao, dividend_yield: e.target.value})}
                    placeholder="Ex: 6.5"
                    className="w-full bg-gray-700 text-white px-4 py-2 rounded-lg border border-gray-600"
                  />
                </div>
              </div>

              <button
                onClick={handleSimularCompra}
                className="w-full bg-purple-600 hover:bg-purple-700 text-white py-3 rounded-lg flex items-center justify-center gap-2"
              >
                <Calculator className="w-4 h-4" />
                Calcular
              </button>

              {simulacaoCompra && (
                <div className="bg-gray-700 rounded-lg p-4 space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Quantidade a comprar:</span>
                    <span className="text-white font-bold">{simulacaoCompra.quantidade_comprar} ações</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Valor real investido:</span>
                    <span className="text-white">{formatCurrency(simulacaoCompra.valor_real_investido)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Sobra:</span>
                    <span className="text-amber-500">{formatCurrency(simulacaoCompra.sobra)}</span>
                  </div>
                  <hr className="border-gray-600" />
                  <div className="flex justify-between">
                    <span className="text-gray-400">Dividendo anual esperado:</span>
                    <span className="text-green-500 font-bold">{formatCurrency(simulacaoCompra.dividendo_anual_esperado)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Dividendo mensal esperado:</span>
                    <span className="text-green-500">{formatCurrency(simulacaoCompra.dividendo_mensal_esperado)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Payback:</span>
                    <span className="text-white">{simulacaoCompra.payback_anos.toFixed(1)} anos</span>
                  </div>
                </div>
              )}
            </div>
            
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => {setShowSimulador(false); setSimulacaoCompra(null);}}
                className="flex-1 bg-gray-700 hover:bg-gray-600 text-white py-3 rounded-lg"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Resultado Venda */}
      {simulacaoVenda && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md border border-gray-700">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-white">Resultado da Venda</h3>
              <button onClick={() => setSimulacaoVenda(null)} className="text-gray-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className={`text-center py-6 rounded-lg ${
              simulacaoVenda.resultado === 'LUCRO' ? 'bg-green-500/20' : 
              simulacaoVenda.resultado === 'PREJUÍZO' ? 'bg-red-500/20' : 'bg-gray-700'
            }`}>
              <div className="flex justify-center mb-2">
                {simulacaoVenda.resultado === 'LUCRO' ? (
                  <ArrowUpRight className="w-12 h-12 text-green-500" />
                ) : simulacaoVenda.resultado === 'PREJUÍZO' ? (
                  <ArrowDownRight className="w-12 h-12 text-red-500" />
                ) : null}
              </div>
              <p className="text-2xl font-bold text-white">{simulacaoVenda.resultado}</p>
              <p className={`text-3xl font-bold mt-2 ${
                simulacaoVenda.lucro_prejuizo >= 0 ? 'text-green-500' : 'text-red-500'
              }`}>
                {formatCurrency(simulacaoVenda.lucro_prejuizo)}
              </p>
              <p className="text-gray-400">
                ({simulacaoVenda.lucro_prejuizo_pct.toFixed(2)}%)
              </p>
            </div>

            <div className="mt-4 space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Custo total:</span>
                <span className="text-white">{formatCurrency(simulacaoVenda.custo_total)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Valor venda:</span>
                <span className="text-white">{formatCurrency(simulacaoVenda.valor_venda)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Dividendos recebidos:</span>
                <span className="text-green-500">{formatCurrency(simulacaoVenda.dividendos_recebidos)}</span>
              </div>
              <hr className="border-gray-700" />
              <div className="flex justify-between font-bold">
                <span className="text-gray-400">Retorno total:</span>
                <span className={simulacaoVenda.retorno_total >= 0 ? 'text-green-500' : 'text-red-500'}>
                  {formatCurrency(simulacaoVenda.retorno_total)} ({simulacaoVenda.retorno_total_pct.toFixed(2)}%)
                </span>
              </div>
            </div>
            
            <button
              onClick={() => setSimulacaoVenda(null)}
              className="w-full mt-6 bg-amber-600 hover:bg-amber-700 text-white py-3 rounded-lg"
            >
              Fechar
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
