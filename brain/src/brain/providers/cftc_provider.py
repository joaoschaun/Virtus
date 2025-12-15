"""
VIRTUS Brain - CFTC COT Provider
=================================

Provider para dados COT (Commitment of Traders) da CFTC.
Fonte oficial, gratuita, atualizada toda sexta-feira.

Dados disponíveis:
- Posições de Commercials (hedgers)
- Posições de Non-Commercials (speculators)
- Open Interest
- Changes from previous week
"""

import asyncio
import aiohttp
import ssl
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from ...core.logger import get_logger

logger = get_logger("cftc")


@dataclass
class COTReport:
    """Estrutura para dados COT"""
    symbol: str
    report_date: datetime
    
    # Non-Commercial (Speculators)
    nc_long: int
    nc_short: int
    nc_spreading: int
    nc_net: int  # long - short
    
    # Commercial (Hedgers)
    comm_long: int
    comm_short: int
    comm_net: int
    
    # Total
    total_long: int
    total_short: int
    open_interest: int
    
    # Changes
    nc_change: int = 0
    comm_change: int = 0
    oi_change: int = 0
    
    # Analysis
    sentiment: str = "neutral"  # bullish, bearish, neutral
    explanation_pt: str = ""


class CFTCProvider:
    """
    Provider para COT Reports da CFTC.
    
    Fonte oficial e gratuita para:
    - Gold futures (COMEX)
    - Euro futures (CME)
    - British Pound futures (CME)
    - Japanese Yen futures (CME)
    """
    
    PROVIDER_NAME = "cftc"
    BASE_URL = "https://www.cftc.gov/dea/newcot"
    
    # Mapeamento de símbolos para nomes no relatório CFTC
    SYMBOL_MAPPING = {
        'XAUUSD': ['GOLD', 'COMEX'],
        'EURUSD': ['EURO FX', 'CME'],
        'GBPUSD': ['BRITISH POUND', 'CME'],
        'USDJPY': ['JAPANESE YEN', 'CME'],
        'USDCHF': ['SWISS FRANC', 'CME'],
        'AUDUSD': ['AUSTRALIAN DOLLAR', 'CME'],
        'USDCAD': ['CANADIAN DOLLAR', 'CME'],
        'NZDUSD': ['NEW ZEALAND DOLLAR', 'CME'],
        'XAGUSD': ['SILVER', 'COMEX'],
    }
    
    # Índices das colunas no arquivo CSV da CFTC
    COL_MAP = {
        'market_name': 0,
        'report_date': 2,
        'open_interest': 7,
        'nc_long': 8,
        'nc_short': 9,
        'nc_spreading': 10,
        'comm_long': 11,
        'comm_short': 12,
        'total_long': 13,
        'total_short': 14,
        'nc_change_long': 15,
        'nc_change_short': 16,
        'comm_change_long': 19,
        'comm_change_short': 20,
        'oi_change': 23,
    }
    
    def __init__(self):
        self._cache: Dict[str, COTReport] = {}
        self._last_update: Optional[datetime] = None
        self._raw_data: List[List[str]] = []
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Cria sessão com SSL flexível (CFTC às vezes tem problemas de cert)"""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        return aiohttp.ClientSession(connector=connector)
    
    async def health_check(self) -> bool:
        """Verifica disponibilidade do CFTC"""
        try:
            session = await self._get_session()
            async with session:
                url = f"{self.BASE_URL}/deacom.txt"
                async with session.get(url, timeout=15) as resp:
                    return resp.status == 200
        except Exception as e:
            logger.error(f"CFTC health check falhou: {e}")
            return False
    
    async def fetch_latest_data(self) -> bool:
        """
        Baixa os dados mais recentes do CFTC.
        Atualizado toda sexta-feira após mercado fechar.
        """
        try:
            session = await self._get_session()
            async with session:
                # Disaggregated report (mais detalhado)
                url = f"{self.BASE_URL}/deacom.txt"
                
                async with session.get(url, timeout=30) as resp:
                    if resp.status != 200:
                        logger.error(f"CFTC retornou status {resp.status}")
                        return False
                    
                    text = await resp.text()
                    lines = text.strip().split('\n')
                    
                    # Parse CSV
                    self._raw_data = []
                    for line in lines[1:]:  # Skip header
                        cols = line.split(',')
                        if len(cols) > 20:
                            self._raw_data.append(cols)
                    
                    self._last_update = datetime.now()
                    logger.info(f"CFTC: {len(self._raw_data)} registros carregados")
                    return True
                    
        except Exception as e:
            logger.error(f"Erro ao baixar dados CFTC: {e}")
            return False
    
    async def get_cot_report(self, symbol: str) -> Optional[COTReport]:
        """
        Obtém relatório COT para um símbolo.
        
        Args:
            symbol: Símbolo (ex: 'XAUUSD', 'EURUSD')
            
        Returns:
            COTReport com dados ou None
        """
        # Verifica se precisa atualizar (dados têm 1 semana de vida)
        if not self._raw_data or self._needs_refresh():
            await self.fetch_latest_data()
        
        if not self._raw_data:
            return None
        
        # Busca o símbolo
        mapping = self.SYMBOL_MAPPING.get(symbol)
        if not mapping:
            logger.warning(f"Símbolo {symbol} não suportado para COT")
            return None
        
        search_term, exchange = mapping
        
        # Encontra a linha mais recente para este mercado
        latest_row = None
        latest_date = None
        
        for row in self._raw_data:
            market_name = row[self.COL_MAP['market_name']].strip().upper()
            
            if search_term in market_name:
                try:
                    date_str = row[self.COL_MAP['report_date']].strip()
                    report_date = datetime.strptime(date_str, '%Y-%m-%d')
                    
                    if latest_date is None or report_date > latest_date:
                        latest_date = report_date
                        latest_row = row
                except:
                    continue
        
        if not latest_row:
            return None
        
        # Parse dos dados
        try:
            def safe_int(val):
                try:
                    return int(val.strip().replace('"', ''))
                except:
                    return 0
            
            nc_long = safe_int(latest_row[self.COL_MAP['nc_long']])
            nc_short = safe_int(latest_row[self.COL_MAP['nc_short']])
            nc_spreading = safe_int(latest_row[self.COL_MAP['nc_spreading']])
            comm_long = safe_int(latest_row[self.COL_MAP['comm_long']])
            comm_short = safe_int(latest_row[self.COL_MAP['comm_short']])
            total_long = safe_int(latest_row[self.COL_MAP['total_long']])
            total_short = safe_int(latest_row[self.COL_MAP['total_short']])
            open_interest = safe_int(latest_row[self.COL_MAP['open_interest']])
            
            nc_net = nc_long - nc_short
            comm_net = comm_long - comm_short
            
            # Determina sentimento baseado nas posições dos speculators
            if nc_net > 0:
                if nc_net > open_interest * 0.1:  # > 10% do OI
                    sentiment = "bullish"
                else:
                    sentiment = "slightly_bullish"
            elif nc_net < 0:
                if abs(nc_net) > open_interest * 0.1:
                    sentiment = "bearish"
                else:
                    sentiment = "slightly_bearish"
            else:
                sentiment = "neutral"
            
            # Gera explicação em português
            explanation = self._generate_explanation_pt(
                symbol, nc_net, comm_net, open_interest, sentiment
            )
            
            return COTReport(
                symbol=symbol,
                report_date=latest_date,
                nc_long=nc_long,
                nc_short=nc_short,
                nc_spreading=nc_spreading,
                nc_net=nc_net,
                comm_long=comm_long,
                comm_short=comm_short,
                comm_net=comm_net,
                total_long=total_long,
                total_short=total_short,
                open_interest=open_interest,
                sentiment=sentiment,
                explanation_pt=explanation
            )
            
        except Exception as e:
            logger.error(f"Erro ao parsear COT para {symbol}: {e}")
            return None
    
    def _needs_refresh(self) -> bool:
        """Verifica se dados precisam ser atualizados"""
        if not self._last_update:
            return True
        
        # Atualiza se passou mais de 6 horas
        age = datetime.now() - self._last_update
        return age > timedelta(hours=6)
    
    def _generate_explanation_pt(
        self,
        symbol: str,
        nc_net: int,
        comm_net: int,
        oi: int,
        sentiment: str
    ) -> str:
        """Gera explicação em português"""
        
        sentiment_text = {
            "bullish": "fortemente comprado (altista)",
            "slightly_bullish": "levemente comprado",
            "neutral": "neutro",
            "slightly_bearish": "levemente vendido",
            "bearish": "fortemente vendido (baixista)"
        }
        
        direction = "comprados" if nc_net > 0 else "vendidos"
        
        return (
            f"COT Report {symbol}: Especuladores estão {direction} "
            f"(posição líquida: {nc_net:,}). "
            f"Open Interest: {oi:,}. "
            f"Sentimento institucional: {sentiment_text.get(sentiment, 'neutro')}."
        )
    
    async def get_all_cot(self) -> Dict[str, COTReport]:
        """Obtém COT para todos os símbolos suportados"""
        results = {}
        
        for symbol in self.SYMBOL_MAPPING.keys():
            report = await self.get_cot_report(symbol)
            if report:
                results[symbol] = report
        
        return results
