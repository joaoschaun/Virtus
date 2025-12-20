//+------------------------------------------------------------------+
//|                                         VirtusDataServer.mq4     |
//|                                 Servidor de dados para Virtus    |
//|                                              ZeroMQ + HTTP       |
//+------------------------------------------------------------------+
#property copyright "Virtus Trading System"
#property link      "https://virtusinvestimentos.com.br"
#property version   "1.00"
#property strict

// Configurações do servidor HTTP
input string   ServerURL = "http://127.0.0.1:8000";  // URL completa do servidor
input int      UpdateInterval = 30;         // Intervalo de atualização (segundos)
input bool     SendOnTrade = true;          // Enviar ao abrir/fechar trade
input bool     AutoSync = true;             // Sincronização automática

// Variáveis globais
datetime lastUpdate = 0;
int lastTicket = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                     |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("🚀 Virtus Data Server iniciado!");
   Print("📡 Servidor: ", ServerURL);
   Print("⏱️ Intervalo: ", UpdateInterval, " segundos");
   
   // Enviar dados iniciais
   SendAccountData();
   SendHistoryData();
   
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
   Print("❌ Virtus Data Server encerrado");
}

//+------------------------------------------------------------------+
//| Timer function                                                     |
//+------------------------------------------------------------------+
void OnTimer()
{
   if(AutoSync)
   {
      SendAccountData();
      CheckNewTrades();
   }
}

//+------------------------------------------------------------------+
//| Trade function                                                     |
//+------------------------------------------------------------------+
void OnTrade()
{
   if(SendOnTrade)
   {
      Sleep(1000); // Espera 1 segundo para trade ser processado
      SendAccountData();
      SendHistoryData();
   }
}

//+------------------------------------------------------------------+
//| Envia dados da conta via HTTP POST                                 |
//+------------------------------------------------------------------+
void SendAccountData()
{
   string url = ServerURL + "/api/mt4-account/sync/account";
   
   // Montar JSON com dados da conta
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
   json += "\"company\":\"" + AccountCompany() + "\"";
   json += "}";
   
   // Enviar via HTTP
   string result = HttpPost(url, json);
   
   if(StringLen(result) > 0)
   {
      Print("✅ Dados da conta sincronizados");
   }
   else
   {
      Print("⚠️ Erro ao sincronizar conta");
   }
   
   lastUpdate = TimeCurrent();
}

//+------------------------------------------------------------------+
//| Envia histórico de trades                                          |
//+------------------------------------------------------------------+
void SendHistoryData()
{
   string url = ServerURL + "/api/mt4-account/sync/trades";
   
   // Buscar histórico dos últimos 30 dias
   datetime startTime = TimeCurrent() - 30 * 24 * 60 * 60;
   
   string json = "[";
   bool first = true;
   
   // Iterar pelo histórico
   int total = OrdersHistoryTotal();
   
   for(int i = total - 1; i >= 0 && i >= total - 100; i--) // Últimos 100 trades
   {
      if(OrderSelect(i, SELECT_BY_POS, MODE_HISTORY))
      {
         if(OrderCloseTime() < startTime) continue;
         if(OrderType() > OP_SELL) continue; // Ignorar pending orders canceladas
         
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
   
   // Enviar via HTTP
   string result = HttpPost(url, json);
   
   if(StringLen(result) > 0)
   {
      Print("✅ Histórico sincronizado: ", total, " trades");
   }
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
            SendHistoryData();
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Envia posições abertas                                             |
//+------------------------------------------------------------------+
void SendOpenPositions()
{
   string url = ServerURL + "/api/mt4-account/sync/positions";
   
   string json = "[";
   bool first = true;
   
   int total = OrdersTotal();
   
   for(int i = 0; i < total; i++)
   {
      if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
      {
         if(OrderType() > OP_SELL) continue; // Ignorar pending orders
         
         if(!first) json += ",";
         first = false;
         
         json += "{";
         json += "\"ticket\":" + IntegerToString(OrderTicket()) + ",";
         json += "\"symbol\":\"" + OrderSymbol() + "\",";
         json += "\"type\":\"" + (OrderType() == OP_BUY ? "BUY" : "SELL") + "\",";
         json += "\"volume\":" + DoubleToString(OrderLots(), 2) + ",";
         json += "\"open_price\":" + DoubleToString(OrderOpenPrice(), 5) + ",";
         json += "\"current_price\":" + DoubleToString(OrderClosePrice(), 5) + ",";
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
   
   HttpPost(url, json);
}

//+------------------------------------------------------------------+
//| Função HTTP POST usando WebRequest                                 |
//+------------------------------------------------------------------+
string HttpPost(string url, string data)
{
   string headers = "Content-Type: application/json\r\n";
   char post[];
   char result[];
   string resultHeaders;
   
   StringToCharArray(data, post, 0, StringLen(data));
   
   int timeout = 5000; // 5 segundos
   
   int res = WebRequest(
      "POST",           // Método
      url,              // URL
      headers,          // Headers
      timeout,          // Timeout
      post,             // Dados POST
      result,           // Resultado
      resultHeaders     // Headers do resultado
   );
   
   if(res == -1)
   {
      int error = GetLastError();
      if(error == 4014)
      {
         Print("❌ Erro: Adicione a URL nas opções do MT4!");
         Print("   Vá em: Tools → Options → Expert Advisors");
         Print("   Marque: Allow WebRequest for listed URL");
         Print("   Adicione: ", ServerURL);
      }
      else
      {
         Print("❌ Erro HTTP: ", error);
      }
      return "";
   }
   
   return CharArrayToString(result);
}

//+------------------------------------------------------------------+
//| Força sincronização manual (pode ser chamada via botão)           |
//+------------------------------------------------------------------+
void ForceSync()
{
   Print("🔄 Forçando sincronização...");
   SendAccountData();
   SendHistoryData();
   SendOpenPositions();
   Print("✅ Sincronização completa!");
}
//+------------------------------------------------------------------+
