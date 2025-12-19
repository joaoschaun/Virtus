/**
 * VIRTUS Trading System - Brapi Service
 * Serviço para integração com a API Brapi no frontend
 */

import api from './api';

// ==================== TIPOS ====================

export interface StockQuote {
  symbol: string;
  shortName: string;
  longName: string;
  currency: string;
  regularMarketPrice: number;
  regularMarketChange: number;
  regularMarketChangePercent: number;
  regularMarketDayHigh: number;
  regularMarketDayLow: number;
  regularMarketVolume: number;
  regularMarketPreviousClose: number;
  regularMarketOpen: number;
  marketCap: number;
  fiftyTwoWeekHigh: number;
  fiftyTwoWeekLow: number;
  logourl?: string;
  priceEarnings?: number;
  earningsPerShare?: number;
  historicalDataPrice?: HistoricalDataPoint[];
  dividendsData?: DividendsData;
  summaryProfile?: SummaryProfile;
  financialData?: FinancialData;
  balanceSheetHistory?: BalanceSheetItem[];
}

export interface HistoricalDataPoint {
  date: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  adjustedClose: number;
}

export interface DividendsData {
  cashDividends: CashDividend[];
  stockDividends: StockDividend[];
  subscriptions: any[];
}

export interface CashDividend {
  assetIssued: string;
  paymentDate: string;
  rate: number;
  relatedTo: string;
  approvedOn: string | null;
  isinCode: string;
  label: string;
  lastDatePrior: string;
  remarks: string;
}

export interface StockDividend {
  assetIssued: string;
  factor: number;
  completeFactor: string;
  approvedOn: string;
  isinCode: string;
  label: string;
  lastDatePrior: string;
  remarks: string;
}

export interface SummaryProfile {
  symbol: string;
  address1: string;
  city: string;
  state: string;
  country: string;
  phone: string;
  website: string;
  industry: string;
  sector: string;
  longBusinessSummary: string;
  fullTimeEmployees?: number;
}

export interface FinancialData {
  symbol: string;
  currentPrice: number;
  ebitda: number;
  quickRatio: number;
  currentRatio: number;
  debtToEquity: number;
  revenuePerShare: number;
  returnOnAssets: number;
  returnOnEquity: number;
  earningsGrowth: number;
  revenueGrowth: number;
  grossMargins: number;
  ebitdaMargins: number;
  operatingMargins: number;
  profitMargins: number;
  totalCash: number;
  totalDebt: number;
  totalRevenue: number;
  freeCashflow: number;
}

export interface BalanceSheetItem {
  symbol: string;
  type: string;
  endDate: string;
  totalAssets: number;
  totalLiab: number;
  totalStockholderEquity: number;
  cash: number;
  totalDebt: number;
}

export interface CryptoQuote {
  coin: string;
  coinName: string;
  currency: string;
  regularMarketPrice: number;
  regularMarketChange: number;
  regularMarketChangePercent: number;
  regularMarketDayHigh: number;
  regularMarketDayLow: number;
  regularMarketVolume: number;
  marketCap: number;
  coinImageUrl: string;
  historicalDataPrice?: HistoricalDataPoint[];
}

export interface CurrencyQuote {
  fromCurrency: string;
  toCurrency: string;
  name: string;
  high: string;
  low: string;
  bidVariation: string;
  percentageChange: string;
  bidPrice: string;
  askPrice: string;
  updatedAtTimestamp: string;
  updatedAtDate: string;
}

export interface InflationData {
  date: string;
  value: string;
  epochDate: number;
}

export interface PrimeRateData {
  date: string;
  value: string;
  epochDate: number;
}

export interface MarketSummary {
  ibovespa: { results: StockQuote[] } | null;
  currencies: { currency: CurrencyQuote[] } | null;
  crypto: { coins: CryptoQuote[] } | null;
  inflation: { inflation: InflationData[] } | null;
  selic: { 'prime-rate': PrimeRateData[] } | null;
  topGainers: { stocks: StockQuote[] } | null;
  topLosers: { stocks: StockQuote[] } | null;
  timestamp: string;
}

// ==================== AÇÕES ====================

export const getQuote = async (
  tickers: string[],
  options?: {
    range?: string;
    interval?: string;
    fundamental?: boolean;
    dividends?: boolean;
    modules?: string[];
  }
): Promise<{ results: StockQuote[] }> => {
  const params = new URLSearchParams();
  if (options?.range) params.append('range', options.range);
  if (options?.interval) params.append('interval', options.interval);
  if (options?.fundamental) params.append('fundamental', 'true');
  if (options?.dividends) params.append('dividends', 'true');
  if (options?.modules) params.append('modules', options.modules.join(','));
  
  const queryString = params.toString();
  const url = `/api/brapi/quote/${tickers.join(',')}${queryString ? `?${queryString}` : ''}`;
  const response = await api.get(url);
  return response.data;
};

