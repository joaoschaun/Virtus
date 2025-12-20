"""
Serviço de Gestão Patrimonial
Consolida todos os ativos: MT4, Ações, FIIs, etc.
"""
import json
import os
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


# Cache da cotação do dólar
_cotacao_cache = {
    "valor": 6.10,  # Valor padrão
    "timestamp": None
}


async def get_cotacao_dolar() -> float:
    """Busca cotação atual do dólar (USD/BRL)"""
    global _cotacao_cache
    
    # Verificar cache (válido por 1 hora)
    if _cotacao_cache["timestamp"]:
        diff = datetime.now() - _cotacao_cache["timestamp"]
        if diff.total_seconds() < 3600:  # 1 hora
            return _cotacao_cache["valor"]
    
    try:
        # Usar API gratuita do Banco Central ou AwesomeAPI
        async with httpx.AsyncClient(timeout=10) as client:
            # AwesomeAPI - gratuita e confiável
            response = await client.get("https://economia.awesomeapi.com.br/json/last/USD-BRL")
            if response.status_code == 200:
                data = response.json()
                cotacao = float(data["USDBRL"]["bid"])
                _cotacao_cache["valor"] = cotacao
                _cotacao_cache["timestamp"] = datetime.now()
                return cotacao
    except Exception as e:
        print(f"⚠️ Erro ao buscar cotação: {e}")
    
    return _cotacao_cache["valor"]


def get_cotacao_dolar_sync() -> float:
    """Versão síncrona para buscar cotação"""
    global _cotacao_cache
    
    # Verificar cache
    if _cotacao_cache["timestamp"]:
        diff = datetime.now() - _cotacao_cache["timestamp"]
        if diff.total_seconds() < 3600:
            return _cotacao_cache["valor"]
    
    try:
        import requests
        
        # Tentar Banco Central do Brasil primeiro
        try:
            response = requests.get(
                "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarDia(dataCotacao=@dataCotacao)?@dataCotacao=''&$format=json",
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('value') and len(data['value']) > 0:
                    cotacao = float(data['value'][0]['cotacaoCompra'])
                    _cotacao_cache["valor"] = cotacao
                    _cotacao_cache["timestamp"] = datetime.now()
                    print(f"💵 Cotação USD/BRL (BCB): R$ {cotacao:.4f}")
                    return cotacao
        except Exception as e:
            print(f"⚠️ BCB API falhou: {e}")
        
        # Fallback: API alternativa
        try:
            response = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=10)
            if response.status_code == 200:
                data = response.json()
                cotacao = float(data['rates']['BRL'])
                _cotacao_cache["valor"] = cotacao
                _cotacao_cache["timestamp"] = datetime.now()
                print(f"💵 Cotação USD/BRL (ExchangeRate): R$ {cotacao:.4f}")
                return cotacao
        except Exception as e:
            print(f"⚠️ ExchangeRate API falhou: {e}")
            
    except Exception as e:
        print(f"⚠️ Erro ao buscar cotação: {e}")
    
    print(f"⚠️ Usando cotação padrão: R$ {_cotacao_cache['valor']:.2f}")
    return _cotacao_cache["valor"]


@dataclass
class PatrimonioSnapshot:
    """Snapshot do patrimônio em um momento"""
    date: str
    total: float
    mt4_balance: float
    acoes_valor: float
    fiis_valor: float
    outros: float
    
    
@dataclass
class PatrimonioResumo:
    """Resumo atual do patrimônio"""
    total: float
    mt4_balance: float
    mt4_balance_usd: float
    mt4_profit: float
    mt4_profit_usd: float
    cotacao_dolar: float
    acoes_valor: float
    acoes_lucro: float
    fiis_valor: float
    fiis_lucro: float
    dividendos_recebidos: float
    outros: float
    variacao_dia: float
    variacao_dia_pct: float
    variacao_mes: float
    variacao_mes_pct: float


