"""
VIRTUS ML - Checkpointing
==========================

Sistema de checkpoints para modelos ML.
"""

import json
import shutil
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class CheckpointMetadata:
    """Metadados de um checkpoint."""
    checkpoint_id: str
    model_name: str
    model_type: str
    symbol: str
    epoch: int
    
    # Métricas no momento do checkpoint
    train_loss: float
    val_loss: float
    val_accuracy: float
    
    # Timestamps
    created_at: str
    training_time_seconds: float
    
    # Configuração
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Info adicional
    is_best: bool = False
    notes: str = ""


class CheckpointManager:
    """
    Gerenciador de checkpoints de modelos.
    
    Features:
    - Salvar/carregar checkpoints
    - Tracking do melhor modelo
    - Limpeza automática de checkpoints antigos
    - Versionamento
    """
    
    def __init__(
        self,
        checkpoint_dir: Union[str, Path],
        max_checkpoints: int = 5,
        keep_best: bool = True
    ):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_checkpoints = max_checkpoints
        self.keep_best = keep_best
        
        self.metadata_file = self.checkpoint_dir / "metadata.json"
        self.checkpoints: Dict[str, CheckpointMetadata] = {}
        self.best_checkpoint_id: Optional[str] = None
        
        self._load_metadata()
    
    def _load_metadata(self):
        """Carrega metadados existentes."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    data = json.load(f)
                
                self.checkpoints = {
                    k: CheckpointMetadata(**v) 
                    for k, v in data.get('checkpoints', {}).items()
                }
                self.best_checkpoint_id = data.get('best_checkpoint_id')
                
            except Exception as e:
                logger.warning(f"Erro ao carregar metadados: {e}")
    
    def _save_metadata(self):
        """Salva metadados."""
        data = {
            'checkpoints': {k: asdict(v) for k, v in self.checkpoints.items()},
            'best_checkpoint_id': self.best_checkpoint_id,
        }
        
        with open(self.metadata_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _generate_checkpoint_id(
        self,
        model_name: str,
        epoch: int
    ) -> str:
        """Gera ID único para checkpoint."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_input = f"{model_name}_{epoch}_{timestamp}"
        hash_suffix = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        
        return f"{model_name}_epoch{epoch}_{hash_suffix}"
    
    def save_checkpoint(
        self,
        model,
        model_name: str,
        model_type: str,
        symbol: str,
        epoch: int,
        train_loss: float,
        val_loss: float,
        val_accuracy: float,
        training_time: float = 0.0,
        config: Optional[Dict] = None,
        notes: str = "",
        optimizer=None,
        extra_state: Optional[Dict] = None
    ) -> str:
        """
        Salva checkpoint do modelo.
        
        Args:
            model: Modelo a salvar
            model_name: Nome do modelo
            model_type: Tipo (LSTM, CNN, etc.)
            symbol: Símbolo do ativo
            epoch: Época atual
            train_loss: Loss de treino
            val_loss: Loss de validação
            val_accuracy: Acurácia de validação
            training_time: Tempo de treino em segundos
            config: Configuração do modelo
            notes: Notas adicionais
            optimizer: Optimizer (opcional)
            extra_state: Estado adicional (opcional)
            
        Returns:
            ID do checkpoint
        """
        checkpoint_id = self._generate_checkpoint_id(model_name, epoch)
        checkpoint_path = self.checkpoint_dir / checkpoint_id
        checkpoint_path.mkdir(exist_ok=True)
        
        # Verifica se é o melhor
        is_best = False
        if self.best_checkpoint_id is None:
            is_best = True
        else:
            best_meta = self.checkpoints.get(self.best_checkpoint_id)
            if best_meta and val_accuracy > best_meta.val_accuracy:
                is_best = True
        
        # Metadados
        metadata = CheckpointMetadata(
            checkpoint_id=checkpoint_id,
            model_name=model_name,
            model_type=model_type,
            symbol=symbol,
            epoch=epoch,
            train_loss=train_loss,
            val_loss=val_loss,
            val_accuracy=val_accuracy,
            created_at=datetime.now().isoformat(),
            training_time_seconds=training_time,
            config=config or {},
            is_best=is_best,
            notes=notes,
        )
        
        # Salva modelo (detecta framework)
        try:
            self._save_model(model, checkpoint_path, model_type)
        except Exception as e:
            logger.error(f"Erro ao salvar modelo: {e}")
            raise
        
        # Salva optimizer se fornecido
        if optimizer:
            self._save_optimizer(optimizer, checkpoint_path, model_type)
        
        # Salva estado extra
        if extra_state:
            with open(checkpoint_path / "extra_state.json", 'w') as f:
                json.dump(extra_state, f)
        
        # Salva metadados do checkpoint
        with open(checkpoint_path / "metadata.json", 'w') as f:
            json.dump(asdict(metadata), f, indent=2)
        
        # Atualiza estado
        self.checkpoints[checkpoint_id] = metadata
        
        if is_best:
            self.best_checkpoint_id = checkpoint_id
            logger.info(f"Novo melhor checkpoint: {checkpoint_id}")
        
        self._save_metadata()
        
        # Limpa checkpoints antigos
        self._cleanup_old_checkpoints()
        
        logger.info(f"Checkpoint salvo: {checkpoint_id}")
        
        return checkpoint_id
    
    def _save_model(self, model, path: Path, model_type: str):
        """Salva modelo baseado no tipo."""
        
        # Tenta TensorFlow/Keras
        if hasattr(model, 'save'):
            try:
                model.save(str(path / "model.h5"))
                return
            except:
                pass
        
        # Tenta PyTorch
        try:
            import torch
            if hasattr(model, 'state_dict'):
                torch.save(model.state_dict(), path / "model.pt")
                return
        except ImportError:
            pass
        
        # Tenta scikit-learn / joblib
        try:
            import joblib
            joblib.dump(model, path / "model.joblib")
            return
        except:
            pass
        
        # Fallback: pickle
        import pickle
        with open(path / "model.pkl", 'wb') as f:
            pickle.dump(model, f)
    
    def _save_optimizer(self, optimizer, path: Path, model_type: str):
        """Salva optimizer."""
        try:
            import torch
            if hasattr(optimizer, 'state_dict'):
                torch.save(optimizer.state_dict(), path / "optimizer.pt")
                return
        except ImportError:
            pass
        
        # Keras optimizers são salvos com o modelo
    
    def load_checkpoint(
        self,
        checkpoint_id: str,
        model=None,
        optimizer=None,
        load_model: bool = True
    ) -> Dict[str, Any]:
        """
        Carrega checkpoint.
        
        Args:
            checkpoint_id: ID do checkpoint
            model: Modelo para carregar pesos (opcional)
            optimizer: Optimizer para carregar estado (opcional)
            load_model: Se deve carregar modelo
            
        Returns:
            Dicionário com estado carregado
        """
        if checkpoint_id not in self.checkpoints:
            raise ValueError(f"Checkpoint não encontrado: {checkpoint_id}")
        
        checkpoint_path = self.checkpoint_dir / checkpoint_id
        
        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Diretório não encontrado: {checkpoint_path}")
        
        result = {
            'metadata': self.checkpoints[checkpoint_id],
            'model': None,
            'optimizer': None,
            'extra_state': None,
        }
        
        # Carrega modelo
        if load_model:
            result['model'] = self._load_model(checkpoint_path, model)
        
        # Carrega optimizer
        if optimizer:
            result['optimizer'] = self._load_optimizer(checkpoint_path, optimizer)
        
        # Carrega estado extra
        extra_state_path = checkpoint_path / "extra_state.json"
        if extra_state_path.exists():
            with open(extra_state_path, 'r') as f:
                result['extra_state'] = json.load(f)
        
        logger.info(f"Checkpoint carregado: {checkpoint_id}")
        
        return result
    
    def _load_model(self, path: Path, model=None):
        """Carrega modelo."""
        
        # TensorFlow/Keras
        if (path / "model.h5").exists():
            try:
                from tensorflow import keras
                return keras.models.load_model(str(path / "model.h5"))
            except:
                pass
        
        # PyTorch
        if (path / "model.pt").exists():
            try:
                import torch
                state_dict = torch.load(path / "model.pt", map_location='cpu')
                if model:
                    model.load_state_dict(state_dict)
                    return model
                return state_dict
            except:
                pass
        
        # Joblib
        if (path / "model.joblib").exists():
            import joblib
            return joblib.load(path / "model.joblib")
        
        # Pickle
        if (path / "model.pkl").exists():
            import pickle
            with open(path / "model.pkl", 'rb') as f:
                return pickle.load(f)
        
        return None
    
    def _load_optimizer(self, path: Path, optimizer):
        """Carrega optimizer."""
        if (path / "optimizer.pt").exists():
            try:
                import torch
                state_dict = torch.load(path / "optimizer.pt", map_location='cpu')
                optimizer.load_state_dict(state_dict)
                return optimizer
            except:
                pass
        return optimizer
    
    def load_best_checkpoint(self, model=None) -> Dict[str, Any]:
        """Carrega o melhor checkpoint."""
        if not self.best_checkpoint_id:
            raise ValueError("Nenhum melhor checkpoint registrado")
        
        return self.load_checkpoint(self.best_checkpoint_id, model)
    
    def _cleanup_old_checkpoints(self):
        """Remove checkpoints antigos mantendo os melhores."""
        if len(self.checkpoints) <= self.max_checkpoints:
            return
        
        # Ordena por data de criação
        sorted_checkpoints = sorted(
            self.checkpoints.items(),
            key=lambda x: x[1].created_at,
            reverse=True
        )
        
        to_remove = []
        kept = 0
        
        for checkpoint_id, metadata in sorted_checkpoints:
            # Sempre mantém o melhor
            if self.keep_best and checkpoint_id == self.best_checkpoint_id:
                continue
            
            if kept >= self.max_checkpoints:
                to_remove.append(checkpoint_id)
            else:
                kept += 1
        
        # Remove checkpoints
        for checkpoint_id in to_remove:
            self.delete_checkpoint(checkpoint_id)
    
    def delete_checkpoint(self, checkpoint_id: str):
        """Deleta um checkpoint."""
        if checkpoint_id not in self.checkpoints:
            return
        
        checkpoint_path = self.checkpoint_dir / checkpoint_id
        
        if checkpoint_path.exists():
            shutil.rmtree(checkpoint_path)
        
        del self.checkpoints[checkpoint_id]
        
        if self.best_checkpoint_id == checkpoint_id:
            self.best_checkpoint_id = None
            # Encontra novo melhor
            if self.checkpoints:
                best = max(
                    self.checkpoints.values(),
                    key=lambda x: x.val_accuracy
                )
                self.best_checkpoint_id = best.checkpoint_id
        
        self._save_metadata()
        
        logger.info(f"Checkpoint deletado: {checkpoint_id}")
    
    def list_checkpoints(self) -> List[CheckpointMetadata]:
        """Lista todos os checkpoints."""
        return sorted(
            self.checkpoints.values(),
            key=lambda x: x.created_at,
            reverse=True
        )
    
    def get_checkpoint_info(self, checkpoint_id: str) -> Optional[CheckpointMetadata]:
        """Retorna informações de um checkpoint."""
        return self.checkpoints.get(checkpoint_id)
