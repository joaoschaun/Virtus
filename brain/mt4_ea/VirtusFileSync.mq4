//+------------------------------------------------------------------+
//|                                           VirtusFileSync.mq4     |
//|                          Sincronização via arquivo (mais estável)|
//+------------------------------------------------------------------+
#property copyright "Virtus Trading System"
#property link      "https://virtusinvestimentos.com.br"
#property version   "1.00"
#property strict

// Configurações
input int      UpdateInterval = 10;         // Intervalo de atualização (segundos)
input string   DataFolder = "C:\\VirtusData";  // Pasta para salvar dados

// Variáveis globais
datetime lastUpdate = 0;
int lastTicket = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                     |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("🚀 Virtus File Sync iniciado!");
   Print("📁 Pasta de dados: ", DataFolder);
   Print("⏱️ Intervalo: ", UpdateInterval, " segundos");
   
   // Criar pasta se não existir
   // A pasta precisa ser criada manualmente no Windows
   
   // Enviar dados iniciais
   SaveAccountData();
   SaveHistoryData();
   SaveOpenPositions();
   
   // Configurar timer
   EventSetTimer(UpdateInterval);
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                   |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   Print("❌ Virtus File Sync encerrado");
}

//+------------------------------------------------------------------+
//| Timer function                                                     |
//+------------------------------------------------------------------+
void OnTimer()
{
   SaveAccountData();
   CheckNewTrades();
   SaveOpenPositions();
}

//+------------------------------------------------------------------+
//| Trade function                                                     |
//+------------------------------------------------------------------+
void OnTrade()
{
   Sleep(1000);
   SaveAccountData();
   SaveHistoryData();
   SaveOpenPositions();
}

