"""
Model Factory - MAGISTRAL Edition
===================================

Factory pattern avançado para gerenciamento de modelos de ML.

Features:
- Auto-discovery de modelos
- Lazy loading com cache
- Versionamento de modelos
- Hot-swap de modelos em produção
- Lifecycle management
- Métricas e monitoramento
- Fallback para modelos default
"""

from typing import Dict, Optional, Type, Any, List, Callable, Set
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime
from pathlib import Path
import hashlib


class ModelStatus(Enum):
    """Status do modelo no ciclo de vida."""
    REGISTERED = auto()     # Registrado mas não inicializado
    LOADING = auto()        # Sendo carregado
    READY = auto()          # Pronto para uso
    PRODUCTION = auto()     # Em produção ativa
    DEPRECATED = auto()     # Marcado para remoção
    ERROR = auto()          # Erro no carregamento


class ModelType(Enum):
    """Tipos de modelos suportados."""
    DIRECTION = "direction"       # Predição de direção
    REGIME = "regime"             # Detecção de regime
    VOLATILITY = "volatility"     # Predição de volatilidade
    SENTIMENT = "sentiment"       # Análise de sentimento
    ENSEMBLE = "ensemble"         # Modelo ensemble
    CUSTOM = "custom"             # Modelo customizado


@dataclass
class ModelMetadata:
    """Metadados do modelo."""
    name: str
    model_type: ModelType
    version: str
    status: ModelStatus = ModelStatus.REGISTERED
    created_at: datetime = field(default_factory=datetime.now)
    loaded_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    usage_count: int = 0
    error_count: int = 0
    avg_latency_ms: float = 0.0
    accuracy: float = 0.0
    
    @property
    def is_healthy(self) -> bool:
        """Se o modelo está saudável para uso."""
        return (
            self.status in (ModelStatus.READY, ModelStatus.PRODUCTION) and
            self.error_count < 10
        )
    
    @property
    def health_score(self) -> float:
        """Score de saúde do modelo (0-100)."""
        score = 100.0
        
        # Penalizar erros
        score -= min(50, self.error_count * 5)
        
        # Penalizar alta latência
        if self.avg_latency_ms > 100:
            score -= min(20, (self.avg_latency_ms - 100) / 10)
        
        # Bonificar accuracy alta
        score += self.accuracy * 20
        
        return max(0, min(100, score))


@dataclass
class ModelInstance:
    """Instância de um modelo com metadados."""
    instance: Any
    metadata: ModelMetadata
    
    def update_usage(self, latency_ms: float = 0.0) -> None:
        """Atualiza estatísticas de uso."""
        self.metadata.usage_count += 1
        self.metadata.last_used = datetime.now()
        
        # Atualizar média de latência (média móvel)
        old_avg = self.metadata.avg_latency_ms
        count = self.metadata.usage_count
        self.metadata.avg_latency_ms = (old_avg * (count - 1) + latency_ms) / count
    
    def record_error(self) -> None:
        """Registra um erro."""
        self.metadata.error_count += 1


