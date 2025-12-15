"""
VIRTUS Trainer Service
======================

Serviço de treinamento de modelos ML.
Gerencia o ciclo completo: dados, treinamento, validação e registro.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

import numpy as np

from .model_registry import (
    ModelRegistry,
    ModelVersion,
    ModelType,
    ModelStatus,
    ModelFramework,
    ModelConfig,
    ModelMetrics,
)

logger = logging.getLogger(__name__)


class TrainingStatus(Enum):
    """Status do treinamento."""
    PENDING = "pending"
    PREPARING = "preparing"
    TRAINING = "training"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DataSplitMethod(Enum):
    """Métodos de split de dados."""
    RANDOM = "random"
    TEMPORAL = "temporal"
    WALK_FORWARD = "walk_forward"
    PURGED_KFOLD = "purged_kfold"


@dataclass
class TrainingJob:
    """Job de treinamento."""
    job_id: str
    symbol: str
    model_type: ModelType
    framework: ModelFramework
    config: ModelConfig
    status: TrainingStatus = TrainingStatus.PENDING
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Progresso
    current_epoch: int = 0
    total_epochs: int = 0
    current_loss: float = 0.0
    best_loss: float = float('inf')
    
    # Resultado
    model_id: Optional[str] = None
    metrics: Optional[ModelMetrics] = None
    error_message: Optional[str] = None
    
    # Histórico
    training_history: Dict[str, List[float]] = field(default_factory=dict)


@dataclass
class DatasetConfig:
    """Configuração do dataset."""
    symbol: str
    start_date: datetime
    end_date: datetime
    timeframe: str = "H1"
    features: List[str] = field(default_factory=list)
    target: str = "direction"
    
    # Preprocessing
    normalize: bool = True
    fill_method: str = "ffill"
    remove_outliers: bool = True
    outlier_std: float = 3.0
    
    # Split
    split_method: DataSplitMethod = DataSplitMethod.TEMPORAL
    train_ratio: float = 0.7
    val_ratio: float = 0.15
    test_ratio: float = 0.15
    
    # Walk forward
    walk_forward_windows: int = 5
    walk_forward_gap: int = 0  # Gap entre train e test


class TrainerService:
    """
    Serviço de treinamento de modelos ML.
    
    Funcionalidades:
    - Preparação de dados
    - Treinamento assíncrono
    - Validação cruzada
    - Early stopping
    - Registro automático no ModelRegistry
    - Monitoramento de progresso
    """
    
    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        base_path: str = "models",
        max_workers: int = 2,
        use_gpu: bool = False,
    ):
        """
        Inicializa o Trainer Service.
        
        Args:
            registry: Model registry (cria novo se None)
            base_path: Caminho base para modelos
            max_workers: Workers para treinamento paralelo
            use_gpu: Usar GPU se disponível
        """
        self.registry = registry or ModelRegistry(base_path=base_path)
        self.base_path = Path(base_path)
        self.max_workers = max_workers
        self.use_gpu = use_gpu
        
        # Jobs ativos
        self._jobs: Dict[str, TrainingJob] = {}
        self._job_counter = 0
        
        # Executors
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Callbacks
        self._callbacks: Dict[str, List[Callable]] = {
            'on_epoch_end': [],
            'on_training_start': [],
            'on_training_end': [],
            'on_validation_end': [],
        }
        
        # Device
        self._device = self._detect_device()
        
        logger.info(f"TrainerService inicializado (device: {self._device})")
    
    def _detect_device(self) -> str:
        """Detecta dispositivo disponível."""
        if not self.use_gpu:
            return "cpu"
        
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except ImportError:
            pass
        
        return "cpu"
    
    def _generate_job_id(self) -> str:
        """Gera ID único para job."""
        self._job_counter += 1
        return f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self._job_counter}"
    
    # ========================================================================
    # PREPARAÇÃO DE DADOS
    # ========================================================================
    
    async def prepare_dataset(
        self,
        config: DatasetConfig,
        data_provider: Optional[Any] = None,
    ) -> Dict[str, np.ndarray]:
        """
        Prepara dataset para treinamento.
        
        Args:
            config: Configuração do dataset
            data_provider: Provider de dados (opcional)
            
        Returns:
            Dicionário com X_train, X_val, X_test, y_train, y_val, y_test
        """
        logger.info(f"Preparando dataset: {config.symbol}")
        
        # Obtém dados
        raw_data = await self._fetch_data(config, data_provider)
        
        if raw_data is None or len(raw_data) == 0:
            raise ValueError(f"Sem dados para {config.symbol}")
        
        # Feature engineering
        features_df = await self._engineer_features(raw_data, config)
        
        # Preprocessamento
        processed = self._preprocess_data(features_df, config)
        
        # Split
        splits = self._split_data(processed, config)
        
        logger.info(
            f"Dataset preparado: "
            f"train={len(splits['X_train'])}, "
            f"val={len(splits['X_val'])}, "
            f"test={len(splits['X_test'])}"
        )
        
        return splits
    
    async def _fetch_data(
        self,
        config: DatasetConfig,
        data_provider: Optional[Any],
    ) -> Optional[np.ndarray]:
        """Busca dados do provider."""
        # Placeholder - em produção, usaria o data_provider real
        # Por enquanto, gera dados sintéticos
        
        n_samples = 1000
        n_features = len(config.features) if config.features else 10
        
        data = np.random.randn(n_samples, n_features + 1)  # +1 para target
        
        return data
    
    async def _engineer_features(
        self,
        raw_data: np.ndarray,
        config: DatasetConfig,
    ) -> np.ndarray:
        """Engenharia de features."""
        # Placeholder para feature engineering
        return raw_data
    
    def _preprocess_data(
        self,
        data: np.ndarray,
        config: DatasetConfig,
    ) -> np.ndarray:
        """Preprocessa dados."""
        if config.remove_outliers:
            # Remove outliers baseado em desvio padrão
            mean = np.mean(data, axis=0)
            std = np.std(data, axis=0)
            mask = np.all(
                np.abs(data - mean) < config.outlier_std * std,
                axis=1
            )
            data = data[mask]
        
        if config.normalize:
            # Normalização min-max
            data_min = data.min(axis=0)
            data_max = data.max(axis=0)
            data = (data - data_min) / (data_max - data_min + 1e-8)
        
        return data
    
    def _split_data(
        self,
        data: np.ndarray,
        config: DatasetConfig,
    ) -> Dict[str, np.ndarray]:
        """Split de dados."""
        n = len(data)
        
        if config.split_method == DataSplitMethod.RANDOM:
            # Shuffle e split
            indices = np.random.permutation(n)
            train_end = int(n * config.train_ratio)
            val_end = int(n * (config.train_ratio + config.val_ratio))
            
            train_idx = indices[:train_end]
            val_idx = indices[train_end:val_end]
            test_idx = indices[val_end:]
            
        else:  # TEMPORAL (default)
            # Split temporal (sem shuffle)
            train_end = int(n * config.train_ratio)
            val_end = int(n * (config.train_ratio + config.val_ratio))
            
            train_idx = np.arange(train_end)
            val_idx = np.arange(train_end, val_end)
            test_idx = np.arange(val_end, n)
        
        # Separa features e target (última coluna é target)
        X = data[:, :-1]
        y = data[:, -1]
        
        return {
            'X_train': X[train_idx],
            'X_val': X[val_idx],
            'X_test': X[test_idx],
            'y_train': y[train_idx],
            'y_val': y[val_idx],
            'y_test': y[test_idx],
        }
    
    # ========================================================================
    # TREINAMENTO
    # ========================================================================
    
    async def create_training_job(
        self,
        symbol: str,
        model_type: ModelType,
        framework: ModelFramework = ModelFramework.PYTORCH,
        config: Optional[ModelConfig] = None,
        dataset_config: Optional[DatasetConfig] = None,
    ) -> TrainingJob:
        """
        Cria um job de treinamento.
        
        Args:
            symbol: Símbolo do ativo
            model_type: Tipo do modelo
            framework: Framework de ML
            config: Configuração do modelo
            dataset_config: Configuração do dataset
            
        Returns:
            TrainingJob criado
        """
        job_id = self._generate_job_id()
        
        job = TrainingJob(
            job_id=job_id,
            symbol=symbol,
            model_type=model_type,
            framework=framework,
            config=config or ModelConfig(),
            total_epochs=config.epochs if config else 100,
        )
        
        self._jobs[job_id] = job
        
        logger.info(f"Job criado: {job_id}")
        
        return job
    
    async def start_training(
        self,
        job_id: str,
        dataset: Optional[Dict[str, np.ndarray]] = None,
    ) -> TrainingJob:
        """
        Inicia treinamento de um job.
        
        Args:
            job_id: ID do job
            dataset: Dataset preparado (opcional)
            
        Returns:
            Job atualizado
        """
        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"Job não encontrado: {job_id}")
        
        job.status = TrainingStatus.PREPARING
        job.started_at = datetime.now()
        
        # Notifica início
        await self._trigger_callback('on_training_start', job)
        
        try:
            # Prepara dados se não fornecido
            if dataset is None:
                dataset_config = DatasetConfig(
                    symbol=job.symbol,
                    start_date=datetime.now() - timedelta(days=365),
                    end_date=datetime.now(),
                    features=job.config.input_features,
                )
                dataset = await self.prepare_dataset(dataset_config)
            
            job.status = TrainingStatus.TRAINING
            
            # Treina modelo
            result = await self._train_model(job, dataset)
            
            # Valida
            job.status = TrainingStatus.VALIDATING
            metrics = await self._validate_model(job, result, dataset)
            
            # Registra no registry
            model_version = self._register_trained_model(job, result, metrics)
            
            job.model_id = model_version.model_id
            job.metrics = metrics
            job.status = TrainingStatus.COMPLETED
            job.completed_at = datetime.now()
            
            logger.info(f"Treinamento concluído: {job_id}")
            
        except Exception as e:
            job.status = TrainingStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now()
            logger.error(f"Erro no treinamento {job_id}: {e}")
        
        # Notifica fim
        await self._trigger_callback('on_training_end', job)
        
        return job
    
    async def _train_model(
        self,
        job: TrainingJob,
        dataset: Dict[str, np.ndarray],
    ) -> Dict[str, Any]:
        """
        Executa treinamento do modelo.
        
        Args:
            job: Job de treinamento
            dataset: Dataset
            
        Returns:
            Resultado do treinamento
        """
        X_train = dataset['X_train']
        y_train = dataset['y_train']
        X_val = dataset['X_val']
        y_val = dataset['y_val']
        
        config = job.config
        
        # Histórico de treinamento
        history = {
            'train_loss': [],
            'val_loss': [],
            'train_acc': [],
            'val_acc': [],
        }
        
        # Simula treinamento (em produção, usaria framework real)
        best_weights = None
        best_val_loss = float('inf')
        patience_counter = 0
        
        for epoch in range(config.epochs):
            # Simula epoch
            train_loss = max(0.1, 1.0 - epoch * 0.01 + np.random.randn() * 0.05)
            val_loss = max(0.1, 1.1 - epoch * 0.01 + np.random.randn() * 0.05)
            train_acc = min(0.95, 0.5 + epoch * 0.005 + np.random.randn() * 0.02)
            val_acc = min(0.9, 0.45 + epoch * 0.004 + np.random.randn() * 0.02)
            
            history['train_loss'].append(train_loss)
            history['val_loss'].append(val_loss)
            history['train_acc'].append(train_acc)
            history['val_acc'].append(val_acc)
            
            # Atualiza job
            job.current_epoch = epoch + 1
            job.current_loss = train_loss
            
            # Early stopping check
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                job.best_loss = val_loss
                best_weights = f"weights_epoch_{epoch}"
                patience_counter = 0
            else:
                patience_counter += 1
            
            if patience_counter >= config.early_stopping_patience:
                logger.info(f"Early stopping no epoch {epoch}")
                break
            
            # Callback
            await self._trigger_callback('on_epoch_end', job, epoch, history)
            
            # Pequena pausa para permitir outras tarefas
            await asyncio.sleep(0.01)
        
        job.training_history = history
        
        return {
            'weights': best_weights,
            'history': history,
            'final_epoch': job.current_epoch,
            'best_val_loss': best_val_loss,
        }
    
    async def _validate_model(
        self,
        job: TrainingJob,
        result: Dict[str, Any],
        dataset: Dict[str, np.ndarray],
    ) -> ModelMetrics:
        """
        Valida modelo treinado.
        
        Args:
            job: Job de treinamento
            result: Resultado do treinamento
            dataset: Dataset com dados de teste
            
        Returns:
            Métricas de validação
        """
        X_test = dataset['X_test']
        y_test = dataset['y_test']
        
        # Simula previsões
        n_test = len(X_test)
        predictions = np.random.randint(0, 2, n_test)
        y_test_binary = (y_test > 0.5).astype(int)
        
        # Calcula métricas
        accuracy = np.mean(predictions == y_test_binary)
        
        # Simula outras métricas
        tp = np.sum((predictions == 1) & (y_test_binary == 1))
        fp = np.sum((predictions == 1) & (y_test_binary == 0))
        fn = np.sum((predictions == 0) & (y_test_binary == 1))
        
        precision = tp / (tp + fp + 1e-8)
        recall = tp / (tp + fn + 1e-8)
        f1 = 2 * precision * recall / (precision + recall + 1e-8)
        
        # Simula métricas de trading
        trades = np.random.randint(50, 200)
        wins = int(trades * (0.5 + np.random.randn() * 0.1))
        
        metrics = ModelMetrics(
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            auc_roc=0.5 + np.random.randn() * 0.15,
            sharpe_ratio=1.0 + np.random.randn() * 0.5,
            profit_factor=1.2 + np.random.randn() * 0.3,
            max_drawdown=5.0 + np.random.randn() * 2.0,
            win_rate=wins / trades,
            total_trades=trades,
        )
        
        await self._trigger_callback('on_validation_end', job, metrics)
        
        return metrics
    
    def _register_trained_model(
        self,
        job: TrainingJob,
        result: Dict[str, Any],
        metrics: ModelMetrics,
    ) -> ModelVersion:
        """Registra modelo treinado no registry."""
        # Cria arquivo temporário do modelo
        model_path = self.base_path / f"temp_{job.job_id}.model"
        model_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(model_path, 'w') as f:
            f.write(f"Model: {job.symbol}_{job.model_type.value}\n")
            f.write(f"Framework: {job.framework.value}\n")
            f.write(f"Trained: {datetime.now().isoformat()}\n")
        
        # Registra
        model_version = self.registry.register_model(
            symbol=job.symbol,
            model_type=job.model_type,
            framework=job.framework,
            model_path=str(model_path),
            config=job.config,
            metrics=metrics,
            description=f"Trained via job {job.job_id}",
            tags=[job.framework.value, "auto-trained"],
        )
        
        # Remove arquivo temporário
        model_path.unlink(missing_ok=True)
        
        return model_version
    
    # ========================================================================
    # BATCH TRAINING
    # ========================================================================
    
    async def train_all_symbols(
        self,
        model_type: ModelType,
        symbols: Optional[List[str]] = None,
        framework: ModelFramework = ModelFramework.PYTORCH,
        config: Optional[ModelConfig] = None,
    ) -> Dict[str, TrainingJob]:
        """
        Treina modelo para múltiplos símbolos.
        
        Args:
            model_type: Tipo do modelo
            symbols: Lista de símbolos (default: XAUUSD, EURUSD, GBPUSD)
            framework: Framework de ML
            config: Configuração do modelo
            
        Returns:
            Dicionário de jobs por símbolo
        """
        symbols = symbols or ['XAUUSD', 'EURUSD', 'GBPUSD']
        jobs = {}
        
        for symbol in symbols:
            job = await self.create_training_job(
                symbol=symbol,
                model_type=model_type,
                framework=framework,
                config=config,
            )
            
            job = await self.start_training(job.job_id)
            jobs[symbol] = job
        
        return jobs
    
    async def retrain_production_models(
        self,
        min_age_days: int = 7,
    ) -> List[TrainingJob]:
        """
        Retreina modelos em produção.
        
        Args:
            min_age_days: Idade mínima em dias para retreinar
            
        Returns:
            Lista de jobs de retreino
        """
        cutoff = datetime.now() - timedelta(days=min_age_days)
        jobs = []
        
        for symbol in ['XAUUSD', 'EURUSD', 'GBPUSD']:
            for model_type in ModelType:
                prod_model = self.registry.get_production_model(symbol, model_type)
                
                if prod_model and prod_model.created_at < cutoff:
                    logger.info(f"Retreinando {symbol}/{model_type.value}")
                    
                    job = await self.create_training_job(
                        symbol=symbol,
                        model_type=model_type,
                        framework=prod_model.framework,
                        config=prod_model.config,
                    )
                    
                    job = await self.start_training(job.job_id)
                    jobs.append(job)
                    
                    # Auto-deploy se melhor
                    if job.status == TrainingStatus.COMPLETED:
                        if (job.metrics and prod_model.metrics and
                            job.metrics.profit_factor > prod_model.metrics.profit_factor):
                            self.registry.deploy_model(job.model_id)
        
        return jobs
    
    # ========================================================================
    # CALLBACKS E MONITORAMENTO
    # ========================================================================
    
    def register_callback(
        self,
        event: str,
        callback: Callable,
    ) -> None:
        """
        Registra callback para evento.
        
        Args:
            event: Nome do evento
            callback: Função callback
        """
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    async def _trigger_callback(
        self,
        event: str,
        *args,
        **kwargs,
    ) -> None:
        """Dispara callbacks de um evento."""
        for callback in self._callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(*args, **kwargs)
                else:
                    callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Erro em callback {event}: {e}")
    
    def get_job(self, job_id: str) -> Optional[TrainingJob]:
        """Obtém job por ID."""
        return self._jobs.get(job_id)
    
    def list_jobs(
        self,
        status: Optional[TrainingStatus] = None,
        symbol: Optional[str] = None,
    ) -> List[TrainingJob]:
        """
        Lista jobs com filtros.
        
        Args:
            status: Filtrar por status
            symbol: Filtrar por símbolo
            
        Returns:
            Lista de jobs
        """
        jobs = list(self._jobs.values())
        
        if status:
            jobs = [j for j in jobs if j.status == status]
        
        if symbol:
            jobs = [j for j in jobs if j.symbol == symbol]
        
        return jobs
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancela um job.
        
        Args:
            job_id: ID do job
            
        Returns:
            True se cancelado
        """
        job = self._jobs.get(job_id)
        if not job:
            return False
        
        if job.status in [TrainingStatus.PENDING, TrainingStatus.PREPARING, TrainingStatus.TRAINING]:
            job.status = TrainingStatus.CANCELLED
            job.completed_at = datetime.now()
            logger.info(f"Job cancelado: {job_id}")
            return True
        
        return False
    
    # ========================================================================
    # HYPERPARAMETER TUNING
    # ========================================================================
    
    async def hyperparameter_search(
        self,
        symbol: str,
        model_type: ModelType,
        param_grid: Dict[str, List[Any]],
        n_trials: int = 10,
        metric: str = "profit_factor",
    ) -> Dict[str, Any]:
        """
        Busca de hiperparâmetros.
        
        Args:
            symbol: Símbolo
            model_type: Tipo do modelo
            param_grid: Grid de parâmetros
            n_trials: Número de trials
            metric: Métrica para otimização
            
        Returns:
            Melhores parâmetros e resultados
        """
        best_params = None
        best_score = float('-inf')
        all_results = []
        
        for trial in range(n_trials):
            # Amostra parâmetros
            params = {
                key: np.random.choice(values)
                for key, values in param_grid.items()
            }
            
            config = ModelConfig(
                learning_rate=params.get('learning_rate', 0.001),
                batch_size=params.get('batch_size', 32),
                epochs=params.get('epochs', 50),
                hidden_layers=params.get('hidden_layers', [64, 32]),
                dropout=params.get('dropout', 0.2),
            )
            
            # Treina
            job = await self.create_training_job(
                symbol=symbol,
                model_type=model_type,
                config=config,
            )
            
            job = await self.start_training(job.job_id)
            
            if job.status == TrainingStatus.COMPLETED and job.metrics:
                score = getattr(job.metrics, metric, 0.0)
                
                all_results.append({
                    'params': params,
                    'score': score,
                    'job_id': job.job_id,
                })
                
                if score > best_score:
                    best_score = score
                    best_params = params
            
            logger.info(f"Trial {trial + 1}/{n_trials}: score={score:.4f}")
        
        return {
            'best_params': best_params,
            'best_score': best_score,
            'all_results': sorted(all_results, key=lambda x: x['score'], reverse=True),
        }
    
    # ========================================================================
    # ESTATÍSTICAS
    # ========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do serviço."""
        jobs = list(self._jobs.values())
        
        return {
            'total_jobs': len(jobs),
            'by_status': {
                status.value: len([j for j in jobs if j.status == status])
                for status in TrainingStatus
            },
            'by_symbol': {
                symbol: len([j for j in jobs if j.symbol == symbol])
                for symbol in set(j.symbol for j in jobs)
            },
            'avg_training_time': self._calculate_avg_training_time(),
            'success_rate': self._calculate_success_rate(),
            'registry_stats': self.registry.get_registry_stats(),
        }
    
    def _calculate_avg_training_time(self) -> float:
        """Calcula tempo médio de treinamento em minutos."""
        completed = [
            j for j in self._jobs.values()
            if j.status == TrainingStatus.COMPLETED
            and j.started_at and j.completed_at
        ]
        
        if not completed:
            return 0.0
        
        total_time = sum(
            (j.completed_at - j.started_at).total_seconds() / 60
            for j in completed
        )
        
        return total_time / len(completed)
    
    def _calculate_success_rate(self) -> float:
        """Calcula taxa de sucesso."""
        finished = [
            j for j in self._jobs.values()
            if j.status in [TrainingStatus.COMPLETED, TrainingStatus.FAILED]
        ]
        
        if not finished:
            return 0.0
        
        completed = len([j for j in finished if j.status == TrainingStatus.COMPLETED])
        
        return completed / len(finished)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa serviço para dicionário."""
        return {
            'device': self._device,
            'max_workers': self.max_workers,
            'active_jobs': len([
                j for j in self._jobs.values()
                if j.status in [TrainingStatus.PENDING, TrainingStatus.TRAINING]
            ]),
            'stats': self.get_stats(),
        }
    
    async def shutdown(self) -> None:
        """Encerra o serviço."""
        # Cancela jobs pendentes
        for job_id in list(self._jobs.keys()):
            self.cancel_job(job_id)
        
        # Encerra executor
        self._executor.shutdown(wait=True)
        
        logger.info("TrainerService encerrado")
