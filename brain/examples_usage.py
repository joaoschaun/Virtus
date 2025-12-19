"""
VIRTUS - Exemplos de Uso dos Novos Módulos
==========================================

Este arquivo demonstra como usar os novos módulos de infraestrutura.
"""

import asyncio
from pathlib import Path
import sys

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))


# ============================================================================
# 1. CIRCUIT BREAKER - Proteção contra falhas cascata
# ============================================================================

async def example_circuit_breaker():
    """Exemplo de uso do Circuit Breaker."""
    from src.core.circuit_breaker import circuit_breaker_manager, CircuitBreakerConfig
    
    # Configura circuit breaker para um serviço
    circuit_breaker_manager.create_breaker(
        "mt5_connection",
        CircuitBreakerConfig(
            failure_threshold=5,      # Abre após 5 falhas
            timeout_seconds=60,       # Espera 60s antes de tentar novamente
            success_threshold=2,      # Precisa de 2 sucessos para fechar
        )
    )
    
    # Usando como decorador
    from src.core.circuit_breaker import circuit_breaker
    
    @circuit_breaker("mt5_connection")
    async def get_positions():
        """Função protegida pelo circuit breaker."""
        # Sua lógica aqui
        return {"positions": []}
    
    # Verificando estado
    cb = circuit_breaker_manager.get_breaker("mt5_connection")
    print(f"Estado: {cb.state}")
    print(f"Pode executar: {cb.can_execute()}")


# ============================================================================
# 2. RATE LIMITER - Controle de frequência de requisições
# ============================================================================

async def example_rate_limiter():
    """Exemplo de uso do Rate Limiter."""
    from src.core.rate_limiter import rate_limiter
    
    # Configuração já inclui defaults, mas você pode customizar
    rate_limiter.configure("minha_api", requests_per_second=2, burst_size=5)
    
    # Uso básico - aguarda o token estar disponível
    async def fetch_data():
        # Aguarda permissão para executar
        if await rate_limiter.acquire("minha_api"):
            print("Fazendo requisição...")
            # Sua chamada à API aqui
    
    # Usando como decorador
    from src.core.rate_limiter import rate_limited
    
    @rate_limited("finnhub")  # Usa config padrão do finnhub
    async def get_news():
        """Função com rate limiting automático."""
        return {"news": []}
    
    # Verificando estatísticas
    stats = rate_limiter.get_stats()
    print(f"Estatísticas: {stats}")


# ============================================================================
# 3. RETRY COM BACKOFF - Retentativas inteligentes
# ============================================================================

async def example_retry():
    """Exemplo de uso do Retry com Backoff."""
    from src.core.retry import retry_async, RetryConfig, API_RETRY_CONFIG
    
    # Função que pode falhar
    async def unstable_api_call():
        import random
        if random.random() < 0.7:
            raise ConnectionError("Falha temporária")
        return {"data": "success"}
    
    # Usando função diretamente
    try:
        result = await retry_async(
            unstable_api_call,
            config=API_RETRY_CONFIG
        )
        print(f"Resultado: {result}")
    except Exception as e:
        print(f"Falhou após todas as tentativas: {e}")
    
    # Usando como decorador
    from src.core.retry import with_retry
    
    @with_retry(max_retries=3, base_delay=1.0)
    async def get_market_data():
        """Função com retry automático."""
        # Sua lógica aqui
        return {"price": 2050.0}
    
    # Config customizada
    custom_config = RetryConfig(
        max_retries=5,
        base_delay=0.5,
        max_delay=30.0,
        exponential_base=2.0,
        jitter=True,
        retryable_exceptions=(ConnectionError, TimeoutError),
    )


# ============================================================================
# 4. CACHE - Armazenamento temporário de resultados
# ============================================================================

async def example_cache():
    """Exemplo de uso do Cache de Análises."""
    from src.core.cache import analysis_cache, CacheKey
    
    # Set/Get básico
    await analysis_cache.set("market_data:XAUUSD", {"price": 2050.0})
    data = await analysis_cache.get("market_data:XAUUSD")
    print(f"Do cache: {data}")
    
    # Com TTL customizado
    await analysis_cache.set("news:latest", {"headlines": []}, ttl=300)
    
    # Usando como decorador
    from src.core.cache import cached
    
    @cached(key="analysis:XAUUSD", ttl=30)
    async def get_analysis():
        """Resultado é cacheado automaticamente."""
        # Cálculo pesado aqui
        return {"trend": "bullish", "strength": 0.8}
    
    # Gerando chaves
    key = CacheKey.analysis("XAUUSD", "trend")
    await analysis_cache.set(key, {"direction": "up"})
    
    # Estatísticas
    stats = analysis_cache.get_stats()
    print(f"Cache stats: {stats}")
    
    # Limpeza
    await analysis_cache.delete_pattern("analysis:*")  # Remove análises
    await analysis_cache.cleanup()  # Remove expirados


# ============================================================================
# 5. WEBHOOKS - Notificações para sistemas externos
# ============================================================================