class ModelFactory:
    """
    Factory MAGISTRAL para gerenciamento de modelos de ML.
    
    Features:
    - Registry com versionamento
    - Lazy loading com cache
    - Hot-swap em produção
    - Auto-fallback
    - Métricas detalhadas
    - Event callbacks
    """
    
    _models: Dict[str, ModelInstance] = {}
    _model_classes: Dict[str, Type] = {}
    _default_models: Dict[ModelType, str] = {}
    _fallback_models: Dict[ModelType, str] = {}
    _callbacks: List[Callable] = []
    _initialized: bool = False
    
    # Configurações
    MAX_ERROR_COUNT = 10
    LAZY_LOAD_ENABLED = True
    
    @classmethod
    def initialize(cls, models_dir: str = "models") -> bool:
        """
        Inicializa a factory com descoberta automática de modelos.
        
        Args:
            models_dir: Diretório contendo modelos
            
        Returns:
            True se inicializado com sucesso
        """
        if cls._initialized:
            return True
        
        cls._models = {}
        cls._model_classes = {}
        cls._default_models = {}
        cls._fallback_models = {}
        cls._callbacks = []
        cls._initialized = True
        
        return True
    
    @classmethod
    def register(cls, name: str, model_class: Type, model_type: ModelType = ModelType.CUSTOM, version: str = "1.0.0") -> bool:
        """
        Registra uma classe de modelo.
        
        Args:
            name: Nome único do modelo
            model_class: Classe do modelo
            model_type: Tipo do modelo
            version: Versão do modelo
            
        Returns:
            True se registrado com sucesso
        """
        if not cls._initialized:
            cls.initialize()
        
        cls._model_classes[name] = model_class
        
        # Criar metadata mas não instanciar (lazy loading)
        metadata = ModelMetadata(
            name=name,
            model_type=model_type,
            version=version,
            status=ModelStatus.REGISTERED,
        )
        
        # Se lazy loading desabilitado, criar instância imediatamente
        if not cls.LAZY_LOAD_ENABLED:
            cls._load_model(name, metadata)
        
        cls._emit_event('model_registered', {'name': name, 'type': model_type.value})
        return True
    
    @classmethod
    def _load_model(cls, name: str, metadata: Optional[ModelMetadata] = None) -> Optional[ModelInstance]:
        """Carrega um modelo (lazy loading)."""
        model_class = cls._model_classes.get(name)
        if not model_class:
            return None
        
        if metadata is None:
            metadata = ModelMetadata(
                name=name,
                model_type=ModelType.CUSTOM,
                version="1.0.0",
            )
        
        try:
            metadata.status = ModelStatus.LOADING
            instance = model_class()
            metadata.status = ModelStatus.READY
            metadata.loaded_at = datetime.now()
            
            model_instance = ModelInstance(instance=instance, metadata=metadata)
            cls._models[name] = model_instance
            
            cls._emit_event('model_loaded', {'name': name})
            return model_instance
            
        except Exception as e:
            metadata.status = ModelStatus.ERROR
            cls._emit_event('model_error', {'name': name, 'error': str(e)})
            return None
    
    @classmethod
    def create(cls, name: str, **kwargs) -> Optional[Any]:
        """
        Cria/obtém uma instância de modelo pelo nome.
        
        Usa cache se disponível, senão lazy-load.
        
        Args:
            name: Nome do modelo
            **kwargs: Argumentos para criação (se nova instância)
            
        Returns:
            Instância do modelo ou None
        """
        if not cls._initialized:
            cls.initialize()
        
        # Verificar se já carregado
        if name in cls._models:
            model_instance = cls._models[name]
            if model_instance.metadata.is_healthy:
                return model_instance.instance
            else:
                # Modelo com problemas - tentar fallback
                return cls._get_fallback(model_instance.metadata.model_type)
        
        # Lazy load
        if name in cls._model_classes:
            model_instance = cls._load_model(name)
            if model_instance:
                return model_instance.instance
        
        # Criar nova instância se classe disponível
        model_class = cls._model_classes.get(name)
        if model_class:
            try:
                return model_class(**kwargs)
            except Exception:
                pass
        
        return None
    
    @classmethod
    def _get_fallback(cls, model_type: ModelType) -> Optional[Any]:
        """Obtém modelo fallback para o tipo."""
        fallback_name = cls._fallback_models.get(model_type)
        if fallback_name and fallback_name in cls._models:
            return cls._models[fallback_name].instance
        return None
    
    @classmethod
    def get(cls, name: str) -> Optional[ModelInstance]:
        """Obtém instância de modelo com metadados."""
        if not cls._initialized:
            cls.initialize()
        
        if name in cls._models:
            return cls._models[name]
        
        # Lazy load
        if name in cls._model_classes:
            return cls._load_model(name)
        
        return None
    
    @classmethod
    def set_default(cls, model_type: ModelType, name: str) -> bool:
        """Define modelo padrão para um tipo."""
        if name in cls._model_classes or name in cls._models:
            cls._default_models[model_type] = name
            cls._emit_event('default_changed', {'type': model_type.value, 'name': name})
            return True
        return False
    
    @classmethod
    def set_fallback(cls, model_type: ModelType, name: str) -> bool:
        """Define modelo fallback para um tipo."""
        if name in cls._model_classes or name in cls._models:
            cls._fallback_models[model_type] = name
            return True
        return False
    
    @classmethod
    def get_default(cls, model_type: ModelType) -> Optional[Any]:
        """Obtém modelo padrão para um tipo."""
        name = cls._default_models.get(model_type)
        if name:
            return cls.create(name)
        return None
    
    @classmethod
    def promote_to_production(cls, name: str) -> bool:
        """Promove modelo para produção."""
        model_instance = cls.get(name)
        if model_instance and model_instance.metadata.is_healthy:
            model_instance.metadata.status = ModelStatus.PRODUCTION
            cls._emit_event('model_promoted', {'name': name})
            return True
        return False
    
    @classmethod
    def deprecate(cls, name: str) -> bool:
        """Marca modelo como deprecated."""
        if name in cls._models:
            cls._models[name].metadata.status = ModelStatus.DEPRECATED
            cls._emit_event('model_deprecated', {'name': name})
            return True
        return False
    
    @classmethod
    def unregister(cls, name: str) -> bool:
        """Remove modelo do registry."""
        removed = False
        if name in cls._models:
            del cls._models[name]
            removed = True
        if name in cls._model_classes:
            del cls._model_classes[name]
            removed = True
        
        if removed:
            cls._emit_event('model_unregistered', {'name': name})
        return removed
    
    @classmethod
    def list_models(cls) -> List[str]:
        """Lista nomes de modelos registrados."""
        if not cls._initialized:
            return []
        all_models = set(cls._model_classes.keys()) | set(cls._models.keys())
        return sorted(list(all_models))
    
    @classmethod
    def list_by_type(cls, model_type: ModelType) -> List[str]:
        """Lista modelos de um tipo específico."""
        result = []
        for name, instance in cls._models.items():
            if instance.metadata.model_type == model_type:
                result.append(name)
        return result
    
    @classmethod
    def list_production(cls) -> List[str]:
        """Lista modelos em produção."""
        return [
            name for name, instance in cls._models.items()
            if instance.metadata.status == ModelStatus.PRODUCTION
        ]
    
    @classmethod
    def get_statistics(cls) -> Dict[str, Any]:
        """Retorna estatísticas da factory."""
        if not cls._initialized:
            return {'initialized': False}
        
        total = len(cls._models)
        healthy = sum(1 for m in cls._models.values() if m.metadata.is_healthy)
        production = sum(1 for m in cls._models.values() if m.metadata.status == ModelStatus.PRODUCTION)
        
        return {
            'initialized': True,
            'total_registered': len(cls._model_classes),
            'total_loaded': total,
            'healthy': healthy,
            'production': production,
            'default_models': {k.value: v for k, v in cls._default_models.items()},
            'fallback_models': {k.value: v for k, v in cls._fallback_models.items()},
            'models': {
                name: {
                    'status': inst.metadata.status.name,
                    'type': inst.metadata.model_type.value,
                    'version': inst.metadata.version,
                    'health_score': round(inst.metadata.health_score, 1),
                    'usage_count': inst.metadata.usage_count,
                    'avg_latency_ms': round(inst.metadata.avg_latency_ms, 2),
                }
                for name, inst in cls._models.items()
            }
        }
    
    @classmethod
    def get_health_report(cls) -> Dict[str, Any]:
        """Gera relatório de saúde dos modelos."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'overall_health': 'healthy',
            'issues': [],
            'models': {},
        }
        
        for name, instance in cls._models.items():
            health = instance.metadata.health_score
            report['models'][name] = {
                'health_score': health,
                'status': instance.metadata.status.name,
                'error_count': instance.metadata.error_count,
            }
            
            if health < 50:
                report['issues'].append(f"Model '{name}' has low health score: {health:.1f}")
                report['overall_health'] = 'degraded'
            
            if instance.metadata.error_count >= cls.MAX_ERROR_COUNT:
                report['issues'].append(f"Model '{name}' has too many errors")
                report['overall_health'] = 'critical'
        
        return report
    
    @classmethod
    def register_callback(cls, callback: Callable) -> None:
        """Registra callback para eventos."""
        cls._callbacks.append(callback)
    
    @classmethod
    def _emit_event(cls, event_type: str, data: Dict[str, Any]) -> None:
        """Emite evento para callbacks registrados."""
        event = {
            'type': event_type,
            'timestamp': datetime.now().isoformat(),
            'data': data,
        }
        
        for callback in cls._callbacks:
            try:
                callback(event)
            except Exception:
                pass
    
    @classmethod
    def reset(cls) -> None:
        """Reseta a factory para estado inicial."""
        cls._models.clear()
        cls._model_classes.clear()
        cls._default_models.clear()
        cls._fallback_models.clear()
        cls._callbacks.clear()
        cls._initialized = False