class PatrimonioService:
    """Serviço para gestão do patrimônio consolidado"""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent.parent / "data" / "patrimonio"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.patrimonio_file = self.data_dir / "patrimonio.json"
        self.historico_file = self.data_dir / "historico.json"
        
        self._load_data()
    
    def _load_data(self):
        """Carrega dados do patrimônio"""
        # Carregar patrimônio atual
        if self.patrimonio_file.exists():
            with open(self.patrimonio_file, 'r', encoding='utf-8') as f:
                self.patrimonio = json.load(f)
        else:
            self.patrimonio = {
                "mt4_balance": 0,
                "mt4_profit": 0,
                "acoes_valor": 0,
                "acoes_lucro": 0,
                "fiis_valor": 0,
                "fiis_lucro": 0,
                "dividendos_recebidos": 0,
                "outros": 0,
                "last_update": None
            }
        
        # Carregar histórico
        if self.historico_file.exists():
            with open(self.historico_file, 'r', encoding='utf-8') as f:
                self.historico = json.load(f)
        else:
            self.historico = []
    
    def _save_data(self):
        """Salva dados do patrimônio"""
        self.patrimonio["last_update"] = datetime.now().isoformat()
        
        with open(self.patrimonio_file, 'w', encoding='utf-8') as f:
            json.dump(self.patrimonio, f, indent=2, ensure_ascii=False)
        
        with open(self.historico_file, 'w', encoding='utf-8') as f:
            json.dump(self.historico, f, indent=2, ensure_ascii=False)
    
    def get_total(self, cotacao_dolar: float = None) -> float:
        """Calcula patrimônio total (convertendo MT4 USD->BRL)"""
        if cotacao_dolar is None:
            cotacao_dolar = get_cotacao_dolar_sync()
        
        # MT4 está em USD, converter para BRL
        mt4_brl = self.patrimonio.get("mt4_balance", 0) * cotacao_dolar
        
        return (
            mt4_brl +
            self.patrimonio.get("acoes_valor", 0) +
            self.patrimonio.get("fiis_valor", 0) +
            self.patrimonio.get("outros", 0)
        )
    
    def update_mt4(self, balance: float, profit: float):
        """Atualiza dados do MT4"""
        self.patrimonio["mt4_balance"] = balance
        self.patrimonio["mt4_profit"] = profit
        self._save_data()
        self._save_snapshot()
    
    def update_acoes(self, valor: float, lucro: float):
        """Atualiza dados de ações"""
        self.patrimonio["acoes_valor"] = valor
        self.patrimonio["acoes_lucro"] = lucro
        self._save_data()
    
    def update_fiis(self, valor: float, lucro: float):
        """Atualiza dados de FIIs"""
        self.patrimonio["fiis_valor"] = valor
        self.patrimonio["fiis_lucro"] = lucro
        self._save_data()
    
    def add_dividendo(self, valor: float):
        """Adiciona dividendo recebido"""
        self.patrimonio["dividendos_recebidos"] = self.patrimonio.get("dividendos_recebidos", 0) + valor
        self._save_data()
    
    def update_outros(self, valor: float):
        """Atualiza outros ativos"""
        self.patrimonio["outros"] = valor
        self._save_data()
    
    def _save_snapshot(self):
        """Salva snapshot diário do patrimônio"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        snapshot = {
            "date": today,
            "total": self.get_total(),
            "mt4_balance": self.patrimonio.get("mt4_balance", 0),
            "acoes_valor": self.patrimonio.get("acoes_valor", 0),
            "fiis_valor": self.patrimonio.get("fiis_valor", 0),
            "outros": self.patrimonio.get("outros", 0)
        }
        
        # Verificar se já existe snapshot de hoje
        existing_idx = None
        for i, s in enumerate(self.historico):
            if s["date"] == today:
                existing_idx = i
                break
        
        if existing_idx is not None:
            self.historico[existing_idx] = snapshot
        else:
            self.historico.append(snapshot)
        
        # Manter apenas últimos 365 dias
        self.historico = sorted(self.historico, key=lambda x: x["date"])[-365:]
        self._save_data()
    
    def get_resumo(self) -> PatrimonioResumo:
        """Retorna resumo do patrimônio"""
        # Buscar cotação do dólar
        cotacao = get_cotacao_dolar_sync()
        
        # Valores em USD
        mt4_balance_usd = self.patrimonio.get("mt4_balance", 0)
        mt4_profit_usd = self.patrimonio.get("mt4_profit", 0)
        
        # Valores convertidos para BRL
        mt4_balance_brl = mt4_balance_usd * cotacao
        mt4_profit_brl = mt4_profit_usd * cotacao
        
        total = self.get_total(cotacao)
        
        # Calcular variações
        hoje = datetime.now().strftime("%Y-%m-%d")
        ontem = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        inicio_mes = datetime.now().replace(day=1).strftime("%Y-%m-%d")
        
        valor_ontem = None
        valor_inicio_mes = None
        
        for s in self.historico:
            if s["date"] == ontem:
                valor_ontem = s["total"]
            if s["date"] <= inicio_mes and (valor_inicio_mes is None or s["date"] > valor_inicio_mes):
                valor_inicio_mes = s["total"]
        
        variacao_dia = total - valor_ontem if valor_ontem else 0
        variacao_dia_pct = (variacao_dia / valor_ontem * 100) if valor_ontem else 0
        
        variacao_mes = total - valor_inicio_mes if valor_inicio_mes else 0
        variacao_mes_pct = (variacao_mes / valor_inicio_mes * 100) if valor_inicio_mes else 0
        
        return PatrimonioResumo(
            total=total,
            mt4_balance=mt4_balance_brl,
            mt4_balance_usd=mt4_balance_usd,
            mt4_profit=mt4_profit_brl,
            mt4_profit_usd=mt4_profit_usd,
            cotacao_dolar=cotacao,
            acoes_valor=self.patrimonio.get("acoes_valor", 0),
            acoes_lucro=self.patrimonio.get("acoes_lucro", 0),
            fiis_valor=self.patrimonio.get("fiis_valor", 0),
            fiis_lucro=self.patrimonio.get("fiis_lucro", 0),
            dividendos_recebidos=self.patrimonio.get("dividendos_recebidos", 0),
            outros=self.patrimonio.get("outros", 0),
            variacao_dia=variacao_dia,
            variacao_dia_pct=variacao_dia_pct,
            variacao_mes=variacao_mes,
            variacao_mes_pct=variacao_mes_pct
        )
    
    def get_historico(self, days: int = 30) -> List[Dict]:
        """Retorna histórico do patrimônio"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        return [s for s in self.historico if s["date"] >= cutoff]
    
    def get_composicao(self) -> Dict:
        """Retorna composição do patrimônio (MT4 convertido para BRL)"""
        cotacao = get_cotacao_dolar_sync()
        total = self.get_total(cotacao)
        
        # MT4 em BRL
        mt4_brl = self.patrimonio.get("mt4_balance", 0) * cotacao
        
        if total == 0:
            return {
                "mt4": {"valor": 0, "valor_usd": 0, "percentual": 0, "cotacao": cotacao},
                "acoes": {"valor": 0, "percentual": 0},
                "fiis": {"valor": 0, "percentual": 0},
                "outros": {"valor": 0, "percentual": 0}
            }
        
        return {
            "mt4": {
                "valor": mt4_brl,
                "valor_usd": self.patrimonio.get("mt4_balance", 0),
                "percentual": (mt4_brl / total) * 100,
                "cotacao": cotacao
            },
            "acoes": {
                "valor": self.patrimonio.get("acoes_valor", 0),
                "percentual": (self.patrimonio.get("acoes_valor", 0) / total) * 100
            },
            "fiis": {
                "valor": self.patrimonio.get("fiis_valor", 0),
                "percentual": (self.patrimonio.get("fiis_valor", 0) / total) * 100
            },
            "outros": {
                "valor": self.patrimonio.get("outros", 0),
                "percentual": (self.patrimonio.get("outros", 0) / total) * 100
            }
        }


# Instância global
_patrimonio_service = None

def get_patrimonio_service() -> PatrimonioService:
    global _patrimonio_service
    if _patrimonio_service is None:
        _patrimonio_service = PatrimonioService()
    return _patrimonio_service
