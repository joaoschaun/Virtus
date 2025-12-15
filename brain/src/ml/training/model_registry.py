"""
VIRTUS Model Registry
=====================

Gerenciamento centralizado de modelos ML.
Versionamento, armazenamento e deploy de modelos treinados.
"""

import os
import json
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Tipos de modelo suportados."""
    DIRECTION = "direction"          # Previsão de direção
    VOLATILITY = "volatility"        # Previsão de volatilidade
    REGIME = "regime"                # Detecção de regime de mercado
    SIGNAL = "signal"                # Geração de sinais
    ENTRY = "entry"                  # Timing de entrada
    EXIT = "exit"                    # Timing de saída
    RISK = "risk"                    # Avaliação de risco
    ENSEMBLE = "ensemble"            # Modelo ensemble


class ModelStatus(Enum):
    """Status do modelo."""
    TRAINING = "training"            # Em treinamento
    VALIDATING = "validating"        # Em validação
    STAGING = "staging"              # Pronto para testes
    PRODUCTION = "production"        # Em produção
    ARCHIVED = "archived"            # Arquivado
    FAILED = "failed"                # Falhou


class ModelFramework(Enum):
    """Frameworks de ML suportados."""
    PYTORCH = "pytorch"
    SKLEARN = "sklearn"
    LIGHTGBM = "lightgbm"
    XGBOOST = "xgboost"
    CATBOOST = "catboost"
    TENSORFLOW = "tensorflow"
    CUSTOM = "custom"


@dataclass
class ModelMetrics:
    """Métricas de performance do modelo."""
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    auc_roc: float = 0.0
    sharpe_ratio: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    avg_trade_duration: float = 0.0
    custom_metrics: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelMetrics':
        return cls(**data)


@dataclass
class ModelConfig:
    """Configuração do modelo."""
    # Arquitetura
    input_features: List[str] = field(default_factory=list)
    output_classes: int = 2
    hidden_layers: List[int] = field(default_factory=lambda: [64, 32])
    
    # Hiperparâmetros
    learning_rate: float = 0.001
    batch_size: int = 32
    epochs: int = 100
    dropout: float = 0.2
    
    # Dados
    lookback_period: int = 60
    prediction_horizon: int = 1
    train_split: float = 0.7
    val_split: float = 0.15
    
    # Treinamento
    early_stopping_patience: int = 10
    reduce_lr_patience: int = 5
    min_lr: float = 1e-6
    
    # Custom
    custom_params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelConfig':
        return cls(**data)


@dataclass
class ModelVersion:
    """Versão de um modelo."""
    version: str
    model_id: str
    symbol: str
    model_type: ModelType
    framework: ModelFramework
    status: ModelStatus
    
    # Metadados
    created_at: datetime
    updated_at: datetime
    trained_by: str = "system"
    description: str = ""
    tags: List[str] = field(default_factory=list)
    
    # Caminhos
    model_path: str = ""
    weights_path: str = ""
    config_path: str = ""
    
    # Performance
    metrics: ModelMetrics = field(default_factory=ModelMetrics)
    config: ModelConfig = field(default_factory=ModelConfig)
    
    # Histórico de treinamento
    training_history: Dict[str, List[float]] = field(default_factory=dict)
    
    # Hash para verificação de integridade
    checksum: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['model_type'] = self.model_type.value
        data['framework'] = self.framework.value
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelVersion':
        data['model_type'] = ModelType(data['model_type'])
        data['framework'] = ModelFramework(data['framework'])
        data['status'] = ModelStatus(data['status'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        data['metrics'] = ModelMetrics.from_dict(data['metrics'])
        data['config'] = ModelConfig.from_dict(data['config'])
        return cls(**data)


class ModelRegistry:
    """
    Registry centralizado para modelos ML.
    
    Funcionalidades:
    - Registro e versionamento de modelos
    - Armazenamento organizado por símbolo/tipo
    - Deploy para produção
    - Rollback de versões
    - Comparação de performance
    - Limpeza de modelos antigos
    """
    
    def __init__(
        self,
        base_path: str = "models",
        metadata_file: str = "registry.json",
    ):
        """
        Inicializa o Model Registry.
        
        Args:
            base_path: Diretório base para modelos
            metadata_file: Arquivo de metadados
        """
        self.base_path = Path(base_path)
        self.metadata_file = metadata_file
        
        # Estrutura de diretórios
        self.shared_path = self.base_path / "shared"
        self.symbol_path = self.base_path / "symbol_specific"
        
        # Cache de modelos registrados
        self._models: Dict[str, ModelVersion] = {}
        
        # Modelos em produção por símbolo/tipo
        self._production_models: Dict[str, Dict[str, str]] = {}
        
        # Inicializa
        self._ensure_directories()
        self._load_registry()
        
        logger.info(f"ModelRegistry inicializado em {self.base_path}")
    
    def _ensure_directories(self) -> None:
        """Cria estrutura de diretórios."""
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.shared_path.mkdir(exist_ok=True)
        self.symbol_path.mkdir(exist_ok=True)
        
        # Diretórios por símbolo
        for symbol in ['XAUUSD', 'EURUSD', 'GBPUSD']:
            symbol_dir = self.symbol_path / symbol
            symbol_dir.mkdir(exist_ok=True)
    
    def _get_registry_path(self) -> Path:
        """Retorna caminho do arquivo de registry."""
        return self.base_path / self.metadata_file
    
    def _load_registry(self) -> None:
        """Carrega registry do disco."""
        registry_path = self._get_registry_path()
        
        if registry_path.exists():
            try:
                with open(registry_path, 'r') as f:
                    data = json.load(f)
                
                # Carrega modelos
                for model_id, model_data in data.get('models', {}).items():
                    self._models[model_id] = ModelVersion.from_dict(model_data)
                
                # Carrega modelos em produção
                self._production_models = data.get('production', {})
                
                logger.info(f"Registry carregado: {len(self._models)} modelos")
                
            except Exception as e:
                logger.error(f"Erro ao carregar registry: {e}")
    
    def _save_registry(self) -> None:
        """Salva registry para disco."""
        registry_path = self._get_registry_path()
        
        try:
            data = {
                'models': {
                    model_id: model.to_dict()
                    for model_id, model in self._models.items()
                },
                'production': self._production_models,
                'updated_at': datetime.now().isoformat(),
            }
            
            with open(registry_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug("Registry salvo")
            
        except Exception as e:
            logger.error(f"Erro ao salvar registry: {e}")
    
    def _generate_model_id(
        self,
        symbol: str,
        model_type: ModelType,
        version: str,
    ) -> str:
        """Gera ID único para modelo."""
        return f"{symbol}_{model_type.value}_{version}"
    
    def _generate_version(self) -> str:
        """Gera versão baseada em timestamp."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def _compute_checksum(self, file_path: Path) -> str:
        """Computa checksum MD5 de um arquivo."""
        if not file_path.exists():
            return ""
        
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        
        return hasher.hexdigest()
    
    # ========================================================================
    # REGISTRO DE MODELOS
    # ========================================================================
    
    def register_model(
        self,
        symbol: str,
        model_type: ModelType,
        framework: ModelFramework,
        model_path: str,
        config: Optional[ModelConfig] = None,
        metrics: Optional[ModelMetrics] = None,
        description: str = "",
        tags: Optional[List[str]] = None,
        weights_path: Optional[str] = None,
    ) -> ModelVersion:
        """
        Registra um novo modelo.
        
        Args:
            symbol: Símbolo do ativo
            model_type: Tipo do modelo
            framework: Framework usado
            model_path: Caminho do arquivo do modelo
            config: Configuração do modelo
            metrics: Métricas de performance
            description: Descrição
            tags: Tags para organização
            weights_path: Caminho dos pesos (se separado)
            
        Returns:
            ModelVersion registrada
        """
        version = self._generate_version()
        model_id = self._generate_model_id(symbol, model_type, version)
        
        # Copia modelo para diretório do registry
        dest_dir = self.symbol_path / symbol / model_type.value / version
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        # Copia arquivos
        src_path = Path(model_path)
        dest_model = dest_dir / src_path.name
        
        if src_path.exists():
            shutil.copy2(src_path, dest_model)
        
        dest_weights = ""
        if weights_path:
            weights_src = Path(weights_path)
            if weights_src.exists():
                dest_weights_path = dest_dir / weights_src.name
                shutil.copy2(weights_src, dest_weights_path)
                dest_weights = str(dest_weights_path)
        
        # Salva configuração
        config_path = dest_dir / "config.json"
        if config:
            with open(config_path, 'w') as f:
                json.dump(config.to_dict(), f, indent=2)
        
        # Cria versão
        now = datetime.now()
        model_version = ModelVersion(
            version=version,
            model_id=model_id,
            symbol=symbol,
            model_type=model_type,
            framework=framework,
            status=ModelStatus.STAGING,
            created_at=now,
            updated_at=now,
            description=description,
            tags=tags or [],
            model_path=str(dest_model),
            weights_path=dest_weights,
            config_path=str(config_path),
            metrics=metrics or ModelMetrics(),
            config=config or ModelConfig(),
            checksum=self._compute_checksum(dest_model),
        )
        
        # Registra
        self._models[model_id] = model_version
        self._save_registry()
        
        logger.info(f"Modelo registrado: {model_id}")
        
        return model_version
    
    def update_model_metrics(
        self,
        model_id: str,
        metrics: ModelMetrics,
    ) -> Optional[ModelVersion]:
        """
        Atualiza métricas de um modelo.
        
        Args:
            model_id: ID do modelo
            metrics: Novas métricas
            
        Returns:
            ModelVersion atualizada ou None
        """
        if model_id not in self._models:
            logger.warning(f"Modelo não encontrado: {model_id}")
            return None
        
        model = self._models[model_id]
        model.metrics = metrics
        model.updated_at = datetime.now()
        
        self._save_registry()
        
        logger.info(f"Métricas atualizadas: {model_id}")
        
        return model
    
    def update_model_status(
        self,
        model_id: str,
        status: ModelStatus,
    ) -> Optional[ModelVersion]:
        """
        Atualiza status de um modelo.
        
        Args:
            model_id: ID do modelo
            status: Novo status
            
        Returns:
            ModelVersion atualizada ou None
        """
        if model_id not in self._models:
            logger.warning(f"Modelo não encontrado: {model_id}")
            return None
        
        model = self._models[model_id]
        old_status = model.status
        model.status = status
        model.updated_at = datetime.now()
        
        self._save_registry()
        
        logger.info(f"Status atualizado: {model_id} ({old_status} -> {status})")
        
        return model
    
    # ========================================================================
    # QUERIES
    # ========================================================================
    
    def get_model(self, model_id: str) -> Optional[ModelVersion]:
        """Obtém modelo por ID."""
        return self._models.get(model_id)
    
    def list_models(
        self,
        symbol: Optional[str] = None,
        model_type: Optional[ModelType] = None,
        status: Optional[ModelStatus] = None,
        tags: Optional[List[str]] = None,
    ) -> List[ModelVersion]:
        """
        Lista modelos com filtros.
        
        Args:
            symbol: Filtrar por símbolo
            model_type: Filtrar por tipo
            status: Filtrar por status
            tags: Filtrar por tags
            
        Returns:
            Lista de modelos
        """
        models = list(self._models.values())
        
        if symbol:
            models = [m for m in models if m.symbol == symbol]
        
        if model_type:
            models = [m for m in models if m.model_type == model_type]
        
        if status:
            models = [m for m in models if m.status == status]
        
        if tags:
            models = [m for m in models if any(t in m.tags for t in tags)]
        
        # Ordena por data (mais recente primeiro)
        models.sort(key=lambda m: m.created_at, reverse=True)
        
        return models
    
    def get_latest_model(
        self,
        symbol: str,
        model_type: ModelType,
        status: Optional[ModelStatus] = None,
    ) -> Optional[ModelVersion]:
        """
        Obtém modelo mais recente para símbolo/tipo.
        
        Args:
            symbol: Símbolo
            model_type: Tipo do modelo
            status: Status desejado (default: qualquer)
            
        Returns:
            ModelVersion ou None
        """
        models = self.list_models(symbol=symbol, model_type=model_type, status=status)
        return models[0] if models else None
    
    def get_production_model(
        self,
        symbol: str,
        model_type: ModelType,
    ) -> Optional[ModelVersion]:
        """
        Obtém modelo em produção para símbolo/tipo.
        
        Args:
            symbol: Símbolo
            model_type: Tipo do modelo
            
        Returns:
            ModelVersion em produção ou None
        """
        symbol_production = self._production_models.get(symbol, {})
        model_id = symbol_production.get(model_type.value)
        
        if model_id:
            return self.get_model(model_id)
        
        return None
    
    # ========================================================================
    # DEPLOY E ROLLBACK
    # ========================================================================
    
    def deploy_model(
        self,
        model_id: str,
        validate_metrics: bool = True,
        min_accuracy: float = 0.6,
        min_profit_factor: float = 1.2,
    ) -> bool:
        """
        Deploy modelo para produção.
        
        Args:
            model_id: ID do modelo
            validate_metrics: Validar métricas antes do deploy
            min_accuracy: Accuracy mínima
            min_profit_factor: Profit factor mínimo
            
        Returns:
            True se deploy bem-sucedido
        """
        model = self.get_model(model_id)
        if not model:
            logger.error(f"Modelo não encontrado: {model_id}")
            return False
        
        # Valida métricas
        if validate_metrics:
            if model.metrics.accuracy < min_accuracy:
                logger.warning(
                    f"Modelo {model_id} não atende accuracy mínima: "
                    f"{model.metrics.accuracy:.2f} < {min_accuracy}"
                )
                return False
            
            if model.metrics.profit_factor < min_profit_factor:
                logger.warning(
                    f"Modelo {model_id} não atende profit factor mínimo: "
                    f"{model.metrics.profit_factor:.2f} < {min_profit_factor}"
                )
                return False
        
        # Remove modelo anterior de produção (se houver)
        current_prod = self.get_production_model(model.symbol, model.model_type)
        if current_prod and current_prod.model_id != model_id:
            self.update_model_status(current_prod.model_id, ModelStatus.ARCHIVED)
        
        # Deploy novo modelo
        if model.symbol not in self._production_models:
            self._production_models[model.symbol] = {}
        
        self._production_models[model.symbol][model.model_type.value] = model_id
        
        # Atualiza status
        self.update_model_status(model_id, ModelStatus.PRODUCTION)
        
        logger.info(f"Modelo deployed: {model_id}")
        
        return True
    
    def rollback_model(
        self,
        symbol: str,
        model_type: ModelType,
    ) -> Optional[ModelVersion]:
        """
        Rollback para versão anterior.
        
        Args:
            symbol: Símbolo
            model_type: Tipo do modelo
            
        Returns:
            Modelo anterior ou None
        """
        # Obtém modelo atual
        current = self.get_production_model(symbol, model_type)
        if not current:
            logger.warning(f"Sem modelo em produção para {symbol}/{model_type.value}")
            return None
        
        # Encontra versão anterior
        models = self.list_models(
            symbol=symbol,
            model_type=model_type,
            status=ModelStatus.ARCHIVED,
        )
        
        if not models:
            logger.warning(f"Sem versão anterior para rollback: {symbol}/{model_type.value}")
            return None
        
        # Faz rollback
        previous = models[0]
        
        # Arquiva atual
        self.update_model_status(current.model_id, ModelStatus.ARCHIVED)
        
        # Restaura anterior
        self.deploy_model(previous.model_id, validate_metrics=False)
        
        logger.info(f"Rollback: {current.model_id} -> {previous.model_id}")
        
        return previous
    
    # ========================================================================
    # COMPARAÇÃO E ANÁLISE
    # ========================================================================
    
    def compare_models(
        self,
        model_ids: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compara métricas de múltiplos modelos.
        
        Args:
            model_ids: Lista de IDs
            
        Returns:
            Dicionário com comparação
        """
        comparison = {}
        
        for model_id in model_ids:
            model = self.get_model(model_id)
            if model:
                comparison[model_id] = {
                    'version': model.version,
                    'status': model.status.value,
                    'accuracy': model.metrics.accuracy,
                    'precision': model.metrics.precision,
                    'recall': model.metrics.recall,
                    'f1_score': model.metrics.f1_score,
                    'sharpe_ratio': model.metrics.sharpe_ratio,
                    'profit_factor': model.metrics.profit_factor,
                    'max_drawdown': model.metrics.max_drawdown,
                    'win_rate': model.metrics.win_rate,
                }
        
        return comparison
    
    def get_best_model(
        self,
        symbol: str,
        model_type: ModelType,
        metric: str = "profit_factor",
    ) -> Optional[ModelVersion]:
        """
        Obtém melhor modelo por métrica.
        
        Args:
            symbol: Símbolo
            model_type: Tipo do modelo
            metric: Métrica para comparação
            
        Returns:
            Melhor modelo ou None
        """
        models = self.list_models(symbol=symbol, model_type=model_type)
        
        if not models:
            return None
        
        def get_metric_value(model: ModelVersion) -> float:
            metrics_dict = model.metrics.to_dict()
            return metrics_dict.get(metric, 0.0)
        
        # Para drawdown, menor é melhor
        if metric == 'max_drawdown':
            return min(models, key=get_metric_value)
        
        return max(models, key=get_metric_value)
    
    # ========================================================================
    # LIMPEZA
    # ========================================================================
    
    def cleanup_old_models(
        self,
        keep_versions: int = 5,
        keep_days: int = 30,
        dry_run: bool = True,
    ) -> List[str]:
        """
        Remove modelos antigos.
        
        Args:
            keep_versions: Manter últimas N versões
            keep_days: Manter modelos dos últimos N dias
            dry_run: Se True, apenas lista sem remover
            
        Returns:
            Lista de IDs removidos
        """
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        to_remove = []
        
        # Agrupa por símbolo/tipo
        groups: Dict[str, List[ModelVersion]] = {}
        
        for model in self._models.values():
            key = f"{model.symbol}_{model.model_type.value}"
            if key not in groups:
                groups[key] = []
            groups[key].append(model)
        
        # Identifica para remoção
        for key, models in groups.items():
            # Ordena por data
            models.sort(key=lambda m: m.created_at, reverse=True)
            
            for i, model in enumerate(models):
                # Nunca remove modelos em produção
                if model.status == ModelStatus.PRODUCTION:
                    continue
                
                # Mantém últimas N versões
                if i < keep_versions:
                    continue
                
                # Remove se mais antigo que cutoff
                if model.created_at < cutoff_date:
                    to_remove.append(model.model_id)
        
        if not dry_run:
            for model_id in to_remove:
                self._delete_model(model_id)
            
            logger.info(f"Limpeza: {len(to_remove)} modelos removidos")
        else:
            logger.info(f"Limpeza (dry run): {len(to_remove)} modelos identificados")
        
        return to_remove
    
    def _delete_model(self, model_id: str) -> bool:
        """Remove modelo completamente."""
        model = self.get_model(model_id)
        if not model:
            return False
        
        # Não remove modelos em produção
        if model.status == ModelStatus.PRODUCTION:
            logger.warning(f"Não é possível remover modelo em produção: {model_id}")
            return False
        
        # Remove arquivos
        model_path = Path(model.model_path)
        if model_path.exists():
            model_dir = model_path.parent
            shutil.rmtree(model_dir, ignore_errors=True)
        
        # Remove do registry
        del self._models[model_id]
        self._save_registry()
        
        logger.info(f"Modelo removido: {model_id}")
        
        return True
    
    # ========================================================================
    # ESTATÍSTICAS
    # ========================================================================
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do registry."""
        stats = {
            'total_models': len(self._models),
            'by_symbol': {},
            'by_type': {},
            'by_status': {},
            'by_framework': {},
            'production_models': sum(
                len(types) for types in self._production_models.values()
            ),
        }
        
        for model in self._models.values():
            # Por símbolo
            stats['by_symbol'][model.symbol] = \
                stats['by_symbol'].get(model.symbol, 0) + 1
            
            # Por tipo
            stats['by_type'][model.model_type.value] = \
                stats['by_type'].get(model.model_type.value, 0) + 1
            
            # Por status
            stats['by_status'][model.status.value] = \
                stats['by_status'].get(model.status.value, 0) + 1
            
            # Por framework
            stats['by_framework'][model.framework.value] = \
                stats['by_framework'].get(model.framework.value, 0) + 1
        
        return stats
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa registry para dicionário."""
        return {
            'base_path': str(self.base_path),
            'total_models': len(self._models),
            'production_models': self._production_models,
            'stats': self.get_registry_stats(),
        }
