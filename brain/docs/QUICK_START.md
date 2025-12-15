# VIRTUS - Quick Start Guide

## 🚀 Início Rápido

### Pré-requisitos

- Python 3.10+
- MetaTrader 5 instalado
- Conta de broker MT5 ativa

### 1. Configurar Ambiente

```powershell
# Criar ambiente virtual
python -m venv env
.\env\Scripts\Activate.ps1

# Instalar dependências
pip install -r requirements.txt
```

### 2. Configurar Credenciais

Edite `config/config.yaml`:

```yaml
mt5:
  login: SEU_LOGIN
  password: "SUA_SENHA"
  server: "SEU_BROKER"

telegram:
  token: "SEU_BOT_TOKEN"
  chat_id: "SEU_CHAT_ID"
```

### 3. Iniciar o Bot

```powershell
# Ambiente virtual ativado
cd brain
python main.py
```

### 4. Dashboard (Opcional)

```powershell
# Em outro terminal
cd brain/dashboard/backend
python -m uvicorn main:app --port 8000

# Frontend
cd brain/dashboard/frontend
npm install && npm run dev
```

## ⚙️ Configurações Importantes

### Timeframes

| Modo | Timeframes | Uso |
|------|------------|-----|
| Scalping | M1, M5 | Trades rápidos |
| Trend | H1, H4 | Tendências médias |
| Position | D1 | Swing trades |

### Risk Settings

```yaml
risk:
  max_risk_per_trade: 0.01  # 1% por trade
  max_daily_drawdown: 0.05  # 5% máximo diário
  max_open_positions: 3
```

## 📊 Comandos Telegram

| Comando | Descrição |
|---------|-----------|
| `/status` | Status do sistema |
| `/positions` | Posições abertas |
| `/pnl` | Profit/Loss atual |
| `/stop` | Parar bots |
| `/start` | Iniciar bots |

## 🔧 Troubleshooting

### MT5 não conecta

1. Verificar se MT5 está instalado
2. Confirmar credenciais em `config.yaml`
3. Verificar firewall

### Bot não opera

1. Verificar se mercado está aberto
2. Conferir horários de trading em `config.yaml`
3. Ver logs em `data/logs/virtus.log`

## 📁 Estrutura de Arquivos

```
brain/
├── main.py           # Ponto de entrada
├── config/           # Configurações
│   ├── config.yaml   # Config principal
│   └── bots/         # Configs por símbolo
├── src/              # Código fonte
├── data/             # Dados e logs
├── models/           # Modelos ML
└── dashboard/        # Interface web
```

---

**Dica:** Para ambiente de desenvolvimento, use `config.yaml` com `mode: paper_trading` primeiro!
