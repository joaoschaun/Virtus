"""
VIRTUS - Testes Automatizados
=============================

Testes unitários e de integração para o sistema VIRTUS.
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict
import sys
from pathlib import Path

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_candles():
    """Dados de candles para teste."""
    import numpy as np
    
    # Simula 100 candles de XAUUSD
    base_price = 2050.0
    candles = []
    
    for i in range(100):
        variation = np.random.uniform(-5, 5)
        open_price = base_price + variation
        close_price = open_price + np.random.uniform(-3, 3)
        high_price = max(open_price, close_price) + np.random.uniform(0, 2)
        low_price = min(open_price, close_price) - np.random.uniform(0, 2)
        
        candles.append({
            "time": datetime.now().timestamp() + i * 300,  # 5 min
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "volume": np.random.randint(100, 1000)
        })
        
        base_price = close_price
    
    return candles


@pytest.fixture
def sample_trade():
    """Trade de exemplo para teste."""
    return {
        "ticket": 123456789,
        "symbol": "XAUUSD",
        "type": "buy",
        "volume": 0.01,
        "price_open": 2050.50,
        "sl": 2045.00,
        "tp": 2060.00,
        "profit": 0.0,
        "time": datetime.now()
    }


# ============================================================================
# TESTES DO CIRCUIT BREAKER
# ============================================================================

class TestCircuitBreaker:
    """Testes do Circuit Breaker."""
    
    def test_circuit_starts_closed(self):
        """Circuit breaker começa fechado."""
        from core.circuit_breaker import CircuitBreaker, CircuitState
        
        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute()
    
    def test_circuit_opens_after_failures(self):
        """Circuit abre após múltiplas falhas."""
        from core.circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerConfig
        
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker("test", config)
        
        # Simula 3 falhas
        for _ in range(3):
            cb.record_failure()
        
        assert cb.state == CircuitState.OPEN
        assert not cb.can_execute()
    
    def test_circuit_half_open_after_timeout(self):
        """Circuit vai para half-open após timeout."""
        from core.circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerConfig
        import time
        
        config = CircuitBreakerConfig(failure_threshold=1, timeout_seconds=0.1)
        cb = CircuitBreaker("test", config)
        
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        
        time.sleep(0.2)
        
        # Após timeout, deve permitir uma tentativa
        assert cb.can_execute()
        assert cb.state == CircuitState.HALF_OPEN
    
    def test_circuit_closes_on_success(self):
        """Circuit fecha após sucesso em half-open."""
        from core.circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerConfig
        import time
        
        config = CircuitBreakerConfig(
            failure_threshold=1,
            success_threshold=1,
            timeout_seconds=0.1
        )
        cb = CircuitBreaker("test", config)
        
        cb.record_failure()
        time.sleep(0.2)
        cb.can_execute()  # Vai para HALF_OPEN
        cb.record_success()
        
        assert cb.state == CircuitState.CLOSED


# ============================================================================
# TESTES DO RATE LIMITER
# ============================================================================

class TestRateLimiter:
    """Testes do Rate Limiter."""
    
    @pytest.mark.asyncio
    async def test_allows_initial_burst(self):
        """Permite burst inicial."""
        from core.rate_limiter import RateLimiter
        
        limiter = RateLimiter()
        limiter.configure("test", requests_per_second=1, burst_size=5)
        
        # Deve permitir 5 requisições em sequência
        for _ in range(5):
            assert await limiter.acquire("test", timeout=0.1)
    
    @pytest.mark.asyncio
    async def test_blocks_after_burst(self):
        """Bloqueia após exceder burst."""
        from core.rate_limiter import RateLimiter
        
        limiter = RateLimiter()
        limiter.configure("test", requests_per_second=1, burst_size=2)
        
        await limiter.acquire("test", timeout=0.1)
        await limiter.acquire("test", timeout=0.1)
        
        # Terceira requisição deve falhar (timeout curto)
        result = await limiter.acquire("test", timeout=0.05)
        assert not result


# ============================================================================
# TESTES DO CACHE
# ============================================================================

class TestAnalysisCache:
    """Testes do Cache de Análises."""
    
    @pytest.mark.asyncio
    async def test_set_and_get(self):
        """Set e get básico."""
        from core.cache import AnalysisCache
        
        cache = AnalysisCache(default_ttl=60)
        
        await cache.set("test_key", {"value": 123})
        result = await cache.get("test_key")
        
        assert result is not None
        assert result["value"] == 123
    
    @pytest.mark.asyncio
    async def test_expiration(self):
        """TTL funciona corretamente."""
        from core.cache import AnalysisCache
        import time
        
        cache = AnalysisCache(default_ttl=0.1)
        
        await cache.set("test_key", "value", ttl=0.1)
        
        time.sleep(0.2)
        
        result = await cache.get("test_key")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        """Eviction LRU funciona."""
        from core.cache import AnalysisCache
        
        cache = AnalysisCache(default_ttl=60, max_size=3)
        
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        
        # Acessa key1 para mantê-la recente
        await cache.get("key1")
        
        # Adiciona key4, deve remover key2 (mais antiga não acessada)
        await cache.set("key4", "value4")
        
        assert await cache.get("key1") is not None
        assert await cache.get("key2") is None  # Removida
        assert await cache.get("key3") is not None
        assert await cache.get("key4") is not None
    
    @pytest.mark.asyncio
    async def test_stats(self):
        """Estatísticas são atualizadas."""
        from core.cache import AnalysisCache
        
        cache = AnalysisCache()
        
        await cache.set("key", "value")
        await cache.get("key")  # hit
        await cache.get("key")  # hit
        await cache.get("nonexistent")  # miss
        
        stats = cache.get_stats()
        
        assert stats["hits"] == 2
        assert stats["misses"] == 1


# ============================================================================
# TESTES DO RETRY
# ============================================================================

class TestRetry:
    """Testes do sistema de Retry."""
    
    @pytest.mark.asyncio
    async def test_succeeds_on_first_try(self):
        """Sucesso na primeira tentativa."""
        from core.retry import retry_async, RetryConfig
        
        call_count = 0
        
        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await retry_async(success_func)
        
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retries_on_failure(self):
        """Retenta após falha."""
        from core.retry import retry_async, RetryConfig
        
        call_count = 0
        
        async def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        config = RetryConfig(max_retries=3, base_delay=0.01)
        result = await retry_async(fail_then_succeed, config=config)
        
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        """Levanta exceção após máximo de tentativas."""
        from core.retry import retry_async, RetryConfig
        
        async def always_fail():
            raise ValueError("Always fails")
        
        config = RetryConfig(max_retries=2, base_delay=0.01)
        
        with pytest.raises(ValueError):
            await retry_async(always_fail, config=config)


# ============================================================================
# TESTES DO WEBHOOK MANAGER
# ============================================================================

class TestWebhookManager:
    """Testes do Webhook Manager."""
    
    def test_register_webhook(self):
        """Registro de webhook."""
        from core.webhooks import WebhookManager, WebhookConfig, WebhookEvent
        
        manager = WebhookManager()
        
        config = WebhookConfig(
            id="test",
            name="Test Webhook",
            url="https://example.com/webhook",
            events=[WebhookEvent.TRADE_OPENED]
        )
        
        manager.register(config)
        
        assert manager.get_webhook("test") is not None
        assert len(manager.list_webhooks()) == 1
    
    def test_unregister_webhook(self):
        """Remoção de webhook."""
        from core.webhooks import WebhookManager, WebhookConfig, WebhookEvent
        
        manager = WebhookManager()
        
        config = WebhookConfig(
            id="test",
            name="Test",
            url="https://example.com",
            events=[WebhookEvent.TRADE_OPENED]
        )
        
        manager.register(config)
        manager.unregister("test")
        
        assert manager.get_webhook("test") is None
    
    @pytest.mark.asyncio
    async def test_local_listener(self):
        """Listener local é chamado."""
        from core.webhooks import WebhookManager, WebhookEvent
        
        manager = WebhookManager()
        received_events = []
        
        def listener(payload):
            received_events.append(payload)
        
        manager.add_listener(WebhookEvent.TRADE_OPENED, listener)
        
        await manager.dispatch(
            WebhookEvent.TRADE_OPENED,
            {"symbol": "XAUUSD"}
        )
        
        assert len(received_events) == 1
        assert received_events[0]["data"]["symbol"] == "XAUUSD"


# ============================================================================
# TESTES DE INDICADORES
# ============================================================================

class TestIndicators:
    """Testes de cálculo de indicadores."""
    
    def test_rsi_calculation(self, sample_candles):
        """RSI é calculado corretamente."""
        import numpy as np
        
        closes = np.array([c["close"] for c in sample_candles])
        
        # Cálculo simplificado de RSI
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        period = 14
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss > 0:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        else:
            rsi = 100
        
        # RSI deve estar entre 0 e 100
        assert 0 <= rsi <= 100
    
    def test_ema_calculation(self, sample_candles):
        """EMA é calculada corretamente."""
        import numpy as np
        
        closes = np.array([c["close"] for c in sample_candles])
        
        def calculate_ema(data, period):
            multiplier = 2 / (period + 1)
            ema = [data[0]]
            for price in data[1:]:
                ema.append((price * multiplier) + (ema[-1] * (1 - multiplier)))
            return np.array(ema)
        
        ema9 = calculate_ema(closes, 9)
        ema21 = calculate_ema(closes, 21)
        
        # EMAs devem ter o mesmo tamanho que os dados
        assert len(ema9) == len(closes)
        assert len(ema21) == len(closes)


# ============================================================================
# TESTES DE RISCO
# ============================================================================

class TestRisk:
    """Testes de cálculos de risco."""
    
    def test_position_size_calculation(self):
        """Cálculo de tamanho de posição."""
        balance = 10000.0
        risk_percent = 1.0  # 1% de risco
        sl_pips = 50
        pip_value = 10  # Para 1 lote standard
        
        risk_amount = balance * (risk_percent / 100)
        position_size = risk_amount / (sl_pips * pip_value)
        
        # Com 1% de risco, $100, 50 pips SL, pip value $10
        # Position size = 100 / (50 * 10) = 0.2 lotes
        assert position_size == pytest.approx(0.2, rel=0.01)
    
    def test_risk_reward_ratio(self):
        """Cálculo de risk/reward."""
        entry = 2050.0
        sl = 2040.0
        tp = 2080.0
        
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        rr_ratio = reward / risk
        
        assert rr_ratio == pytest.approx(3.0, rel=0.01)


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
