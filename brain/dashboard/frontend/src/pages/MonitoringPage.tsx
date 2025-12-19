/**
 * VIRTUS - Página de Monitoramento
 * 
 * Drawdown, Auditoria, Métricas
 */

import React, { useState, useEffect } from 'react';
import {
  Shield,
  AlertTriangle,
  Activity,
  FileText,
  RefreshCw,
  Play,
  Square,
  Download,
  Clock,
  User,
  Server,
} from 'lucide-react';
import {
  drawdownService,
  auditService,
  metricsService,
  reportsService,
  DrawdownState,
  DrawdownAlert,
  AuditLog,
  AuditStats,
} from '../services/newModulesService';

const MonitoringPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'drawdown' | 'audit' | 'metrics' | 'reports'>('drawdown');
  const [loading, setLoading] = useState(true);

  // Drawdown state
  const [drawdownRunning, setDrawdownRunning] = useState(false);
  const [drawdownState, setDrawdownState] = useState<DrawdownState | null>(null);
  const [drawdownAlerts, setDrawdownAlerts] = useState<DrawdownAlert[]>([]);

  // Audit state
  const [auditStats, setAuditStats] = useState<AuditStats | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [auditFilter, setAuditFilter] = useState<string>('');

  // Metrics state
  const [metricsText, setMetricsText] = useState<string>('');

  // Reports state
  const [reportPeriod, setReportPeriod] = useState<'week' | 'month' | 'quarter' | 'year'>('month');

  const fetchDrawdownData = async () => {
    try {
      const [statusRes, alertsRes] = await Promise.all([
        drawdownService.getStatus(),
        drawdownService.getAlerts(20),
      ]);
      setDrawdownRunning(statusRes.data.running);
      setDrawdownState(statusRes.data.state);
      setDrawdownAlerts(alertsRes.data.alerts || []);
    } catch (error) {
      console.error('Error fetching drawdown data:', error);
    }
  };

  const fetchAuditData = async () => {
    try {
      const [statsRes, logsRes] = await Promise.all([
        auditService.getStats(),
        auditService.getLogs({ limit: 50, category: auditFilter || undefined }),
      ]);
      setAuditStats(statsRes.data);
      setAuditLogs(logsRes.data.logs || []);
    } catch (error) {
      console.error('Error fetching audit data:', error);
    }
  };

  const fetchMetricsData = async () => {
    try {
      const res = await metricsService.getMetrics();
      setMetricsText(res.data);
    } catch (error) {
      console.error('Error fetching metrics:', error);
    }
  };

  useEffect(() => {
    const fetchAll = async () => {
      setLoading(true);
      await Promise.all([fetchDrawdownData(), fetchAuditData(), fetchMetricsData()]);
      setLoading(false);
    };
    fetchAll();

    const interval = setInterval(() => {
      if (activeTab === 'drawdown') fetchDrawdownData();
      else if (activeTab === 'audit') fetchAuditData();
      else if (activeTab === 'metrics') fetchMetricsData();
    }, 5000);

    return () => clearInterval(interval);
  }, [activeTab, auditFilter]);

  const handleStartDrawdown = async () => {
    await drawdownService.start();
    setDrawdownRunning(true);
  };

  const handleStopDrawdown = async () => {
    await drawdownService.stop();
    setDrawdownRunning(false);
  };

  const handleDownloadReport = async () => {
    try {
      const res = await reportsService.getPerformanceReport(reportPeriod, 'html');
      const blob = new Blob([res.data], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `virtus_report_${reportPeriod}.html`;
      a.click();
    } catch (error) {
      console.error('Error downloading report:', error);
    }
  };

  const getAlertLevelColor = (level: string) => {
    switch (level) {
      case 'normal': return 'text-green-500 bg-green-100';
      case 'caution': return 'text-yellow-500 bg-yellow-100';
      case 'warning': return 'text-orange-500 bg-orange-100';
      case 'critical': return 'text-red-500 bg-red-100';
      case 'emergency': return 'text-red-700 bg-red-200';
      default: return 'text-gray-500 bg-gray-100';
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
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          🔍 Monitoramento
        </h1>
        <p className="text-gray-500 dark:text-gray-400">
          Drawdown, Auditoria, Métricas e Relatórios
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b dark:border-gray-700">
        {[
          { id: 'drawdown', label: 'Drawdown', icon: Shield },
          { id: 'audit', label: 'Auditoria', icon: FileText },
          { id: 'metrics', label: 'Métricas', icon: Activity },
          { id: 'reports', label: 'Relatórios', icon: Download },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id as any)}
            className={`flex items-center gap-2 px-4 py-2 border-b-2 transition-colors ${
              activeTab === id
                ? 'border-blue-500 text-blue-500'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Drawdown Tab */}
      {activeTab === 'drawdown' && (
        <div className="space-y-6">
          {/* Controls */}
          <div className="flex items-center gap-4">
            {!drawdownRunning ? (
              <button
                onClick={handleStartDrawdown}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                <Play className="w-4 h-4" />
                Iniciar Monitor
              </button>
            ) : (
              <button
                onClick={handleStopDrawdown}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                <Square className="w-4 h-4" />
                Parar Monitor
              </button>
            )}
            <span className={`px-3 py-1 rounded-full text-sm ${
              drawdownRunning ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
            }`}>
              {drawdownRunning ? 'Monitorando' : 'Parado'}
            </span>
          </div>

          {/* State */}
          {drawdownState && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
                <div className="text-sm text-gray-500">Equity Atual</div>
                <div className="text-xl font-bold">${drawdownState.current_equity.toLocaleString()}</div>
              </div>
              <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
                <div className="text-sm text-gray-500">Pico</div>
                <div className="text-xl font-bold">${drawdownState.peak_equity.toLocaleString()}</div>
              </div>
              <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
                <div className="text-sm text-gray-500">Drawdown Atual</div>
                <div className={`text-xl font-bold ${(drawdownState.drawdown_percent ?? 0) > 5 ? 'text-red-500' : 'text-yellow-500'}`}>
                  {(drawdownState.drawdown_percent ?? 0).toFixed(2)}%
                </div>
              </div>
              <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
                <div className="text-sm text-gray-500">Nível</div>
                <div className={`text-xl font-bold px-2 py-1 rounded ${getAlertLevelColor(drawdownState.current_level)}`}>
                  {drawdownState.current_level.toUpperCase()}
                </div>
              </div>
            </div>
          )}

          {/* Alerts */}
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5" />
              Alertas Recentes
            </h2>
            {drawdownAlerts.length === 0 ? (
              <p className="text-gray-500 text-center py-4">Nenhum alerta</p>
            ) : (
              <div className="space-y-2">
                {drawdownAlerts.map((alert, i) => (
                  <div key={i} className={`p-3 rounded-lg ${getAlertLevelColor(alert.level)}`}>
                    <div className="flex justify-between items-start">
                      <div>
                        <span className="font-semibold">{alert.level.toUpperCase()}</span>
                        <span className="ml-2">{alert.message}</span>
                      </div>
                      <span className="text-sm">{new Date(alert.timestamp).toLocaleTimeString()}</span>
                    </div>
                    <div className="text-sm mt-1">
                      Drawdown: {(alert.drawdown_percent ?? 0).toFixed(2)}% | Ação: {alert.action_taken}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Audit Tab */}
      {activeTab === 'audit' && (
        <div className="space-y-6">
          {/* Stats */}
          {auditStats && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
                <div className="text-sm text-gray-500">Total de Eventos</div>
                <div className="text-xl font-bold">{auditStats.total_events}</div>
              </div>
              <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
                <div className="text-sm text-gray-500">Por Categoria</div>
                <div className="text-sm">
                  {Object.entries(auditStats.by_category).slice(0, 3).map(([k, v]) => (
                    <div key={k}>{k}: {v}</div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Filter */}
          <div className="flex gap-2">
            <select
              value={auditFilter}
              onChange={(e) => setAuditFilter(e.target.value)}
              className="px-3 py-2 border rounded dark:bg-gray-800 dark:border-gray-700"
            >
              <option value="">Todas as Categorias</option>
              <option value="TRADE">Trades</option>
              <option value="AUTH">Autenticação</option>
              <option value="CONFIG">Configuração</option>
              <option value="SYSTEM">Sistema</option>
            </select>
          </div>

          {/* Logs */}
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
            <h2 className="text-lg font-semibold mb-4">Logs de Auditoria</h2>
            {auditLogs.length === 0 ? (
              <p className="text-gray-500 text-center py-4">Nenhum log encontrado</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b dark:border-gray-700">
                      <th className="text-left p-2">Data</th>
                      <th className="text-left p-2">Categoria</th>
                      <th className="text-left p-2">Ação</th>
                      <th className="text-left p-2">Usuário</th>
                      <th className="text-left p-2">Severidade</th>
                    </tr>
                  </thead>
                  <tbody>
                    {auditLogs.map((log) => (
                      <tr key={log.id} className="border-b dark:border-gray-700">
                        <td className="p-2">{new Date(log.timestamp).toLocaleString()}</td>
                        <td className="p-2">
                          <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                            {log.category}
                          </span>
                        </td>
                        <td className="p-2">{log.action}</td>
                        <td className="p-2">{log.user || 'system'}</td>
                        <td className="p-2">
                          <span className={`px-2 py-1 rounded text-xs ${
                            log.severity === 'error' ? 'bg-red-100 text-red-800' :
                            log.severity === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {log.severity}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Metrics Tab */}
      {activeTab === 'metrics' && (
        <div className="space-y-6">
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Server className="w-5 h-5" />
                Métricas Prometheus
              </h2>
              <button
                onClick={fetchMetricsData}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
            <pre className="bg-gray-900 text-green-400 p-4 rounded-lg overflow-x-auto text-xs max-h-96">
              {metricsText || '# No metrics available'}
            </pre>
            <p className="text-sm text-gray-500 mt-2">
              Endpoint: <code className="bg-gray-100 dark:bg-gray-700 px-1 rounded">http://localhost:8000/metrics</code>
            </p>
          </div>
        </div>
      )}

      {/* Reports Tab */}
      {activeTab === 'reports' && (
        <div className="space-y-6">
          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Download className="w-5 h-5" />
              Gerar Relatório
            </h2>
            <div className="flex gap-4 items-end">
              <div>
                <label className="block text-sm mb-1">Período</label>
                <select
                  value={reportPeriod}
                  onChange={(e) => setReportPeriod(e.target.value as any)}
                  className="px-3 py-2 border rounded dark:bg-gray-700 dark:border-gray-600"
                >
                  <option value="week">Última Semana</option>
                  <option value="month">Último Mês</option>
                  <option value="quarter">Último Trimestre</option>
                  <option value="year">Último Ano</option>
                </select>
              </div>
              <button
                onClick={handleDownloadReport}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                <Download className="w-4 h-4" />
                Download HTML
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MonitoringPage;
