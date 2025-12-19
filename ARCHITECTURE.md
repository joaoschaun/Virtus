# 🏗️ VIRTUS - Arquitetura de Microsserviços

## Visão Geral

O sistema VIRTUS é dividido em **3 serviços independentes** que se comunicam via API:

```
┌─────────────────────────────────────────────────────────────────┐
│                        USUÁRIO                                   │
│                           │                                      │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │           FRONTEND (React + Vite)                         │   │
│  │           http://localhost:5173                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           │                                      │
│                           ▼ REST API + WebSocket                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │           BACKEND API (FastAPI)                           │   │
│  │           http://localhost:8000                           │   │
│  │   - Autenticação JWT                                      │   │
│  │   - Rotas REST para dashboard                             │   │
│  │   - WebSocket para atualizações real-time                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           │                                      │
│                           ▼ REST API                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │           BRAIN API (Trading Engine)                      │   │
│  │           http://localhost:8001                           │   │
│  │   - Execução de trades                                    │   │
│  │   - Análise de mercado                                    │   │
│  │   - Sinais e alertas                                      │   │
│  │   - Conexão MT5                                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           │                                      │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │           METATRADER 5                                    │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Portas

| Serviço   | Porta | Descrição                    |
|-----------|-------|------------------------------|
| Frontend  | 5173  | Interface web React          |
| Backend   | 8000  | API REST do Dashboard        |
| Brain API | 8001  | API do Trading Engine        |

## Como Iniciar

### Opção 1: Script Unificado
```powershell
.\start_all.ps1
```

### Opção 2: Separadamente

**Terminal 1 - Brain (Trading):**
```powershell
cd brain
..\env\Scripts\python.exe main.py
```

**Terminal 2 - Backend API:**
```powershell
cd brain\dashboard\backend
..\..\env\Scripts\python.exe run_server.py
```

**Terminal 3 - Frontend:**
```powershell
cd brain\dashboard\frontend
npm run dev
```

## Endpoints da Brain API (porta 8001)

### Status
- `GET /api/status` - Status geral do sistema
- `GET /api/health` - Health check

### Conta MT5
- `GET /api/account` - Informações da conta
- `GET /api/positions` - Posições abertas
- `GET /api/orders` - Ordens pendentes

### Trading
- `POST /api/trade` - Executar trade manual
- `DELETE /api/position/{ticket}` - Fechar posição
- `GET /api/history` - Histórico de trades

### Análise
- `GET /api/analysis/{symbol}` - Análise completa de um símbolo
- `GET /api/signals` - Sinais ativos
- `GET /api/market/{symbol}` - Dados de mercado

### Bots
- `GET /api/bots` - Lista de bots
- `POST /api/bots/{id}/start` - Iniciar bot
- `POST /api/bots/{id}/stop` - Parar bot
- `GET /api/bots/{id}/status` - Status do bot

## Comunicação

### Brain → Backend (Push via callback)
O Brain envia atualizações para o Backend quando:
- Trade executado
- Posição fechada
- Sinal gerado
- Alerta disparado

### Backend → Brain (Pull via API)
O Backend consulta o Brain para:
- Status dos bots
- Posições atuais
- Histórico de trades
- Análises de mercado

## Endpoints de Integração no Backend (porta 8000)

O Dashboard Backend expõe rotas que fazem proxy para a Brain API:

- `GET /api/brain/health` - Verifica se Brain API está disponível
- `GET /api/brain/status` - Status do sistema via Brain API
- `GET /api/brain/account` - Conta MT5 via Brain API
- `GET /api/brain/positions` - Posições via Brain API
- `GET /api/brain/bots` - Bots via Brain API
- `POST /api/brain/trade` - Executar trade via Brain API
- `DELETE /api/brain/position/{ticket}` - Fechar posição via Brain API

Se a Brain API não estiver disponível, esses endpoints retornam dados de fallback.

## Benefícios desta Arquitetura

1. **Independência**: Cada serviço pode ser reiniciado sem afetar os outros
2. **Escalabilidade**: Serviços podem rodar em máquinas diferentes
3. **Manutenção**: Mudanças em um serviço não afetam os outros
4. **Debugging**: Mais fácil isolar problemas
5. **Deploy**: Pode fazer deploy parcial de apenas um serviço

## Troubleshooting

### Brain API não conecta
1. Verifique se MT5 está aberto e logado
2. Execute: `.\start_trading.ps1`
3. Verifique logs em `brain/data/logs/`

### Dashboard não mostra dados em tempo real
1. Verifique se Brain API está rodando
2. Acesse: `http://localhost:8000/api/brain/health`
3. Se `brain_api_available: false`, inicie a Brain API

### Erro de porta em uso
```powershell
# Encontrar processo na porta
netstat -ano | findstr :8001
# Matar processo
taskkill /PID <PID> /F
```