//+------------------------------------------------------------------+
//| Salva dados da conta em arquivo JSON                               |
//+------------------------------------------------------------------+
void SaveAccountData()
{
   string filename = DataFolder + "\\account.json";
   
   int handle = FileOpen(filename, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(handle == INVALID_HANDLE)
   {
      // Tenta criar na pasta comum do MT4
      filename = "account.json";
      handle = FileOpen(filename, FILE_WRITE|FILE_TXT|FILE_COMMON);
      if(handle == INVALID_HANDLE)
      {
         Print("❌ Erro ao abrir arquivo: ", GetLastError());
         return;
      }
   }
   
   string json = "{";
   json += "\"login\":" + IntegerToString(AccountNumber()) + ",";
   json += "\"name\":\"" + AccountName() + "\",";
   json += "\"server\":\"" + AccountServer() + "\",";
   json += "\"currency\":\"" + AccountCurrency() + "\",";
   json += "\"balance\":" + DoubleToString(AccountBalance(), 2) + ",";
   json += "\"equity\":" + DoubleToString(AccountEquity(), 2) + ",";
   json += "\"margin\":" + DoubleToString(AccountMargin(), 2) + ",";
   json += "\"free_margin\":" + DoubleToString(AccountFreeMargin(), 2) + ",";
   json += "\"profit\":" + DoubleToString(AccountProfit(), 2) + ",";
   json += "\"leverage\":" + IntegerToString(AccountLeverage()) + ",";
   json += "\"company\":\"" + AccountCompany() + "\",";
   json += "\"timestamp\":\"" + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + "\"";
   json += "}";
   
   FileWriteString(handle, json);
   FileClose(handle);
   
   Print("✅ Dados da conta salvos");
   lastUpdate = TimeCurrent();
}

//+------------------------------------------------------------------+
//| Salva histórico de trades                                          |
//+------------------------------------------------------------------+
void SaveHistoryData()
{
   string filename = DataFolder + "\\trades.json";
   
   int handle = FileOpen(filename, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(handle == INVALID_HANDLE)
   {
      filename = "trades.json";
      handle = FileOpen(filename, FILE_WRITE|FILE_TXT|FILE_COMMON);
      if(handle == INVALID_HANDLE)
      {
         Print("❌ Erro ao abrir arquivo de trades");
         return;
      }
   }
   
   datetime startTime = TimeCurrent() - 30 * 24 * 60 * 60;
   
   string json = "[";
   bool first = true;
   
   int total = OrdersHistoryTotal();
   
   // Pegar TODOS os trades dos últimos 30 dias (até 1000)
   for(int i = total - 1; i >= 0 && i >= total - 1000; i--)
   {
      if(OrderSelect(i, SELECT_BY_POS, MODE_HISTORY))
      {
         if(OrderCloseTime() < startTime) continue;
         if(OrderType() > OP_SELL) continue;
         
         if(!first) json += ",";
         first = false;
         
         json += "{";
         json += "\"ticket\":" + IntegerToString(OrderTicket()) + ",";
         json += "\"symbol\":\"" + OrderSymbol() + "\",";
         json += "\"type\":\"" + (OrderType() == OP_BUY ? "BUY" : "SELL") + "\",";
         json += "\"volume\":" + DoubleToString(OrderLots(), 2) + ",";
         json += "\"open_price\":" + DoubleToString(OrderOpenPrice(), 5) + ",";
         json += "\"close_price\":" + DoubleToString(OrderClosePrice(), 5) + ",";
         json += "\"open_time\":\"" + TimeToString(OrderOpenTime(), TIME_DATE|TIME_MINUTES) + "\",";
         json += "\"close_time\":\"" + TimeToString(OrderCloseTime(), TIME_DATE|TIME_MINUTES) + "\",";
         json += "\"profit\":" + DoubleToString(OrderProfit(), 2) + ",";
         json += "\"swap\":" + DoubleToString(OrderSwap(), 2) + ",";
         json += "\"commission\":" + DoubleToString(OrderCommission(), 2) + ",";
         json += "\"sl\":" + DoubleToString(OrderStopLoss(), 5) + ",";
         json += "\"tp\":" + DoubleToString(OrderTakeProfit(), 5) + ",";
         json += "\"comment\":\"" + OrderComment() + "\"";
         json += "}";
      }
   }
   
   json += "]";
   
   FileWriteString(handle, json);
   FileClose(handle);
   
   Print("✅ Histórico salvo: ", total, " trades");
}

//+------------------------------------------------------------------+
//| Verifica novos trades                                              |
//+------------------------------------------------------------------+
void CheckNewTrades()
{
   int total = OrdersHistoryTotal();
   
   if(total > 0)
   {
      if(OrderSelect(total - 1, SELECT_BY_POS, MODE_HISTORY))
      {
         int ticket = OrderTicket();
         
         if(ticket != lastTicket)
         {
            lastTicket = ticket;
            Print("📊 Novo trade detectado: #", ticket);
            SaveHistoryData();
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Salva posições abertas                                             |
//+------------------------------------------------------------------+
void SaveOpenPositions()
{
   string filename = DataFolder + "\\positions.json";
   
   int handle = FileOpen(filename, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(handle == INVALID_HANDLE)
   {
      filename = "positions.json";
      handle = FileOpen(filename, FILE_WRITE|FILE_TXT|FILE_COMMON);
      if(handle == INVALID_HANDLE)
      {
         Print("❌ Erro ao abrir arquivo de posições");
         return;
      }
   }
   
   string json = "[";
   bool first = true;
   
   int total = OrdersTotal();
   
   for(int i = 0; i < total; i++)
   {
      if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
      {
         if(OrderType() > OP_SELL) continue;
         
         if(!first) json += ",";
         first = false;
         
         json += "{";
         json += "\"ticket\":" + IntegerToString(OrderTicket()) + ",";
         json += "\"symbol\":\"" + OrderSymbol() + "\",";
         json += "\"type\":\"" + (OrderType() == OP_BUY ? "BUY" : "SELL") + "\",";
         json += "\"volume\":" + DoubleToString(OrderLots(), 2) + ",";
         json += "\"open_price\":" + DoubleToString(OrderOpenPrice(), 5) + ",";
         json += "\"current_price\":" + DoubleToString(MarketInfo(OrderSymbol(), MODE_BID), 5) + ",";
         json += "\"open_time\":\"" + TimeToString(OrderOpenTime(), TIME_DATE|TIME_MINUTES) + "\",";
         json += "\"profit\":" + DoubleToString(OrderProfit(), 2) + ",";
         json += "\"swap\":" + DoubleToString(OrderSwap(), 2) + ",";
         json += "\"sl\":" + DoubleToString(OrderStopLoss(), 5) + ",";
         json += "\"tp\":" + DoubleToString(OrderTakeProfit(), 5) + ",";
         json += "\"comment\":\"" + OrderComment() + "\"";
         json += "}";
      }
   }
   
   json += "]";
   
   FileWriteString(handle, json);
   FileClose(handle);
}
//+------------------------------------------------------------------+
