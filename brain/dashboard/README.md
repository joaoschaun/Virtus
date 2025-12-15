# =============================================================================
# VIRTUS TRADING SYSTEM - Dashboard Web
# Professional Institutional Trading Dashboard
# =============================================================================

## 🌟 Visão Geral

Dashboard web profissional de nível institucional para o sistema de trading VIRTUS. 
Interface completa para monitoramento em tempo real, controle de bots e análise de performance.

## 🏗️ Arquitetura

```
dashboard/
├── backend/                 # FastAPI Backend
│   ├── main.py             # Aplicação principal
│   ├── requirements.txt    # Dependências Python
│   ├── Dockerfile          # Container backend
│   ├── routes/             # Rotas da API
│   │   ├── mt5_routes.py   # Integração MetaTrader 5
│   │   └── __init__.py
│   └── websocket/          # WebSocket real-time
│       ├── manager.py      # Gerenciador de conexões
│       └── __init__.py
├── frontend/               # React Frontend
│   ├── src/
│   │   ├── components/     # Componentes React
│   │   ├── pages/          # Páginas da aplicação
│   │   ├── stores/         # Estado global (Zustand)
│   │   ├── services/       # API e WebSocket
│   │   └── lib/            # Utilitários
│   ├── public/             # Assets estáticos
│   ├── package.json        # Dependências Node.js
│   ├── vite.config.ts      # Configuração Vite
│   ├── tailwind.config.js  # Tema TailwindCSS
│   └── Dockerfile          # Container frontend
├── nginx/
│   └── nginx.conf          # Configuração Nginx produção
├── docker-compose.yml      # Orquestração Docker
├── .env.example            # Template variáveis ambiente
└── README.md               # Este arquivo
```

## 🚀 Funcionalidades

### 📊 Dashboard Principal
- Visão geral de métricas em tempo real
- Gráficos de evolução patrimonial
- Indicadores de performance (ROI, Win Rate, Drawdown)
- Status dos bots e estratégias

### 🤖 Controle de Bots
- Ligar/Desligar/Pausar bots individuais
- Configuração de parâmetros em tempo real
- Monitoramento de health status
- Logs de atividade

### 📈 Estratégias
- Toggle de estratégias por bot
- Toggle de símbolos por estratégia
- Estatísticas por estratégia/símbolo
- Histórico de performance

### 💼 Posições
- Posições abertas em tempo real
- Ordens pendentes
- Fechamento manual de posições
- Cancelamento de ordens

### 📜 Histórico
- Histórico completo de trades
- Filtros avançados (data, símbolo, estratégia)
- Exportação de dados
- Estatísticas detalhadas

### 📉 Análise
- Performance por hora/dia da semana
- Atribuição por estratégia/setup/símbolo
- Gráficos de distribuição
- Métricas avançadas

### ⚙️ Configurações
- Parâmetros de risco
- Configurações de trading
- Notificações
- Sistema e manutenção

## 💻 Desenvolvimento Local

### Requisitos
- Node.js 18+
- Python 3.11+
- Docker & Docker Compose

### Backend

```bash
cd backend

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows

# Instalar dependências
pip install -r requirements.txt

# Executar servidor
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# Instalar dependências
npm install

# Executar em desenvolvimento
npm run dev

# Build para produção
npm run build
```

### Docker Compose (Desenvolvimento)

```bash
# Iniciar todos os serviços
docker-compose up -d

# Ver logs
docker-compose logs -f

# Parar serviços
docker-compose down
```

## 🌐 Deploy para Produção

### Cloudflare Setup

1. **DNS Configuration**
   - Adicione um registro A apontando para seu servidor
   - Ative proxy do Cloudflare (nuvem laranja)

2. **SSL/TLS**
   - Configure modo "Full (strict)" no Cloudflare
   - Gere certificado de origem se necessário

3. **Page Rules**
   - Cache Level: Standard para `/assets/*`
   - Browser Cache TTL: 1 year para assets

### Deploy no Servidor

1. **Preparar ambiente**
```bash
# Clonar repositório
git clone https://github.com/seu-repo/virtus.git
cd virtus/brain/dashboard

# Copiar e configurar variáveis
cp .env.example .env
nano .env  # Editar com suas configurações
```

2. **Build e Deploy**
```bash
# Build das imagens
docker-compose build

# Iniciar em modo detached
docker-compose up -d

# Verificar status
docker-compose ps
docker-compose logs -f
```

