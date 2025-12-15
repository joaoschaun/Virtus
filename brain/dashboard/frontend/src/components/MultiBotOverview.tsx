/**
 * VIRTUS Dashboard - Multi-Bot Overview Component
 * =================================================
 * 
 * Visualização de múltiplos tipos de bots no dashboard
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Chip,
  IconButton,
  Tooltip,
  CircularProgress,
  Button,
  Tabs,
  Tab,
  Card,
  CardContent,
  CardActions,
  LinearProgress,
  Alert,
} from '@mui/material';
import {
  PlayArrow,
  Stop,
  Pause,
  Refresh,
  Add,
  ShowChart,
  AccountBalance,
  CurrencyExchange,
  SwapHoriz,
  Storefront,
} from '@mui/icons-material';
import multiBotService, { Bot, DashboardState } from '../services/multiBotService';

// Ícones por tipo de bot
const botTypeIcons: Record<string, React.ReactNode> = {
  forex: <CurrencyExchange />,
  arbitrage: <SwapHoriz />,
  crypto: <AccountBalance />,
  stocks: <Storefront />,
};

// Cores por tipo de bot
const botTypeColors: Record<string, string> = {
  forex: '#2196F3',
  arbitrage: '#9C27B0',
  crypto: '#FF9800',
  stocks: '#4CAF50',
};

// Cores por status
const statusColors: Record<string, 'success' | 'error' | 'warning' | 'default' | 'info'> = {
  running: 'success',
  stopped: 'default',
  paused: 'warning',
  error: 'error',
  starting: 'info',
  maintenance: 'warning',
};

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div role="tabpanel" hidden={value !== index} {...other}>
      {value === index && <Box sx={{ py: 2 }}>{children}</Box>}
    </div>
  );
}

export default function MultiBotOverview() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dashboardState, setDashboardState] = useState<DashboardState | null>(null);
  const [selectedTab, setSelectedTab] = useState(0);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = async () => {
    try {
      setRefreshing(true);
      const state = await multiBotService.getDashboardState();
      setDashboardState(state);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Erro ao carregar dados');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000); // Atualiza a cada 10s
    return () => clearInterval(interval);
  }, []);

  const handleControl = async (botId: string, action: 'start' | 'stop' | 'pause') => {
    try {
      await multiBotService.controlBot(botId, action);
      await loadData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!dashboardState) {
    return (
      <Alert severity="info">
        Sistema multi-bot não disponível. Configure os bots primeiro.
      </Alert>
    );
  }

  const { bots, aggregated, summary } = dashboardState;
  const botTypes = Object.keys(summary.by_type || {});

  return (
    <Box>
      {/* Header com métricas agregadas */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">
            Sistema Multi-Bot
          </Typography>
          <Box>
            <Tooltip title="Atualizar">
              <IconButton onClick={loadData} disabled={refreshing}>
                <Refresh className={refreshing ? 'spinning' : ''} />
              </IconButton>
            </Tooltip>
            <Button
              variant="contained"
              startIcon={<Add />}
              size="small"
              sx={{ ml: 1 }}
            >
              Novo Bot
            </Button>
          </Box>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Cards de resumo */}
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
          <Box sx={{ flex: '1 1 calc(50% - 8px)', minWidth: '140px' }}>
            <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'background.default' }}>
              <Typography variant="h4" color="primary">
                {aggregated?.total_bots || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Total de Bots
              </Typography>
            </Paper>
          </Box>
          <Box sx={{ flex: '1 1 calc(50% - 8px)', minWidth: '140px' }}>
            <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'background.default' }}>
              <Typography variant="h4" color="success.main">
                {aggregated?.running_bots || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Rodando
              </Typography>
            </Paper>
          </Box>
          <Box sx={{ flex: '1 1 calc(50% - 8px)', minWidth: '140px' }}>
            <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'background.default' }}>
              <Typography variant="h4">
                {aggregated?.total_trades || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Total Trades
              </Typography>
            </Paper>
          </Box>
          <Box sx={{ flex: '1 1 calc(50% - 8px)', minWidth: '140px' }}>
            <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'background.default' }}>
              <Typography 
                variant="h4" 
                color={(aggregated?.total_profit || 0) >= 0 ? 'success.main' : 'error.main'}
              >
                ${(aggregated?.total_profit || 0).toFixed(2)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Lucro Total
              </Typography>
            </Paper>
          </Box>
        </Box>
      </Paper>

      {/* Tabs por tipo de bot */}
      <Paper sx={{ mb: 2 }}>
        <Tabs 
          value={selectedTab} 
          onChange={(_: React.SyntheticEvent, v: number) => setSelectedTab(v)}
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab label="Todos" icon={<ShowChart />} iconPosition="start" />
          {botTypes.map((type) => (
            <Tab 
              key={type}
              label={type.charAt(0).toUpperCase() + type.slice(1)}
              icon={(botTypeIcons[type] || <ShowChart />) as React.ReactElement}
              iconPosition="start"
            />
          ))}
        </Tabs>
      </Paper>

      {/* Lista de bots */}
      <TabPanel value={selectedTab} index={0}>
        <BotList bots={bots} onControl={handleControl} />
      </TabPanel>

      {botTypes.map((type, index) => (
        <TabPanel key={type} value={selectedTab} index={index + 1}>
          <BotList 
            bots={bots.filter(b => b.type === type)} 
            onControl={handleControl}
          />
        </TabPanel>
      ))}

      {/* Se não houver bots */}
      {bots.length === 0 && (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            Nenhum bot configurado
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Configure seus bots de Forex, Arbitragem, Crypto ou Ações.
          </Typography>
          <Button variant="contained" startIcon={<Add />}>
            Criar Primeiro Bot
          </Button>
        </Paper>
      )}
    </Box>
  );
}

