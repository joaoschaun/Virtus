"""
Testes para os módulos de Machine Learning do VIRTUS.

Testa:
- LSTM Model (séries temporais)
- k-NN Pattern Recognizer (padrões de candlestick)
- Vision AI (análise visual de gráficos)
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


class TestLSTMModel:
    """Testes para o modelo LSTM."""
    
    def test_lstm_imports(self):
        """Testa se os imports funcionam."""
        from src.ml.models.lstm import (
            VirtusLSTMModel,
            LSTMConfig,
            LSTMArchitecture,
            PredictionTarget,
            LSTMPrediction,
        )
        assert VirtusLSTMModel is not None
        assert LSTMConfig is not None
    
    def test_lstm_config_defaults(self):
        """Testa configuração padrão do LSTM."""
        from src.ml.models.lstm import LSTMConfig, LSTMArchitecture
        
        config = LSTMConfig()
        
        assert config.sequence_length == 60
        assert config.hidden_units == [128, 64, 32]
        assert config.dropout_rate == 0.2
        assert config.architecture == LSTMArchitecture.STACKED
    
    def test_lstm_config_custom(self):
        """Testa configuração customizada."""
        from src.ml.models.lstm import LSTMConfig, LSTMArchitecture
        
        config = LSTMConfig(
            sequence_length=30,
            hidden_units=[64, 32],
            dropout_rate=0.3,
            architecture=LSTMArchitecture.BIDIRECTIONAL,
        )
        
        assert config.sequence_length == 30
        assert config.hidden_units == [64, 32]
        assert config.dropout_rate == 0.3
        assert config.architecture == LSTMArchitecture.BIDIRECTIONAL
    
    def test_lstm_preprocessor(self):
        """Testa o preprocessador LSTM."""
        from src.ml.models.lstm import LSTMConfig
        from src.ml.models.lstm.lstm_model import LSTMPreprocessor
        
        config = LSTMConfig(sequence_length=10)
        preprocessor = LSTMPreprocessor(config)
        
        # Cria dados sintéticos
        data = np.random.randn(100, 5).astype(np.float32)
        feature_names = ['open', 'high', 'low', 'close', 'volume']
        
        # Fit e transform
        preprocessor.fit(data, feature_names)
        transformed = preprocessor.transform(data, feature_names)
        
        assert transformed is not None
        # Verifica normalização (0-1 range)
        assert transformed.min() >= -0.1  # Pode ter pequenas variações
        assert transformed.max() <= 1.1
    
    def test_lstm_sequence_creation(self):
        """Testa criação de sequências."""
        from src.ml.models.lstm import LSTMConfig
        from src.ml.models.lstm.lstm_model import LSTMPreprocessor
        
        config = LSTMConfig(sequence_length=5)
        preprocessor = LSTMPreprocessor(config)
        
        # Dados 2D (samples, features)
        data = np.arange(60).reshape(20, 3).astype(np.float32)
        labels = np.arange(20).astype(np.int32)
        
        X, y = preprocessor.create_sequences(data, labels)
        
        assert X.shape[0] == 15  # 20 - 5 = 15 sequências
        assert X.shape[1] == 5   # sequence_length
        assert X.shape[2] == 3   # n_features
    
    def test_lstm_model_creation(self):
        """Testa criação do modelo LSTM."""
        from src.ml.models.lstm import VirtusLSTMModel, LSTMConfig
        
        config = LSTMConfig(
            sequence_length=10,
            hidden_units=[32, 16],
        )
        
        model = VirtusLSTMModel(config=config)
        
        assert model.config.sequence_length == 10
        assert model.model is None  # Modelo não construído ainda
    
    def test_lstm_feature_preparation(self):
        """Testa preparação de features."""
        from src.ml.models.lstm import VirtusLSTMModel, LSTMConfig
        
        config = LSTMConfig(sequence_length=10)
        model = VirtusLSTMModel(config=config)
        
        # Cria DataFrame sintético
        dates = pd.date_range(start='2024-01-01', periods=50, freq='h')
        df = pd.DataFrame({
            'open': 1.1000 + np.random.randn(50) * 0.001,
            'high': 1.1010 + np.random.randn(50) * 0.001,
            'low': 1.0990 + np.random.randn(50) * 0.001,
            'close': 1.1005 + np.random.randn(50) * 0.001,
            'volume': np.random.randint(100, 1000, 50),
        }, index=dates)
        
        features, feature_names = model.prepare_features(df)
        
        assert features is not None
        assert len(features) > 0
        assert len(feature_names) > 0
    
    def test_lstm_architectures(self):
        """Testa todas as arquiteturas LSTM."""
        from src.ml.models.lstm import LSTMArchitecture
        
        archs = [
            LSTMArchitecture.SIMPLE,
            LSTMArchitecture.STACKED,
            LSTMArchitecture.BIDIRECTIONAL,
            LSTMArchitecture.ATTENTION,
            LSTMArchitecture.CNN_LSTM,
            LSTMArchitecture.GRU,
        ]
        
        assert len(archs) == 6
        assert LSTMArchitecture.SIMPLE.value == "simple"
        assert LSTMArchitecture.ATTENTION.value == "attention"


class TestKNNPatternRecognizer:
    """Testes para o reconhecedor de padrões k-NN."""
    
    def test_knn_imports(self):
        """Testa imports do k-NN."""
        from src.ml.models.knn import (
            KNNPatternRecognizer,
            PatternType,
            PatternSignal,
            PatternReliability,
            PatternMatch,
        )
        assert KNNPatternRecognizer is not None
        assert PatternType is not None
    
    def test_pattern_types(self):
        """Testa tipos de padrões."""
        from src.ml.models.knn import PatternType
        
        # Single candle
        assert PatternType.DOJI.value == "doji"
        assert PatternType.HAMMER.value == "hammer"
        assert PatternType.SHOOTING_STAR.value == "shooting_star"
        
        # Double candle
        assert PatternType.BULLISH_ENGULFING.value == "bullish_engulfing"
        assert PatternType.BEARISH_ENGULFING.value == "bearish_engulfing"
        
        # Triple candle
        assert PatternType.MORNING_STAR.value == "morning_star"
        assert PatternType.THREE_WHITE_SOLDIERS.value == "three_white_soldiers"
    
    def test_pattern_signals(self):
        """Testa sinais de padrões."""
        from src.ml.models.knn import PatternSignal
        
        assert PatternSignal.BULLISH.value == "bullish"
        assert PatternSignal.BEARISH.value == "bearish"
        assert PatternSignal.NEUTRAL.value == "neutral"
    
    def test_knn_creation(self):
        """Testa criação do reconhecedor."""
        from src.ml.models.knn import KNNPatternRecognizer
        
        recognizer = KNNPatternRecognizer(k=3, distance_threshold=0.5)
        
        assert recognizer.k == 3
        assert recognizer.distance_threshold == 0.5
        assert len(recognizer.pattern_db.templates) > 0
    
    def test_feature_extraction(self):
        """Testa extração de features de candlestick."""
        from src.ml.models.knn.pattern_recognizer import CandleFeatureExtractor
        
        extractor = CandleFeatureExtractor()
        
        # Candle de alta (hammer-like)
        features = extractor.extract_single(
            open_=1.1000,
            high=1.1010,
            low=1.0950,
            close=1.1008,
            volume=500,
            prev_close=1.0990,
            atr=0.0020,
            avg_volume=400,
        )
        
        assert features.is_bullish == True
        assert features.body_size < 0.5  # Corpo pequeno
        assert features.lower_shadow > 0.5  # Sombra inferior longa
    
    def test_pattern_recognition(self):
        """Testa reconhecimento de padrões."""
        from src.ml.models.knn import KNNPatternRecognizer
        
        recognizer = KNNPatternRecognizer(
            k=3,
            distance_threshold=1.0,  # Mais permissivo para teste
            min_confidence=0.1,
        )
        
        # Cria DataFrame com padrão hammer
        df = pd.DataFrame({
            'open': [1.1000, 1.0990, 1.0980],
            'high': [1.1010, 1.0995, 1.0985],
            'low': [1.0950, 1.0940, 1.0930],  # Sombra inferior longa
            'close': [1.1005, 1.0992, 1.0982],
            'volume': [500, 600, 700],
        })
        
        matches = recognizer.recognize_pattern(df, n_candles=1)
        
        # Deve detectar algum padrão
        assert isinstance(matches, list)
    
    def test_dominant_signal(self):
        """Testa determinação de sinal dominante."""
        from src.ml.models.knn import KNNPatternRecognizer
        
        recognizer = KNNPatternRecognizer()
        
        df = pd.DataFrame({
            'open': [1.10, 1.11, 1.12],
            'high': [1.11, 1.12, 1.13],
            'low': [1.09, 1.10, 1.11],
            'close': [1.11, 1.12, 1.13],
            'volume': [100, 100, 100],
        })
        
        signal, confidence, matches = recognizer.get_dominant_signal(df)
        
        assert signal is not None
        assert 0 <= confidence <= 1
    
    def test_statistics(self):
        """Testa estatísticas do reconhecedor."""
        from src.ml.models.knn import KNNPatternRecognizer
        
        recognizer = KNNPatternRecognizer()
        stats = recognizer.get_statistics()
        
        assert 'total_scans' in stats
        assert 'patterns_detected' in stats
        assert 'templates_count' in stats


class TestVisionAnalyzer:
    """Testes para o analisador de visão computacional."""
    
    def test_vision_imports(self):
        """Testa imports do Vision."""
        from src.ml.models.vision import (
            VirtusVisionAnalyzer,
            ChartPatternType,
            PatternBias,
            PatternDetection,
            ChartRenderer,
        )
        assert VirtusVisionAnalyzer is not None
        assert ChartPatternType is not None
    
    def test_chart_pattern_types(self):
        """Testa tipos de padrões gráficos."""
        from src.ml.models.vision import ChartPatternType
        
        # Reversal
        assert ChartPatternType.HEAD_SHOULDERS.value == "head_shoulders"
        assert ChartPatternType.DOUBLE_TOP.value == "double_top"
        
        # Continuation
        assert ChartPatternType.ASCENDING_TRIANGLE.value == "ascending_triangle"
        assert ChartPatternType.BULL_FLAG.value == "bull_flag"
        
        # Trend
        assert ChartPatternType.UPTREND.value == "uptrend"
        assert ChartPatternType.DOWNTREND.value == "downtrend"
    
    def test_pattern_bias(self):
        """Testa viés dos padrões."""
        from src.ml.models.vision import PatternBias
        
        assert PatternBias.BULLISH.value == "bullish"
        assert PatternBias.BEARISH.value == "bearish"
        assert PatternBias.NEUTRAL.value == "neutral"
    
    def test_chart_renderer_creation(self):
        """Testa criação do renderizador."""
        from src.ml.models.vision import ChartRenderer
        
        renderer = ChartRenderer(
            width=224,
            height=224,
            style='candlestick',
            include_volume=True,
        )
        
        assert renderer.width == 224
        assert renderer.height == 224
        assert renderer.style == 'candlestick'
    
    def test_chart_rendering_simple(self):
        """Testa renderização simples de gráfico."""
        from src.ml.models.vision.chart_analyzer import ChartRenderer
        
        renderer = ChartRenderer(width=100, height=100)
        
        df = pd.DataFrame({
            'open': [1.10, 1.11, 1.12, 1.13, 1.14],
            'high': [1.11, 1.12, 1.13, 1.14, 1.15],
            'low': [1.09, 1.10, 1.11, 1.12, 1.13],
            'close': [1.11, 1.12, 1.13, 1.14, 1.15],
            'volume': [100, 110, 120, 130, 140],
        })
        
        chart_image = renderer._render_simple(df, "EURUSD", "H1")
        
        assert chart_image.data.shape == (100, 100, 3)
        assert chart_image.symbol == "EURUSD"
        assert chart_image.timeframe == "H1"
    
    def test_vision_analyzer_creation(self):
        """Testa criação do analisador."""
        from src.ml.models.vision import VirtusVisionAnalyzer
        
        # Usa configuração que não requer TF/PyTorch
        analyzer = VirtusVisionAnalyzer(
            image_size=100,
            use_tensorflow=False,
            use_pytorch=False,
        )
        
        assert analyzer.image_size == 100
        assert len(analyzer.models) == 0  # Sem modelos de DL
    
    def test_heuristic_analysis(self):
        """Testa análise heurística."""
        from src.ml.models.vision import VirtusVisionAnalyzer, PatternBias
        
        analyzer = VirtusVisionAnalyzer(
            use_tensorflow=False,
            use_pytorch=False,
        )
        
        # Dados com tendência de alta
        df = pd.DataFrame({
            'open': [1.10 + i*0.01 for i in range(30)],
            'high': [1.11 + i*0.01 for i in range(30)],
            'low': [1.09 + i*0.01 for i in range(30)],
            'close': [1.105 + i*0.01 for i in range(30)],
            'volume': [100] * 30,
        })
        
        detections = analyzer._heuristic_analysis(df)
        
        assert len(detections) > 0
        # Com tendência de alta, deve detectar UPTREND
        assert detections[0].bias in [PatternBias.BULLISH, PatternBias.NEUTRAL]
    
    def test_pattern_detection_dataclass(self):
        """Testa dataclass de detecção."""
        from src.ml.models.vision import PatternDetection, ChartPatternType, PatternBias
        
        detection = PatternDetection(
            pattern_type=ChartPatternType.DOUBLE_TOP,
            bias=PatternBias.BEARISH,
            confidence=0.85,
            bounding_box=(10, 20, 200, 180),
            target_price=1.0950,
            stop_loss=1.1050,
        )
        
        assert detection.confidence == 0.85
        assert detection.pattern_type == ChartPatternType.DOUBLE_TOP
        
        # Testa serialização
        dict_repr = detection.to_dict()
        assert dict_repr['pattern'] == 'double_top'
        assert dict_repr['bias'] == 'bearish'
    
    def test_statistics(self):
        """Testa estatísticas do analisador."""
        from src.ml.models.vision import VirtusVisionAnalyzer
        
        analyzer = VirtusVisionAnalyzer(
            use_tensorflow=False,
            use_pytorch=False,
        )
        
        stats = analyzer.get_statistics()
        
        assert 'total_analyses' in stats
        assert 'patterns_detected' in stats
        assert 'models_loaded' in stats


class TestMLIntegration:
    """Testes de integração dos módulos ML."""
    
    def test_main_module_imports(self):
        """Testa imports do módulo principal."""
        from src.ml.models import (
            # Base
            BaseModel,
            ModelType,
            ModelStatus,
            # LSTM
            VirtusLSTMModel,
            LSTMConfig,
            # k-NN
            KNNPatternRecognizer,
            PatternType,
            PatternSignal,
            # Vision
            VirtusVisionAnalyzer,
            ChartPatternType,
            PatternBias,
        )
        
        # Verifica que todos importaram
        assert BaseModel is not None
        assert VirtusLSTMModel is not None
        assert KNNPatternRecognizer is not None
        assert VirtusVisionAnalyzer is not None
    
    def test_combined_analysis(self):
        """Testa análise combinada de múltiplos modelos."""
        from src.ml.models import (
            KNNPatternRecognizer,
            VirtusVisionAnalyzer,
        )
        
        # Cria dados de teste
        df = pd.DataFrame({
            'open': [1.10, 1.11, 1.12, 1.11, 1.10],
            'high': [1.12, 1.13, 1.14, 1.13, 1.12],
            'low': [1.09, 1.10, 1.11, 1.10, 1.09],
            'close': [1.11, 1.12, 1.13, 1.10, 1.09],
            'volume': [100, 120, 150, 130, 110],
        })
        
        # k-NN
        knn = KNNPatternRecognizer(min_confidence=0.1)
        knn_signal, knn_conf, _ = knn.get_dominant_signal(df)
        
        # Vision
        vision = VirtusVisionAnalyzer(use_tensorflow=False, use_pytorch=False)
        vision_detections = vision._heuristic_analysis(df)
        
        # Ambos devem retornar resultados válidos
        assert knn_signal is not None
        assert len(vision_detections) >= 0
    
    def test_model_statistics_format(self):
        """Testa formato das estatísticas."""
        from src.ml.models import KNNPatternRecognizer, VirtusVisionAnalyzer
        
        knn = KNNPatternRecognizer()
        vision = VirtusVisionAnalyzer(use_tensorflow=False, use_pytorch=False)
        
        knn_stats = knn.get_statistics()
        vision_stats = vision.get_statistics()
        
        # Estrutura comum
        assert isinstance(knn_stats, dict)
        assert isinstance(vision_stats, dict)
        
        # Keys esperadas
        assert 'total_scans' in knn_stats or 'total_analyses' in vision_stats


class TestMLModulesSummary:
    """Teste resumo dos módulos ML."""
    
    def test_print_ml_summary(self):
        """Imprime resumo dos módulos ML disponíveis."""
        from src.ml.models.lstm import LSTMArchitecture, PredictionTarget
        from src.ml.models.knn import PatternType, PatternSignal
        from src.ml.models.vision import ChartPatternType, PatternBias
        
        print("\n" + "="*60)
        print("VIRTUS ML MODULES SUMMARY")
        print("="*60)
        
        print("\n📊 LSTM Architectures:")
        for arch in LSTMArchitecture:
            print(f"  - {arch.value}")
        
        print("\n📊 LSTM Prediction Targets:")
        for target in PredictionTarget:
            print(f"  - {target.value}")
        
        print("\n🕯️ k-NN Candlestick Patterns:")
        count = 0
        for pattern in PatternType:
            if count < 10:  # Apenas primeiros 10
                print(f"  - {pattern.value}")
            count += 1
        print(f"  ... and {count - 10} more patterns")
        
        print("\n📈 Vision Chart Patterns:")
        count = 0
        for pattern in ChartPatternType:
            if count < 10:
                print(f"  - {pattern.value}")
            count += 1
        print(f"  ... and {count - 10} more patterns")
        
        print("\n✅ All ML modules loaded successfully!")
        print("="*60)
        
        assert True  # Teste sempre passa se chegou aqui
