"""
VIRTUS ML - Config Module
=========================

Carregamento e validação de configurações ML.
"""

import yaml
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Diretório de configurações
CONFIG_DIR = Path(__file__).parent


@dataclass
class LSTMConfig:
    """Configuração de modelo LSTM."""
    architecture: str = "bidirectional"
    hidden_units: int = 128
    num_layers: int = 2
    dropout: float = 0.2
    recurrent_dropout: float = 0.2
    sequence_length: int = 60
    features: int = 50
    use_attention: bool = True
    bidirectional: bool = True
    dense_units: int = 64


@dataclass
class KNNConfig:
    """Configuração de modelo k-NN."""
    n_neighbors: int = 5
    weights: str = "distance"
    metric: str = "minkowski"
    algorithm: str = "auto"
    patterns: list = field(default_factory=lambda: [
        "hammer", "engulfing", "doji", "morning_star", "evening_star"
    ])


@dataclass
class CNNConfig:
    """Configuração de modelo CNN."""
    image_size: int = 224
    backbone: str = "efficientnet_b0"
    pretrained: bool = True
    num_classes: int = 3
    dropout: float = 0.3


@dataclass
class TrainingConfig:
    """Configuração de treinamento."""
    epochs: int = 100
    batch_size: int = 32
    learning_rate: float = 0.001
    early_stopping_patience: int = 15
    reduce_lr_patience: int = 5
    reduce_lr_factor: float = 0.5
    min_lr: float = 0.00001


@dataclass
class DataSplitConfig:
    """Configuração de split de dados."""
    method: str = "temporal"
    train_ratio: float = 0.7
    val_ratio: float = 0.15
    test_ratio: float = 0.15
    purge_gap: int = 0


class ConfigLoader:
    """Carregador de configurações YAML."""
    
    _instance: Optional['ConfigLoader'] = None
    _configs: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._configs:
            self._load_all_configs()
    
    def _load_all_configs(self):
        """Carrega todas as configurações YAML."""
        for yaml_file in CONFIG_DIR.glob("*.yaml"):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    config_name = yaml_file.stem
                    self._configs[config_name] = yaml.safe_load(f)
                    logger.info(f"Loaded config: {config_name}")
            except Exception as e:
                logger.warning(f"Failed to load {yaml_file}: {e}")
    
    def get_model_config(self, model_type: str) -> Dict[str, Any]:
        """Retorna configuração de um modelo específico."""
        model_configs = self._configs.get('model_configs', {})
        models = model_configs.get('models', {})
        return models.get(model_type, {})
    
    def get_training_config(self) -> Dict[str, Any]:
        """Retorna configuração de treinamento."""
        training_configs = self._configs.get('training_configs', {})
        return training_configs.get('training', {})
    
    def get_data_split_config(self) -> Dict[str, Any]:
        """Retorna configuração de split de dados."""
        training_configs = self._configs.get('training_configs', {})
        return training_configs.get('data_split', {})
    
    def get_symbol_config(self, symbol: str) -> Dict[str, Any]:
        """Retorna configuração específica de símbolo."""
        model_configs = self._configs.get('model_configs', {})
        symbols = model_configs.get('symbol_specific', {})
        return symbols.get(symbol, {})
    
    def get_lstm_config(self, symbol: Optional[str] = None) -> LSTMConfig:
        """Retorna configuração LSTM tipada."""
        base = self.get_model_config('lstm')
        
        if symbol:
            symbol_config = self.get_symbol_config(symbol)
            if 'lstm_overrides' in symbol_config:
                base.update(symbol_config['lstm_overrides'])
        
        return LSTMConfig(**{k: v for k, v in base.items() if hasattr(LSTMConfig, k)})
    
    def get_knn_config(self) -> KNNConfig:
        """Retorna configuração k-NN tipada."""
        config = self.get_model_config('knn')
        return KNNConfig(**{k: v for k, v in config.items() if hasattr(KNNConfig, k)})
    
    def get_cnn_config(self) -> CNNConfig:
        """Retorna configuração CNN tipada."""
        config = self.get_model_config('cnn')
        return CNNConfig(**{k: v for k, v in config.items() if hasattr(CNNConfig, k)})


# Singleton instance
config_loader = ConfigLoader()


def load_model_config(model_type: str) -> Dict[str, Any]:
    """Helper function para carregar config de modelo."""
    return config_loader.get_model_config(model_type)


def load_training_config() -> Dict[str, Any]:
    """Helper function para carregar config de treinamento."""
    return config_loader.get_training_config()


def load_symbol_config(symbol: str) -> Dict[str, Any]:
    """Helper function para carregar config de símbolo."""
    return config_loader.get_symbol_config(symbol)
