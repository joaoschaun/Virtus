"""
VIRTUS Session Analyzer
========================

Analisa sessões de mercado para otimização de trading.

Sessões:
- Sydney (21:00-06:00 UTC) - Baixa volatilidade, pares AUD
- Tokyo (00:00-09:00 UTC) - Média volatilidade, pares JPY  
- London (07:00-16:00 UTC) - Alta volatilidade, todos pares
- New York (12:00-21:00 UTC) - Alta volatilidade, USD dominante
- Overlap London/NY (12:00-16:00 UTC) - Máxima volatilidade

Funcionalidades:
- Identifica sessão atual
- Detecta overlaps (melhores horários)
- Ajusta parâmetros por sessão
- Kill Zones para entradas de alta probabilidade
- Recomendações de símbolos por sessão
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime, time, timezone, timedelta
import logging


class TradingSession(Enum):
    """Sessões de trading."""
    SYDNEY = auto()
    TOKYO = auto()
    LONDON = auto()
    NEW_YORK = auto()
    CLOSED = auto()  # Weekend


class SessionQuality(Enum):
    """Qualidade da sessão para trading."""
    EXCELLENT = auto()   # Overlap
    GOOD = auto()        # Sessão principal ativa
    MODERATE = auto()    # Sessão secundária
    POOR = auto()        # Sessão fraca
    AVOID = auto()       # Não operar


@dataclass
class SessionConfig:
    """Configuração de uma sessão."""
    name: str
    start_utc: time
    end_utc: time
    
    # Características
    volatility: str          # 'low', 'medium', 'high', 'very_high'
    typical_range_pct: float # Range típico do par principal
    liquidity: str           # 'low', 'medium', 'high'
    
    # Pares recomendados
    primary_pairs: List[str]
    secondary_pairs: List[str]
    avoid_pairs: List[str]
    
    # Parâmetros de trading
    risk_multiplier: float
    spread_tolerance: float   # Multiplicador do spread normal
    sl_multiplier: float
    tp_multiplier: float
    
    # Kill zones (horários de maior probabilidade)
    kill_zones: List[Tuple[time, time]]


# Configurações das sessões
SESSION_CONFIGS: Dict[TradingSession, SessionConfig] = {
    
    TradingSession.SYDNEY: SessionConfig(
        name='Sydney',
        start_utc=time(21, 0),
        end_utc=time(6, 0),
        volatility='low',
        typical_range_pct=0.003,
        liquidity='low',
        primary_pairs=['AUDUSD', 'NZDUSD', 'AUDJPY'],
        secondary_pairs=['AUDCAD', 'AUDNZD'],
        avoid_pairs=['GBPUSD', 'GBPJPY', 'EURUSD'],
        risk_multiplier=0.6,
        spread_tolerance=1.5,
        sl_multiplier=1.0,
        tp_multiplier=1.0,
        kill_zones=[
            (time(22, 0), time(23, 30)),
            (time(0, 30), time(2, 0)),
        ]
    ),
    
    TradingSession.TOKYO: SessionConfig(
        name='Tokyo',
        start_utc=time(0, 0),
        end_utc=time(9, 0),
        volatility='medium',
        typical_range_pct=0.004,
        liquidity='medium',
        primary_pairs=['USDJPY', 'EURJPY', 'GBPJPY', 'AUDJPY'],
        secondary_pairs=['CHFJPY', 'CADJPY', 'NZDJPY'],
        avoid_pairs=['GBPUSD', 'EURUSD'],
        risk_multiplier=0.8,
        spread_tolerance=1.3,
        sl_multiplier=1.0,
        tp_multiplier=1.1,
        kill_zones=[
            (time(0, 0), time(2, 0)),
            (time(5, 0), time(7, 0)),
        ]
    ),
    
    TradingSession.LONDON: SessionConfig(
        name='London',
        start_utc=time(7, 0),
        end_utc=time(16, 0),
        volatility='high',
        typical_range_pct=0.008,
        liquidity='high',
        primary_pairs=['EURUSD', 'GBPUSD', 'GBPJPY', 'EURGBP'],
        secondary_pairs=['EURJPY', 'USDCHF', 'EURCHF'],
        avoid_pairs=['AUDUSD', 'NZDUSD'],
        risk_multiplier=1.2,
        spread_tolerance=1.0,
        sl_multiplier=1.2,
        tp_multiplier=1.5,
        kill_zones=[
            (time(7, 0), time(9, 0)),    # London Open
            (time(12, 0), time(14, 0)),  # NY/London Overlap start
        ]
    ),
    
    TradingSession.NEW_YORK: SessionConfig(
        name='New York',
        start_utc=time(12, 0),
        end_utc=time(21, 0),
        volatility='high',
        typical_range_pct=0.007,
        liquidity='high',
        primary_pairs=['EURUSD', 'GBPUSD', 'USDCAD', 'USDCHF'],
        secondary_pairs=['USDJPY', 'AUDUSD', 'NZDUSD'],
        avoid_pairs=['EURGBP', 'AUDNZD'],
        risk_multiplier=1.1,
        spread_tolerance=1.0,
        sl_multiplier=1.2,
        tp_multiplier=1.4,
        kill_zones=[
            (time(12, 0), time(14, 0)),  # NY Open + London overlap
            (time(14, 30), time(16, 0)), # Post-London
        ]
    ),
    
    TradingSession.CLOSED: SessionConfig(
        name='Closed',
        start_utc=time(21, 0),
        end_utc=time(21, 0),  # Weekend
        volatility='none',
        typical_range_pct=0.0,
        liquidity='none',
        primary_pairs=[],
        secondary_pairs=[],
        avoid_pairs=['ALL'],
        risk_multiplier=0.0,
        spread_tolerance=0.0,
        sl_multiplier=0.0,
        tp_multiplier=0.0,
        kill_zones=[],
    ),
}


@dataclass
class SessionAnalysisResult:
    """Resultado da análise de sessão."""
    current_session: TradingSession
    session_config: SessionConfig
    active_sessions: List[TradingSession]
    is_overlap: bool
    overlap_sessions: List[TradingSession]
    quality: SessionQuality
    
    # Timing
    session_progress_pct: float  # 0-100
    time_to_next_killzone: int   # minutos
    in_killzone: bool
    current_killzone: Optional[Tuple[time, time]]
    
    # Recomendações
    recommended_symbols: List[str]
    avoid_symbols: List[str]
    
    # Parâmetros ajustados
    risk_multiplier: float
    spread_tolerance: float
    sl_multiplier: float
    tp_multiplier: float
    
    details: Dict[str, Any]


class SessionAnalyzer:
    """
    Analisa sessões de trading para otimização.
    
    Identifica a sessão atual, detecta overlaps,
    e recomenda símbolos e parâmetros otimizados.
    """
    
    def __init__(
        self,
        logger: logging.Logger = None,
        broker_utc_offset: int = 0,  # Offset do broker em relação a UTC
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.broker_utc_offset = broker_utc_offset
    
    def analyze(
        self,
        utc_time: datetime = None,
        symbol: str = None,
    ) -> SessionAnalysisResult:
        """
        Analisa a sessão atual.
        
        Args:
            utc_time: Horário UTC (default: agora)
            symbol: Símbolo sendo tradado (opcional)
            
        Returns:
            SessionAnalysisResult
        """
        if utc_time is None:
            utc_time = datetime.now(timezone.utc)
        
        # Verifica se é fim de semana
        if self._is_weekend(utc_time):
            return self._closed_result()
        
        current_time = utc_time.time()
        
        # Sessões ativas
        active_sessions = self._get_active_sessions(current_time)
        
        if not active_sessions:
            return self._closed_result()
        
        # Sessão principal
        main_session = self._get_main_session(active_sessions, current_time)
        
        # Verifica overlap
        is_overlap = len(active_sessions) > 1
        overlap_sessions = active_sessions if is_overlap else []
        
        # Qualidade da sessão
        quality = self._assess_quality(main_session, active_sessions, current_time, symbol)
        
        # Kill zones
        in_killzone, current_kz = self._check_killzone(main_session, current_time)
        time_to_kz = self._time_to_next_killzone(main_session, current_time)
        
        # Progresso da sessão
        progress = self._calculate_progress(main_session, current_time)
        
        # Símbolos recomendados
        recommended, avoid = self._get_symbol_recommendations(
            active_sessions, is_overlap, symbol
        )
        
        # Parâmetros ajustados
        params = self._calculate_adjusted_params(
            main_session, active_sessions, in_killzone
        )
        
        config = SESSION_CONFIGS[main_session]
        
        return SessionAnalysisResult(
            current_session=main_session,
            session_config=config,
            active_sessions=active_sessions,
            is_overlap=is_overlap,
            overlap_sessions=overlap_sessions,
            quality=quality,
            session_progress_pct=progress,
            time_to_next_killzone=time_to_kz,
            in_killzone=in_killzone,
            current_killzone=current_kz,
            recommended_symbols=recommended,
            avoid_symbols=avoid,
            risk_multiplier=params['risk'],
            spread_tolerance=params['spread'],
            sl_multiplier=params['sl'],
            tp_multiplier=params['tp'],
            details={
                'utc_time': utc_time.isoformat(),
                'sessions_active': [s.name for s in active_sessions],
            }
        )
    
    def _is_weekend(self, dt: datetime) -> bool:
        """Verifica se é fim de semana (mercado fechado)."""
        weekday = dt.weekday()
        
        # Sábado
        if weekday == 5:
            return True
        
        # Domingo até 21:00 UTC
        if weekday == 6 and dt.hour < 21:
            return True
        
        # Sexta após 21:00 UTC
        if weekday == 4 and dt.hour >= 21:
            return True
        
        return False
    
    def _get_active_sessions(self, current_time: time) -> List[TradingSession]:
        """Obtém sessões ativas no horário."""
        active = []
        
        for session, config in SESSION_CONFIGS.items():
            if session == TradingSession.CLOSED:
                continue
            
            if self._is_time_in_range(current_time, config.start_utc, config.end_utc):
                active.append(session)
        
        return active
    
    def _is_time_in_range(
        self,
        check_time: time,
        start: time,
        end: time
    ) -> bool:
        """Verifica se horário está no range (funciona com overnight)."""
        if start <= end:
            return start <= check_time <= end
        else:
            # Overnight (ex: 21:00 - 06:00)
            return check_time >= start or check_time <= end
    
    def _get_main_session(
        self,
        active_sessions: List[TradingSession],
        current_time: time
    ) -> TradingSession:
        """Determina sessão principal."""
        if not active_sessions:
            return TradingSession.CLOSED
        
        if len(active_sessions) == 1:
            return active_sessions[0]
        
        # Em overlap, prioriza por volatilidade/importância
        priority = [
            TradingSession.LONDON,
            TradingSession.NEW_YORK,
            TradingSession.TOKYO,
            TradingSession.SYDNEY,
        ]
        
        for session in priority:
            if session in active_sessions:
                return session
        
        return active_sessions[0]
    
    def _assess_quality(
        self,
        main_session: TradingSession,
        active_sessions: List[TradingSession],
        current_time: time,
        symbol: str = None
    ) -> SessionQuality:
        """Avalia qualidade da sessão para trading."""
        
        if main_session == TradingSession.CLOSED:
            return SessionQuality.AVOID
        
        # Overlap London/NY é excelente
        if TradingSession.LONDON in active_sessions and \
           TradingSession.NEW_YORK in active_sessions:
            return SessionQuality.EXCELLENT
        
        # Overlap Tokyo/London é bom
        if TradingSession.TOKYO in active_sessions and \
           TradingSession.LONDON in active_sessions:
            return SessionQuality.GOOD
        
        config = SESSION_CONFIGS[main_session]
        
        # Verifica se símbolo é adequado para a sessão
        if symbol:
            symbol_upper = symbol.upper()
            if symbol_upper in config.avoid_pairs:
                return SessionQuality.POOR
            if symbol_upper in config.primary_pairs:
                return SessionQuality.GOOD
            if symbol_upper in config.secondary_pairs:
                return SessionQuality.MODERATE
        
        # London e NY sem overlap
        if main_session in [TradingSession.LONDON, TradingSession.NEW_YORK]:
            return SessionQuality.GOOD
        
        # Tokyo
        if main_session == TradingSession.TOKYO:
            return SessionQuality.MODERATE
        
        # Sydney sozinha
        if main_session == TradingSession.SYDNEY:
            return SessionQuality.POOR
        
        return SessionQuality.MODERATE
    
    def _check_killzone(
        self,
        session: TradingSession,
        current_time: time
    ) -> Tuple[bool, Optional[Tuple[time, time]]]:
        """Verifica se está em kill zone."""
        
        if session == TradingSession.CLOSED:
            return False, None
        
        config = SESSION_CONFIGS[session]
        
        for kz_start, kz_end in config.kill_zones:
            if self._is_time_in_range(current_time, kz_start, kz_end):
                return True, (kz_start, kz_end)
        
        return False, None
    
    def _time_to_next_killzone(
        self,
        session: TradingSession,
        current_time: time
    ) -> int:
        """Calcula minutos até próxima kill zone."""
        
        if session == TradingSession.CLOSED:
            return -1
        
        config = SESSION_CONFIGS[session]
        
        if not config.kill_zones:
            return -1
        
        current_minutes = current_time.hour * 60 + current_time.minute
        
        min_distance = float('inf')
        
        for kz_start, kz_end in config.kill_zones:
            kz_minutes = kz_start.hour * 60 + kz_start.minute
            
            # Se já estamos na KZ
            if self._is_time_in_range(current_time, kz_start, kz_end):
                return 0
            
            # Distância até o início da KZ
            if kz_minutes > current_minutes:
                distance = kz_minutes - current_minutes
            else:
                distance = (24 * 60 - current_minutes) + kz_minutes
            
            min_distance = min(min_distance, distance)
        
        return int(min_distance) if min_distance != float('inf') else -1
    
    def _calculate_progress(
        self,
        session: TradingSession,
        current_time: time
    ) -> float:
        """Calcula progresso da sessão (0-100%)."""
        
        if session == TradingSession.CLOSED:
            return 0.0
        
        config = SESSION_CONFIGS[session]
        
        start_minutes = config.start_utc.hour * 60 + config.start_utc.minute
        end_minutes = config.end_utc.hour * 60 + config.end_utc.minute
        current_minutes = current_time.hour * 60 + current_time.minute
        
        # Ajusta para overnight
        if end_minutes < start_minutes:
            end_minutes += 24 * 60
            if current_minutes < start_minutes:
                current_minutes += 24 * 60
        
        total_duration = end_minutes - start_minutes
        elapsed = current_minutes - start_minutes
        
        if total_duration <= 0:
            return 0.0
        
        progress = (elapsed / total_duration) * 100
        return max(0.0, min(100.0, progress))
    
    def _get_symbol_recommendations(
        self,
        active_sessions: List[TradingSession],
        is_overlap: bool,
        current_symbol: str = None
    ) -> Tuple[List[str], List[str]]:
        """Obtém recomendações de símbolos."""
        
        recommended = set()
        avoid = set()
        
        for session in active_sessions:
            config = SESSION_CONFIGS[session]
            recommended.update(config.primary_pairs)
            
            if is_overlap:
                recommended.update(config.secondary_pairs)
            
            avoid.update(config.avoid_pairs)
        
        # Remove contradições
        avoid = avoid - recommended
        
        return list(recommended), list(avoid)
    
    def _calculate_adjusted_params(
        self,
        main_session: TradingSession,
        active_sessions: List[TradingSession],
        in_killzone: bool
    ) -> Dict[str, float]:
        """Calcula parâmetros ajustados."""
        
        config = SESSION_CONFIGS[main_session]
        
        risk = config.risk_multiplier
        spread = config.spread_tolerance
        sl = config.sl_multiplier
        tp = config.tp_multiplier
        
        # Bonus para overlap
        if len(active_sessions) > 1:
            if TradingSession.LONDON in active_sessions and \
               TradingSession.NEW_YORK in active_sessions:
                risk *= 1.2
                tp *= 1.2
        
        # Bonus para kill zone
        if in_killzone:
            risk *= 1.1
            tp *= 1.1
        
        return {
            'risk': round(risk, 2),
            'spread': round(spread, 2),
            'sl': round(sl, 2),
            'tp': round(tp, 2),
        }
    
    def _closed_result(self) -> SessionAnalysisResult:
        """Retorna resultado para mercado fechado."""
        config = SESSION_CONFIGS[TradingSession.CLOSED]
        
        return SessionAnalysisResult(
            current_session=TradingSession.CLOSED,
            session_config=config,
            active_sessions=[],
            is_overlap=False,
            overlap_sessions=[],
            quality=SessionQuality.AVOID,
            session_progress_pct=0.0,
            time_to_next_killzone=-1,
            in_killzone=False,
            current_killzone=None,
            recommended_symbols=[],
            avoid_symbols=['ALL'],
            risk_multiplier=0.0,
            spread_tolerance=0.0,
            sl_multiplier=0.0,
            tp_multiplier=0.0,
            details={'reason': 'Mercado fechado'},
        )
    
    def is_good_time_to_trade(
        self,
        symbol: str,
        utc_time: datetime = None
    ) -> Tuple[bool, str]:
        """
        Verifica se é bom horário para operar o símbolo.
        
        Returns:
            (is_good, reason)
        """
        result = self.analyze(utc_time, symbol)
        
        if result.quality == SessionQuality.AVOID:
            return False, "Mercado fechado ou sessão inadequada"
        
        if result.quality == SessionQuality.POOR:
            return False, f"Sessão {result.current_session.name} fraca para {symbol}"
        
        symbol_upper = symbol.upper() if symbol else ''
        
        if symbol_upper in result.avoid_symbols:
            return False, f"{symbol} não é recomendado na sessão {result.current_session.name}"
        
        if result.in_killzone:
            return True, f"Em Kill Zone - Excelente timing para {symbol}"
        
        if result.quality == SessionQuality.EXCELLENT:
            return True, f"Overlap {'/'.join([s.name for s in result.overlap_sessions])}"
        
        return True, f"Sessão {result.current_session.name} OK para trading"
    
    def get_next_killzone(self, utc_time: datetime = None) -> Dict[str, Any]:
        """Obtém informações sobre próxima kill zone."""
        result = self.analyze(utc_time)
        
        return {
            'in_killzone': result.in_killzone,
            'current_killzone': str(result.current_killzone) if result.current_killzone else None,
            'time_to_next_minutes': result.time_to_next_killzone,
            'session': result.current_session.name,
        }
    
    def to_dict(self, result: SessionAnalysisResult) -> Dict[str, Any]:
        """Converte resultado para dicionário."""
        return {
            'session': result.current_session.name,
            'quality': result.quality.name,
            'active_sessions': [s.name for s in result.active_sessions],
            'is_overlap': result.is_overlap,
            'overlap_sessions': [s.name for s in result.overlap_sessions],
            'progress_pct': round(result.session_progress_pct, 1),
            'in_killzone': result.in_killzone,
            'time_to_killzone_min': result.time_to_next_killzone,
            'recommended_symbols': result.recommended_symbols,
            'avoid_symbols': result.avoid_symbols,
            'parameters': {
                'risk_multiplier': result.risk_multiplier,
                'spread_tolerance': result.spread_tolerance,
                'sl_multiplier': result.sl_multiplier,
                'tp_multiplier': result.tp_multiplier,
            },
            'session_config': {
                'volatility': result.session_config.volatility,
                'liquidity': result.session_config.liquidity,
                'primary_pairs': result.session_config.primary_pairs,
            },
        }
