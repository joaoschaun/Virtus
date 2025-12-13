# 🧠 BRAIN - Sistema Multi-Bot Trading

## Descrição
Sistema de trading automatizado multi-símbolo com Brain centralizado, assessor de mercado via Telegram e suporte a múltiplas estratégias.

## Requisitos
- Python 3.11.x (obrigatório para compatibilidade com MT5)

## Instalação

```bash
# Clonar repositório
git clone https://github.com/joaoschaun/Virtus.git
cd Virtus

# Criar ambiente virtual
py -3.11 -m venv env

# Ativar ambiente (Windows)
.\env\Scripts\Activate.ps1

# Instalar dependências
pip install -r requirements.txt
```

## Estrutura do Projeto
```
Virtus/
├── env/                    # Ambiente virtual (não versionado)
├── brain/                  # Código principal do sistema
│   ├── config/             # Configurações (YAML)
│   ├── src/                # Código fonte
│   ├── data/               # Dados persistentes
│   ├── models/             # Modelos ML treinados
│   └── dashboard/          # Dashboard web
├── PROJECT_TRACKER.md      # Tracking do progresso
├── README.md               # Este arquivo
└── requirements.txt        # Dependências
```

## Bots Disponíveis
- **GOLD Bot** (XAUUSD) - Scalping + Trend
- **EURO Bot** (EURUSD) - Scalping + Range
- **GBP Bot** (GBPUSD) - Breakout

## Licença
Proprietário - joaoschaun