// Componente de lista de bots
interface BotListProps {
  bots: Bot[];
  onControl: (botId: string, action: 'start' | 'stop' | 'pause') => void;
}

function BotList({ bots, onControl }: BotListProps) {
  if (bots.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
        Nenhum bot nesta categoria.
      </Typography>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
      {bots.map((bot) => (
        <Box key={bot.id} sx={{ flex: '1 1 calc(33.333% - 16px)', minWidth: '280px' }}>
          <BotCard bot={bot} onControl={onControl} />
        </Box>
      ))}
    </Box>
  );
}

// Card individual de bot
interface BotCardProps {
  bot: Bot;
  onControl: (botId: string, action: 'start' | 'stop' | 'pause') => void;
}

function BotCard({ bot, onControl }: BotCardProps) {
  const typeColor = botTypeColors[bot.type] || '#666';
  const isRunning = bot.status === 'running';
  const isPaused = bot.status === 'paused';

  return (
    <Card 
      sx={{ 
        height: '100%',
        borderLeft: `4px solid ${typeColor}`,
        '&:hover': { boxShadow: 4 },
      }}
    >
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
          <Box>
            <Typography variant="h6" component="div">
              {bot.name}
            </Typography>
            <Box sx={{ display: 'flex', gap: 0.5, mt: 0.5 }}>
              <Chip 
                label={bot.type} 
                size="small" 
                sx={{ bgcolor: typeColor, color: 'white' }}
              />
              <Chip 
                label={bot.status} 
                size="small" 
                color={statusColors[bot.status]}
              />
            </Box>
          </Box>
          {botTypeIcons[bot.type]}
        </Box>

        <Typography variant="body2" color="text.secondary" gutterBottom>
          {bot.market.toUpperCase()} • {bot.symbols.join(', ') || 'Sem símbolos'}
        </Typography>

        {/* Métricas */}
        <Box sx={{ mt: 2, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Trades
            </Typography>
            <Typography variant="body2">
              {bot.metrics?.total_trades || 0}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Win Rate
            </Typography>
            <Typography variant="body2">
              {(bot.metrics?.win_rate || 0).toFixed(1)}%
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Lucro
            </Typography>
            <Typography 
              variant="body2"
              color={(bot.metrics?.net_profit || 0) >= 0 ? 'success.main' : 'error.main'}
            >
              ${(bot.metrics?.net_profit || 0).toFixed(2)}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Drawdown
            </Typography>
            <Typography variant="body2" color="warning.main">
              {(bot.metrics?.current_drawdown || 0).toFixed(1)}%
            </Typography>
          </Box>
        </Box>

        {/* Barra de progresso do drawdown */}
        <Box sx={{ mt: 1 }}>
          <LinearProgress 
            variant="determinate" 
            value={Math.min((bot.metrics?.current_drawdown || 0) / (bot.config?.max_drawdown || 10) * 100, 100)}
            color="warning"
            sx={{ height: 4, borderRadius: 2 }}
          />
        </Box>
      </CardContent>

      <CardActions>
        {!isRunning && !isPaused && (
          <Tooltip title="Iniciar">
            <IconButton 
              size="small" 
              color="success"
              onClick={() => onControl(bot.id, 'start')}
            >
              <PlayArrow />
            </IconButton>
          </Tooltip>
        )}
        {isRunning && (
          <>
            <Tooltip title="Pausar">
              <IconButton 
                size="small" 
                color="warning"
                onClick={() => onControl(bot.id, 'pause')}
              >
                <Pause />
              </IconButton>
            </Tooltip>
            <Tooltip title="Parar">
              <IconButton 
                size="small" 
                color="error"
                onClick={() => onControl(bot.id, 'stop')}
              >
                <Stop />
              </IconButton>
            </Tooltip>
          </>
        )}
        {isPaused && (
          <>
            <Tooltip title="Retomar">
              <IconButton 
                size="small" 
                color="success"
                onClick={() => onControl(bot.id, 'start')}
              >
                <PlayArrow />
              </IconButton>
            </Tooltip>
            <Tooltip title="Parar">
              <IconButton 
                size="small" 
                color="error"
                onClick={() => onControl(bot.id, 'stop')}
              >
                <Stop />
              </IconButton>
            </Tooltip>
          </>
        )}
      </CardActions>
    </Card>
  );
}
