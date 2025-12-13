"""
BRAIN - Redis Cache
Cache distribuído com Redis
"""

from typing import Any, Dict, Optional
import json
import pickle

from ...core.logger import get_logger
from ...core.config import Config

logger = get_logger("brain.cache")


class RedisCache:
    """
    Cache com Redis
    
    Características:
    - Distribuído (múltiplas instâncias podem compartilhar)
    - Persistente
    - TTL nativo
    """
    
    def __init__(self):
        self._config = Config()
        self._redis = None
        self._connected = False
        
        redis_config = self._config.get("redis", {})
        
        if redis_config.get("enabled", False):
            self._connect(redis_config)
    
    def _connect(self, config: Dict[str, Any]):
        """Conecta ao Redis"""
        try:
            import redis
            
            self._redis = redis.Redis(
                host=config.get("host", "localhost"),
                port=config.get("port", 6379),
                db=config.get("db", 0),
                password=config.get("password"),
                decode_responses=False
            )
            
            # Testar conexão
            self._redis.ping()
            self._connected = True
            logger.info("🔴 Redis conectado")
            
        except ImportError:
            logger.warning("⚠️ Pacote redis não instalado")
            self._connected = False
        except Exception as e:
            logger.warning(f"⚠️ Não foi possível conectar ao Redis: {e}")
            self._connected = False
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    def get(self, key: str) -> Optional[Any]:
        """Obtém valor do cache"""
        if not self._connected:
            return None
        
        try:
            data = self._redis.get(f"brain:{key}")
            if data:
                return pickle.loads(data)
            return None
        except Exception as e:
            logger.error(f"Erro ao ler do Redis: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Armazena valor no cache"""
        if not self._connected:
            return False
        
        try:
            data = pickle.dumps(value)
            self._redis.setex(f"brain:{key}", ttl, data)
            return True
        except Exception as e:
            logger.error(f"Erro ao escrever no Redis: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Remove entrada do cache"""
        if not self._connected:
            return False
        
        try:
            self._redis.delete(f"brain:{key}")
            return True
        except Exception as e:
            logger.error(f"Erro ao deletar do Redis: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Verifica se chave existe"""
        if not self._connected:
            return False
        
        try:
            return self._redis.exists(f"brain:{key}") > 0
        except Exception:
            return False
    
    def clear(self, pattern: str = "*"):
        """Limpa cache (por padrão)"""
        if not self._connected:
            return
        
        try:
            keys = self._redis.keys(f"brain:{pattern}")
            if keys:
                self._redis.delete(*keys)
                logger.info(f"🗑️ {len(keys)} chaves removidas do Redis")
        except Exception as e:
            logger.error(f"Erro ao limpar Redis: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas"""
        if not self._connected:
            return {"type": "redis", "connected": False}
        
        try:
            info = self._redis.info()
            keys = self._redis.keys("brain:*")
            
            return {
                "type": "redis",
                "connected": True,
                "keys_count": len(keys),
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "uptime_days": info.get("uptime_in_days", 0)
            }
        except Exception as e:
            return {"type": "redis", "connected": True, "error": str(e)}
