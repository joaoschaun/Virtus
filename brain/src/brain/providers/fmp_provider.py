"""
VIRTUS Brain - FMP Provider
============================

Provider para API Financial Modeling Prep - COT e calendário.

API Docs: https://site.financialmodelingprep.com/developer/docs
Features:
- Relatórios COT (Commitment of Traders)
- Calendário econômico
- Dados fundamentais
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from .base_provider import CalendarProvider
from ...core.logger import get_logger
from ...core.types import EconomicEvent, NewsImpact
from ..cache import CacheManager
from ..budget import BudgetManager

logger = get_logger("fmp")


class FMPProvider(CalendarProvider):
    """
    Provider para Financial Modeling Prep API.
    
    Principal fonte para:
    - Relatórios COT (posicionamento institucional)
    - Calendário econômico
    """
    
    PROVIDER_NAME = "fmp"
    BASE_URL = "https://financialmodelingprep.com/api/v3"
    
    # Mapeamento de símbolos para COT
    COT_SYMBOL_MAP = {
        'XAUUSD': 'GOLD',
        'EURUSD': 'EURO FX',
        'GBPUSD': 'BRITISH POUND',
    }
    
    def __init__(
        self,
        api_key: str,
        cache_manager: Optional[CacheManager] = None,
        budget_manager: Optional[BudgetManager] = None
    ):
        super().__init__(
            api_key=api_key,
            cache_manager=cache_manager,
            budget_manager=budget_manager
        )
    
    def _get_params(self) -> Dict[str, str]:
        """Parâmetros base"""
        return {'apikey': self.api_key}
    
    # ========================================================================
    # MÉTODOS PÚBLICOS
    # ========================================================================
    
    async def health_check(self) -> bool:
        """Verifica se a API está disponível"""
        try:
            params = self._get_params()
            await self.get('is-the-market-open', params=params)
            return True
        except Exception as e:
            logger.error(f"FMP health check falhou: {e}")
            return False
    
    async def get_supported_symbols(self) -> List[str]:
        """Retorna símbolos suportados para COT"""
        return list(self.COT_SYMBOL_MAP.keys())
    
    async def get_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        currencies: Optional[List[str]] = None
    ) -> List[EconomicEvent]:
        """
        Busca eventos do calendário econômico.
        
        Args:
            start_date: Data inicial
            end_date: Data final
            currencies: Moedas para filtrar
            
        Returns:
            Lista de EconomicEvent
        """
        if start_date is None:
            start_date = datetime.now()
        if end_date is None:
            end_date = start_date + timedelta(days=7)
        
        params = self._get_params()
        params['from'] = start_date.strftime('%Y-%m-%d')
        params['to'] = end_date.strftime('%Y-%m-%d')
        
        try:
            response = await self.get('economic_calendar', params=params)
            
            events = []
            for item in response:
                event = self._parse_economic_event(item)
                if event:
                    if currencies is None or event.currency in currencies:
                        events.append(event)
            
            events.sort(key=lambda x: x.timestamp)
            
            logger.debug(f"FMP: {len(events)} eventos encontrados")
            return events
            
        except Exception as e:
            logger.error(f"Erro ao buscar calendário FMP: {e}")
            return []
    
    async def get_cot_report(
        self,
        symbol: str
    ) -> Optional[Dict[str, Any]]:
        """
        Busca último relatório COT para um símbolo.
        
        Args:
            symbol: Símbolo (ex: 'XAUUSD')
            
        Returns:
            Dict com dados do COT
        """
        cot_symbol = self.COT_SYMBOL_MAP.get(symbol)
        if not cot_symbol:
            logger.warning(f"Símbolo {symbol} não suportado para COT")
            return None
        
        params = self._get_params()
        
        try:
            response = await self.get('cot_search', params=params)
            
            # Filtra pelo símbolo
            for report in response:
                if cot_symbol.lower() in report.get('name', '').lower():
                    return self._parse_cot_report(report, symbol)
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar COT FMP: {e}")
            return None
    
    async def get_cot_analysis(
        self,
        symbol: str
    ) -> Dict[str, Any]:
        """
        Análise do relatório COT.
        
        Args:
            symbol: Símbolo
            
        Returns:
            Dict com análise do COT
        """
        cot = await self.get_cot_report(symbol)
        
        if not cot:
            return {
                'symbol': symbol,
                'available': False,
                'message': 'Dados COT não disponíveis'
            }
        
        # Calcula variações e bias
        commercial_net = cot.get('commercial_long', 0) - cot.get('commercial_short', 0)
        non_commercial_net = cot.get('non_commercial_long', 0) - cot.get('non_commercial_short', 0)
        
        # Determina bias institucional
        if non_commercial_net > 0:
            bias = 'BULLISH' if non_commercial_net > cot.get('non_commercial_net_prev', 0) else 'NEUTRAL_BULLISH'
        else:
            bias = 'BEARISH' if non_commercial_net < cot.get('non_commercial_net_prev', 0) else 'NEUTRAL_BEARISH'
        
        return {
            'symbol': symbol,
            'available': True,
            'report_date': cot.get('report_date'),
            'commercial_net': commercial_net,
            'non_commercial_net': non_commercial_net,
            'institutional_bias': bias,
            'analysis_pt': self._generate_cot_analysis(symbol, bias, non_commercial_net)
        }
    
    async def get_market_status(self) -> Dict[str, Any]:
        """Verifica status do mercado"""
        params = self._get_params()
        
        try:
            response = await self.get('is-the-market-open', params=params)
            return response
        except Exception as e:
            logger.error(f"Erro ao verificar status do mercado: {e}")
            return {}
    
    # ========================================================================
    # MÉTODOS PRIVADOS
    # ========================================================================
    
    def _parse_economic_event(
        self,
        data: Dict[str, Any]
    ) -> Optional[EconomicEvent]:
        """Converte resposta da API em EconomicEvent"""
        try:
            # Parse timestamp
            date_str = data.get('date', '')
            if date_str:
                timestamp = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                return None
            
            # Impacto
            impact_raw = data.get('impact', 'Low')
            impact_map = {
                'Low': NewsImpact.LOW,
                'Medium': NewsImpact.MEDIUM,
                'High': NewsImpact.HIGH,
            }
            impact = impact_map.get(impact_raw, NewsImpact.LOW)
            
            return EconomicEvent(
                name=data.get('event', ''),
                country=data.get('country', ''),
                currency=data.get('currency', ''),
                timestamp=timestamp,
                impact=impact,
                actual=self._safe_float(data.get('actual')),
                forecast=self._safe_float(data.get('estimate')),
                previous=self._safe_float(data.get('previous')),
            )
            
        except Exception as e:
            logger.warning(f"Erro ao parsear evento FMP: {e}")
            return None
    
    def _parse_cot_report(
        self,
        data: Dict[str, Any],
        symbol: str
    ) -> Dict[str, Any]:
        """Parse do relatório COT"""
        return {
            'symbol': symbol,
            'report_date': data.get('date'),
            'name': data.get('name'),
            'commercial_long': data.get('commercial_long', 0),
            'commercial_short': data.get('commercial_short', 0),
            'non_commercial_long': data.get('non_commercial_long', 0),
            'non_commercial_short': data.get('non_commercial_short', 0),
            'total_long': data.get('total_long', 0),
            'total_short': data.get('total_short', 0),
            'open_interest': data.get('open_interest', 0),
        }
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """Converte para float de forma segura"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _generate_cot_analysis(
        self,
        symbol: str,
        bias: str,
        net_position: float
    ) -> str:
        """Gera análise em português"""
        bias_text = {
            'BULLISH': 'Alta (institucionais aumentando posições compradas)',
            'NEUTRAL_BULLISH': 'Levemente altista (mantendo posições compradas)',
            'BEARISH': 'Baixa (institucionais aumentando posições vendidas)',
            'NEUTRAL_BEARISH': 'Levemente baixista (mantendo posições vendidas)',
        }
        
        return (
            f"Análise COT para {symbol}: "
            f"Posição líquida não-comercial: {net_position:,.0f} contratos. "
            f"Viés institucional: {bias_text.get(bias, 'Indefinido')}"
        )