export const getStockList = async (options?: {
  search?: string;
  sortBy?: string;
  sortOrder?: string;
  limit?: number;
}): Promise<{ stocks: StockQuote[] }> => {
  const params = new URLSearchParams();
  if (options?.search) params.append('search', options.search);
  if (options?.sortBy) params.append('sort_by', options.sortBy);
  if (options?.sortOrder) params.append('sort_order', options.sortOrder);
  if (options?.limit) params.append('limit', options.limit.toString());
  
  const response = await api.get(`/api/brapi/stocks?${params.toString()}`);
  
  // Mapear resposta da API para formato StockQuote
  const rawStocks = response.data.stocks || [];
  const mappedStocks: StockQuote[] = rawStocks.map((s: any) => ({
    symbol: s.stock,
    shortName: s.name,
    longName: s.name,
    currency: 'BRL',
    regularMarketPrice: s.close,
    regularMarketChange: 0,
    regularMarketChangePercent: s.change || 0,
    regularMarketDayHigh: s.close,
    regularMarketDayLow: s.close,
    regularMarketVolume: s.volume || 0,
    regularMarketPreviousClose: s.close,
    regularMarketOpen: s.close,
    marketCap: s.market_cap || 0,
    fiftyTwoWeekHigh: s.close,
    fiftyTwoWeekLow: s.close,
    logourl: s.logo,
  }));
  
  return { stocks: mappedStocks };
};

export const getFundamentals = async (
  ticker: string,
  modules?: string[]
): Promise<{ results: StockQuote[] }> => {
  const params = modules ? `?modules=${modules.join(',')}` : '';
  const response = await api.get(`/api/brapi/fundamentals/${ticker}${params}`);
  return response.data;
};

export const getDividends = async (ticker: string): Promise<{
  symbol: string;
  dividendsData: DividendsData;
  priceEarnings: number;
  earningsPerShare: number;
}> => {
  const response = await api.get(`/api/brapi/dividends/${ticker}`);
  return response.data;
};

export const getHistorical = async (
  ticker: string,
  range: string = '1y',
  interval: string = '1d'
): Promise<{
  symbol: string;
  historicalDataPrice: HistoricalDataPoint[];
}> => {
  const response = await api.get(`/api/brapi/historical/${ticker}?range=${range}&interval=${interval}`);
  return response.data;
};

// ==================== SCREENER ====================

// Helper para mapear dados de stocks da API Brapi
const mapBrapiStock = (s: any): StockQuote => ({
  symbol: s.stock,
  shortName: s.name,
  longName: s.name,
  currency: 'BRL',
  regularMarketPrice: s.close || 0,
  regularMarketChange: 0,
  regularMarketChangePercent: s.change || 0,
  regularMarketDayHigh: s.close || 0,
  regularMarketDayLow: s.close || 0,
  regularMarketVolume: s.volume || 0,
  regularMarketPreviousClose: s.close || 0,
  regularMarketOpen: s.close || 0,
  marketCap: s.market_cap || 0,
  fiftyTwoWeekHigh: s.close || 0,
  fiftyTwoWeekLow: s.close || 0,
  logourl: s.logo,
});

export const getTopGainers = async (limit: number = 10): Promise<{ stocks: StockQuote[] }> => {
  const response = await api.get(`/api/brapi/screener/top-gainers?limit=${limit}`);
  const rawStocks = response.data.stocks || [];
  return { stocks: rawStocks.map(mapBrapiStock) };
};

export const getTopLosers = async (limit: number = 10): Promise<{ stocks: StockQuote[] }> => {
  const response = await api.get(`/api/brapi/screener/top-losers?limit=${limit}`);
  const rawStocks = response.data.stocks || [];
  return { stocks: rawStocks.map(mapBrapiStock) };
};

export const getMostTraded = async (limit: number = 10): Promise<{ stocks: StockQuote[] }> => {
  const response = await api.get(`/api/brapi/screener/most-traded?limit=${limit}`);
  const rawStocks = response.data.stocks || [];
  return { stocks: rawStocks.map(mapBrapiStock) };
};

// ==================== FIIs ====================

export const getFIIQuote = async (
  tickers: string[],
  dividends: boolean = true
): Promise<{ results: StockQuote[] }> => {
  const response = await api.get(`/api/brapi/fiis/quote/${tickers.join(',')}?dividends=${dividends}`);
  return response.data;
};

export const searchFIIs = async (
  search?: string,
  limit: number = 100
): Promise<{ fiis: StockQuote[]; count: number }> => {
  const params = new URLSearchParams();
  if (search) params.append('search', search);
  params.append('limit', limit.toString());
  
  const response = await api.get(`/api/brapi/fiis/search?${params.toString()}`);
  return response.data;
};

// ==================== CRIPTOMOEDAS ====================