async def example_webhooks():
    """Exemplo de uso do sistema de Webhooks."""
    from src.core.webhooks import webhook_manager, WebhookConfig, WebhookEvent
    
    # Registrar um webhook externo
    webhook_manager.register(WebhookConfig(
        id="discord_alerts",
        name="Discord Alerts",
        url="https://discord.com/api/webhooks/xxx/yyy",
        events=[
            WebhookEvent.TRADE_OPENED,
            WebhookEvent.TRADE_CLOSED,
            WebhookEvent.ALERT_TRIGGERED,
        ],
        secret="minha_chave_hmac",  # Para verificação
        enabled=True,
    ))
    
    # Disparar eventos
    await webhook_manager.dispatch(
        WebhookEvent.TRADE_OPENED,
        {
            "symbol": "XAUUSD",
            "type": "BUY",
            "volume": 0.01,
            "price": 2050.50,
            "sl": 2045.00,
            "tp": 2060.00,
        }
    )
    
    # Listener local (callback)
    def on_trade(payload):
        print(f"Trade disparado: {payload}")
    
    webhook_manager.add_listener(WebhookEvent.TRADE_OPENED, on_trade)
    
    # Listar webhooks
    webhooks = webhook_manager.list_webhooks()
    print(f"Webhooks registrados: {len(webhooks)}")
    
    # Desabilitar webhook
    webhook_manager.update("discord_alerts", enabled=False)


# ============================================================================
# 6. LOGGING ESTRUTURADO - Logs em JSON para análise
# ============================================================================

def example_logging():
    """Exemplo de uso do Logging Estruturado."""
    from src.core.structured_logging import (
        setup_structured_logging,
        log_operation,
        log_trade,
        log_error,
        LogContext,
    )
    
    # Setup inicial
    setup_structured_logging(level="INFO", log_file="brain/data/logs/app.json")
    
    # Logging básico com contexto
    log_operation(
        "analysis",
        "XAUUSD",
        "completed",
        duration_ms=150,
        indicators=["RSI", "MACD", "EMA"],
    )
    
    # Logging de trade
    log_trade(
        ticket=123456789,
        action="open",
        symbol="XAUUSD",
        volume=0.01,
        price=2050.50,
        sl=2045.00,
        tp=2060.00,
    )
    
    # Logging de erro
    try:
        raise ValueError("Erro de teste")
    except Exception as e:
        log_error(e, context={"symbol": "XAUUSD", "operation": "analysis"})
    
    # Contexto de requisição
    with LogContext(request_id="req-123", user="admin"):
        log_operation("auth", "login", "success", user="admin")


# ============================================================================
# 7. VARIÁVEIS DE AMBIENTE - Configuração segura
# ============================================================================

def example_env_config():
    """Exemplo de uso do EnvConfig."""
    from src.core.env_config import EnvConfig
    
    # Carregar configurações MT5 (de .env ou ambiente)
    mt5_config = EnvConfig.mt5()
    print(f"MT5 Login: {mt5_config['login']}")
    print(f"MT5 Server: {mt5_config['server']}")
    
    # Telegram
    telegram = EnvConfig.telegram()
    print(f"Bot Token: {telegram['bot_token'][:20]}...")
    
    # APIs
    apis = EnvConfig.apis()
    print(f"Finnhub API key presente: {bool(apis.get('finnhub_api_key'))}")


# ============================================================================
# 8. MÉTRICAS - Monitoramento de performance
# ============================================================================

async def example_metrics():
    """Exemplo de uso do sistema de Métricas."""
    from src.monitoring.metrics import metrics_collector
    
    # Registrar trade
    metrics_collector.record_trade(
        symbol="XAUUSD",
        profit=45.50,
        pips=20,
        duration_seconds=3600,
        bot_name="XAUUSD_Scalper",
    )
    
    # Registrar operação
    metrics_collector.record_operation(
        operation="analysis",
        duration_ms=150,
        success=True,
    )
    
    # Timer automático
    with metrics_collector.timer("analysis.trend"):
        # Operação cronometrada
        await asyncio.sleep(0.1)
    
    # Obter métricas
    summary = metrics_collector.get_summary()
    print(f"Total trades: {summary['trades']['total']}")
    print(f"Win rate: {summary['trades']['win_rate']}%")


# ============================================================================
# MAIN - Rodar exemplos
# ============================================================================

async def main():
    """Roda todos os exemplos."""
    print("=" * 60)
    print("EXEMPLOS DE USO DOS NOVOS MÓDULOS VIRTUS")
    print("=" * 60)
    
    print("\n1. Circuit Breaker...")
    await example_circuit_breaker()
    
    print("\n2. Rate Limiter...")
    await example_rate_limiter()
    
    print("\n3. Retry com Backoff...")
    await example_retry()
    
    print("\n4. Cache de Análises...")
    await example_cache()
    
    print("\n5. Webhooks...")
    await example_webhooks()
    
    print("\n6. Logging Estruturado...")
    example_logging()
    
    print("\n7. Variáveis de Ambiente...")
    example_env_config()
    
    print("\n8. Métricas...")
    await example_metrics()
    
    print("\n" + "=" * 60)
    print("Exemplos concluídos!")


if __name__ == "__main__":
    asyncio.run(main())
