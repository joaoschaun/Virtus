# 🤖 Virtus MT4 Data Server - Expert Advisor

Este Expert Advisor (EA) sincroniza automaticamente os dados da sua conta MT4 com o sistema Virtus.

## 📋 Funcionalidades

- ✅ Sincronização automática a cada 30 segundos (configurável)
- ✅ Envia dados da conta (balance, equity, profit)
- ✅ Envia histórico de trades fechados
- ✅ Envia posições abertas
- ✅ Detecta novos trades automaticamente
- ✅ Não interfere no trading manual ou outros EAs

## 🔧 Instalação

### Passo 1: Copiar o arquivo

1. Copie o arquivo `VirtusDataServer.mq4` para:
   ```
   C:\Users\[SEU_USUARIO]\AppData\Roaming\MetaQuotes\Terminal\[ID_TERMINAL]\MQL4\Experts\
   ```
   
   Ou no MT4: `File → Open Data Folder → MQL4 → Experts`

### Passo 2: Compilar o EA

1. Abra o MetaEditor (F4 no MT4)
2. Abra o arquivo `VirtusDataServer.mq4`
3. Clique em `Compile` (F7)
4. Verifique se não há erros

### Passo 3: Configurar WebRequest

**IMPORTANTE**: O MT4 bloqueia requisições HTTP por padrão. Você precisa liberar:

1. No MT4, vá em: `Tools → Options → Expert Advisors`
2. Marque: ☑️ `Allow WebRequest for listed URL`
3. Adicione a URL: `http://SEU_IP_DO_SERVIDOR:8000`
   - Se local: `http://localhost:8000`
   - Se remoto: `http://virtusinvestimentos.com.br:8000`
4. Clique em `OK`

### Passo 4: Ativar o EA

1. No MT4, vá em: `View → Navigator` (Ctrl+N)
2. Expanda `Expert Advisors`
3. Arraste `VirtusDataServer` para qualquer gráfico
4. Na janela de configuração:
   - `ServerIP`: IP do servidor Virtus (ex: `localhost` ou `virtusinvestimentos.com.br`)
   - `ServerPort`: Porta do backend (padrão: `8000`)
   - `UpdateInterval`: Intervalo em segundos (padrão: `30`)
   - `SendOnTrade`: Enviar ao abrir/fechar trade (padrão: `true`)
   - `AutoSync`: Sincronização automática (padrão: `true`)
5. Clique em `OK`

### Passo 5: Verificar funcionamento

1. Verifique se aparece um "smiley" 😊 no canto do gráfico
2. Na aba `Experts` (Ctrl+E), você deve ver:
   ```
   🚀 Virtus Data Server iniciado!
   📡 Servidor: localhost:8000
   ⏱️ Intervalo: 30 segundos
   ✅ Dados da conta sincronizados
   ✅ Histórico sincronizado: X trades
   ```

## ⚙️ Configurações

| Parâmetro | Padrão | Descrição |
|-----------|--------|-----------|
| `ServerIP` | localhost | IP do servidor Virtus |
| `ServerPort` | 8000 | Porta do backend |
| `UpdateInterval` | 30 | Intervalo de atualização (segundos) |
| `SendOnTrade` | true | Enviar dados ao abrir/fechar trade |
| `AutoSync` | true | Sincronização automática |

## 🔍 Solução de Problemas

### Erro: "Adicione a URL nas opções do MT4"

O WebRequest não está configurado. Siga o Passo 3 acima.

### EA não aparece na lista

1. Verifique se o arquivo está na pasta correta
2. Reinicie o MT4
3. Tente compilar novamente no MetaEditor

### Dados não aparecem no dashboard

1. Verifique se o servidor está rodando
2. Confira o IP e porta nas configurações
3. Verifique os logs na aba `Experts` do MT4

### Erro de conexão

1. Verifique se o firewall permite conexões na porta 8000
2. Teste a URL no navegador: `http://SEU_IP:8000/api/mt4-account/status`

## 📊 O que é sincronizado

### Dados da Conta
- Login (número da conta)
- Nome do titular
- Servidor (ex: Pepperstone-Live)
- Moeda (USD, EUR, etc)
- Balance
- Equity
- Margem usada
- Margem livre
- Profit flutuante
- Alavancagem

### Histórico de Trades
- Número do ticket
- Símbolo (ex: EURUSD)
- Tipo (BUY/SELL)
- Volume (lotes)
- Preço de abertura
- Preço de fechamento
- Data/hora de abertura
- Data/hora de fechamento
- Profit
- Swap
- Comissão
- Stop Loss
- Take Profit
- Comentário

### Posições Abertas
- Todas as posições abertas em tempo real
- Profit flutuante atualizado

## 🔒 Segurança

- O EA apenas **LEIA** dados - não faz operações de trading
- Não envia senhas ou dados sensíveis
- Conexão direta ao seu servidor

## 📞 Suporte

Se tiver problemas, verifique:
1. Logs na aba `Experts` do MT4
2. Console do backend Virtus
3. Dashboard: `/mt4-account`

---

**Versão**: 1.0.0  
**Compatível com**: MetaTrader 4 Build 1000+