export const getCryptoQuote = async (
  coins: string[],
  currency: string = 'BRL',
  options?: { range?: string; interval?: string }
): Promise<{ coins: CryptoQuote[] }> => {
  const params = new URLSearchParams();
  params.append('coins', coins.join(','));
  params.append('currency', currency);
  if (options?.range) params.append('range', options.range);
  if (options?.interval) params.append('interval', options.interval);
  
  const response = await api.get(`/api/brapi/crypto/quote?${params.toString()}`);
  return response.data;
};

export const listAvailableCryptos = async (): Promise<{ coins: string[] }> => {
  const response = await api.get('/api/brapi/crypto/available');
  return response.data;
};

// ==================== MOEDAS/CÂMBIO ====================

export const getCurrencyQuote = async (
  pairs: string[]
): Promise<{ currency: CurrencyQuote[] }> => {
  const response = await api.get(`/api/brapi/currency/quote?pairs=${pairs.join(',')}`);
  return response.data;
};

export const listAvailableCurrencies = async (): Promise<{ currencies: string[] }> => {
  const response = await api.get('/api/brapi/currency/available');
  return response.data;
};

// ==================== INFLAÇÃO ====================

export const getInflation = async (options?: {
  country?: string;
  historical?: boolean;
  start?: string;
  end?: string;
  sortBy?: string;
  sortOrder?: string;
}): Promise<{ inflation: InflationData[] }> => {
  const params = new URLSearchParams();
  if (options?.country) params.append('country', options.country);
  // Brapi API requer historical=true para funcionar
  params.append('historical', 'true');
  if (options?.start) params.append('start', options.start);
  if (options?.end) params.append('end', options.end);
  if (options?.sortBy) params.append('sort_by', options.sortBy);
  if (options?.sortOrder) params.append('sort_order', options.sortOrder);
  
  const response = await api.get(`/api/brapi/inflation?${params.toString()}`);
  return response.data;
};

// ==================== TAXA SELIC ====================

export const getSelic = async (options?: {
  country?: string;
  historical?: boolean;
  start?: string;
  end?: string;
  sortBy?: string;
  sortOrder?: string;
}): Promise<{ 'prime-rate': PrimeRateData[] }> => {
  const params = new URLSearchParams();
  if (options?.country) params.append('country', options.country);
  // Só enviar historical se for true (API funciona sem o parâmetro para retornar valor atual)
  if (options?.historical === true) params.append('historical', 'true');
  if (options?.start) params.append('start', options.start);
  if (options?.end) params.append('end', options.end);
  if (options?.sortBy) params.append('sort_by', options.sortBy);
  if (options?.sortOrder) params.append('sort_order', options.sortOrder);
  
  const response = await api.get(`/api/brapi/selic?${params.toString()}`);
  return response.data;
};

// ==================== ÍNDICES ====================

export const getIbovespa = async (): Promise<{ results: StockQuote[] }> => {
  const response = await api.get('/api/brapi/ibovespa');
  return response.data;
};

export const getIFIX = async (): Promise<{ results: StockQuote[] }> => {
  const response = await api.get('/api/brapi/ifix');
  return response.data;
};

// ==================== RESUMO DO MERCADO ====================

export const getMarketSummary = async (): Promise<MarketSummary> => {
  const response = await api.get('/api/brapi/market-summary');
  return response.data;
};

// ==================== HELPERS ====================

export const formatCurrency = (value: number, currency: string = 'BRL'): string => {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: currency,
  }).format(value);
};

export const formatPercent = (value: number): string => {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
};

export const formatNumber = (value: number): string => {
  return new Intl.NumberFormat('pt-BR').format(value);
};

export const formatMarketCap = (value: number): string => {
  if (value >= 1e12) return `R$ ${(value / 1e12).toFixed(2)} tri`;
  if (value >= 1e9) return `R$ ${(value / 1e9).toFixed(2)} bi`;
  if (value >= 1e6) return `R$ ${(value / 1e6).toFixed(2)} mi`;
  return `R$ ${value.toLocaleString('pt-BR')}`;
};

export const getChangeColor = (change: number): string => {
  if (change > 0) return 'text-green-500';
  if (change < 0) return 'text-red-500';
  return 'text-gray-500';
};

export const getChangeBgColor = (change: number): string => {
  if (change > 0) return 'bg-green-100 text-green-800';
  if (change < 0) return 'bg-red-100 text-red-800';
  return 'bg-gray-100 text-gray-800';
};

export default {
  getQuote,
  getStockList,
  getFundamentals,
  getDividends,
  getHistorical,
  getTopGainers,
  getTopLosers,
  getMostTraded,
  getFIIQuote,
  searchFIIs,
  getCryptoQuote,
  listAvailableCryptos,
  getCurrencyQuote,
  listAvailableCurrencies,
  getInflation,
  getSelic,
  getIbovespa,
  getIFIX,
  getMarketSummary,
  formatCurrency,
  formatPercent,
  formatNumber,
  formatMarketCap,
  getChangeColor,
  getChangeBgColor,
};