3. **Verificar saúde**
```bash
# Health check do backend
curl http://localhost:8000/health

# Health check do nginx
curl http://localhost/health
```

### Atualização

```bash
# Pull das últimas mudanças
git pull origin main

# Rebuild e restart
docker-compose build
docker-compose up -d --force-recreate
```

## 🔐 Segurança

### Credenciais Padrão (DEMO)
- **Usuário:** admin
- **Senha:** admin123

⚠️ **IMPORTANTE:** Altere as credenciais padrão em produção!

### Checklist de Segurança
- [ ] Alterar SECRET_KEY e JWT_SECRET_KEY
- [ ] Configurar ALLOWED_ORIGINS corretamente
- [ ] Ativar HTTPS via Cloudflare
- [ ] Configurar rate limiting
- [ ] Remover credenciais demo
- [ ] Configurar firewall do servidor
- [ ] Backup automático do banco de dados

## 📊 API Endpoints

### Autenticação
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/auth/login` | Login |
| POST | `/api/auth/refresh` | Renovar token |
| GET | `/api/auth/me` | Usuário atual |
| POST | `/api/auth/logout` | Logout |

### Dashboard
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/dashboard/overview` | Visão geral |
| GET | `/api/dashboard/metrics` | Métricas |
| GET | `/api/dashboard/equity-history` | Histórico equity |

### Bots
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/bots` | Listar bots |
| POST | `/api/bots/{id}/control` | Controlar bot |
| GET | `/api/bots/{id}/config` | Obter config |
| PUT | `/api/bots/{id}/config` | Atualizar config |

### Posições & Ordens
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/positions` | Posições abertas |
| DELETE | `/api/positions/{ticket}` | Fechar posição |
| GET | `/api/orders` | Ordens pendentes |
| DELETE | `/api/orders/{ticket}` | Cancelar ordem |

### Trades
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/trades` | Histórico trades |
| GET | `/api/trades/stats` | Estatísticas |

### WebSocket
```javascript
// Conectar
const ws = new WebSocket('wss://virtusinvestimentos.com.br/ws');

// Autenticar
ws.send(JSON.stringify({ type: 'auth', token: 'jwt-token' }));

// Subscrever canais
ws.send(JSON.stringify({ type: 'subscribe', channel: 'metrics' }));
ws.send(JSON.stringify({ type: 'subscribe', channel: 'positions' }));
ws.send(JSON.stringify({ type: 'subscribe', channel: 'orders' }));
ws.send(JSON.stringify({ type: 'subscribe', channel: 'alerts' }));
```

## 🎨 Tema e Personalização

O dashboard usa um tema dark institucional com as cores do VIRTUS:

```javascript
colors: {
  virtus: {
    primary: '#00D4AA',    // Verde principal
    secondary: '#1E3A5F',  // Azul escuro
    accent: '#FFD700',     // Dourado
  },
  dark: {
    900: '#0A0F1C',        // Fundo principal
    800: '#111827',        // Cards
    700: '#1F2937',        // Bordas
  }
}
```

## 📱 Responsividade

O dashboard é totalmente responsivo:
- Desktop: Layout completo com sidebar
- Tablet: Sidebar colapsável
- Mobile: Navegação bottom tabs

## 🧪 Testes

```bash
# Backend
cd backend
pytest tests/ -v

# Frontend
cd frontend
npm run test
npm run test:coverage
```

## 📈 Monitoramento

### Métricas Prometheus
- `virtus_trades_total` - Total de trades
- `virtus_profit_total` - Lucro total
- `virtus_positions_open` - Posições abertas
- `virtus_bot_status` - Status dos bots

### Logs
```bash
# Ver logs do backend
docker-compose logs -f backend

# Ver logs do nginx
docker-compose logs -f nginx

# Ver todos os logs
docker-compose logs -f
```

## 🛠️ Troubleshooting

### Backend não inicia
```bash
# Verificar logs
docker-compose logs backend

# Verificar variáveis de ambiente
docker-compose config
```

### Frontend em branco
```bash
# Verificar build
docker-compose exec frontend ls -la /usr/share/nginx/html

# Verificar nginx config
docker-compose exec nginx nginx -t
```

### WebSocket não conecta
- Verificar se o proxy WebSocket está configurado
- Verificar firewall para porta 443/80
- Verificar certificado SSL

## 📄 Licença

Propriedade de VIRTUS Investimentos. Todos os direitos reservados.

## 👥 Suporte

Para suporte técnico, entre em contato através do Telegram.

---

**VIRTUS Trading System** - *Excellence in Automated Trading*
