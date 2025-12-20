"""
Serviço de Carteira de Investimentos
Gerencia Ações e FIIs com compra/venda/dividendos
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict, field
from pathlib import Path
from enum import Enum


class TipoAtivo(str, Enum):
    ACAO = "acao"
    FII = "fii"


class TipoOperacao(str, Enum):
    COMPRA = "compra"
    VENDA = "venda"
    DIVIDENDO = "dividendo"


@dataclass
class Operacao:
    """Operação de compra/venda/dividendo"""
    id: str
    tipo: str  # compra, venda, dividendo
    data: str
    quantidade: int
    preco_unitario: float
    valor_total: float
    taxas: float = 0
    observacao: str = ""


@dataclass 
class Ativo:
    """Ativo (ação ou FII)"""
    ticker: str
    tipo: str  # acao ou fii
    nome: str
    setor: str = ""
    quantidade: int = 0
    preco_medio: float = 0
    valor_investido: float = 0
    valor_atual: float = 0
    lucro_prejuizo: float = 0
    lucro_prejuizo_pct: float = 0
    dividendos_recebidos: float = 0
    yield_on_cost: float = 0
    operacoes: List[Dict] = field(default_factory=list)
    

@dataclass
class CarteiraResumo:
    """Resumo da carteira"""
    total_investido: float
    valor_atual: float
    lucro_prejuizo: float
    lucro_prejuizo_pct: float
    dividendos_total: float
    quantidade_ativos: int


class CarteiraService:
    """Serviço para gestão de carteira de ações e FIIs"""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent.parent / "data" / "carteira"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.acoes_file = self.data_dir / "acoes.json"
        self.fiis_file = self.data_dir / "fiis.json"
        self.operacoes_file = self.data_dir / "operacoes.json"
        self.dividendos_file = self.data_dir / "dividendos.json"
        
        self._load_data()
    
    def _load_data(self):
        """Carrega dados da carteira"""
        # Carregar ações
        if self.acoes_file.exists():
            with open(self.acoes_file, 'r', encoding='utf-8') as f:
                self.acoes = json.load(f)
        else:
            self.acoes = {}
        
        # Carregar FIIs
        if self.fiis_file.exists():
            with open(self.fiis_file, 'r', encoding='utf-8') as f:
                self.fiis = json.load(f)
        else:
            self.fiis = {}
        
        # Carregar operações
        if self.operacoes_file.exists():
            with open(self.operacoes_file, 'r', encoding='utf-8') as f:
                self.operacoes = json.load(f)
        else:
            self.operacoes = []
        
        # Carregar dividendos
        if self.dividendos_file.exists():
            with open(self.dividendos_file, 'r', encoding='utf-8') as f:
                self.dividendos = json.load(f)
        else:
            self.dividendos = []
    
    def _save_data(self):
        """Salva todos os dados"""
        with open(self.acoes_file, 'w', encoding='utf-8') as f:
            json.dump(self.acoes, f, indent=2, ensure_ascii=False)
        
        with open(self.fiis_file, 'w', encoding='utf-8') as f:
            json.dump(self.fiis, f, indent=2, ensure_ascii=False)
        
        with open(self.operacoes_file, 'w', encoding='utf-8') as f:
            json.dump(self.operacoes, f, indent=2, ensure_ascii=False)
        
        with open(self.dividendos_file, 'w', encoding='utf-8') as f:
            json.dump(self.dividendos, f, indent=2, ensure_ascii=False)
    
    def _get_storage(self, tipo: str) -> Dict:
        """Retorna o storage correto baseado no tipo"""
        return self.acoes if tipo == TipoAtivo.ACAO else self.fiis
    
    def _generate_id(self) -> str:
        """Gera ID único para operação"""
        return datetime.now().strftime("%Y%m%d%H%M%S%f")
    
    def comprar(
        self,
        ticker: str,
        tipo: str,
        quantidade: int,
        preco_unitario: float,
        data: str = None,
        nome: str = "",
        setor: str = "",
        taxas: float = 0,
        observacao: str = ""
    ) -> Dict:
        """Registra compra de ativo"""
        storage = self._get_storage(tipo)
        ticker = ticker.upper()
        
        if data is None:
            data = datetime.now().strftime("%Y-%m-%d")
        
        valor_total = quantidade * preco_unitario + taxas
        
        # Criar operação
        operacao = {
            "id": self._generate_id(),
            "ticker": ticker,
            "tipo_ativo": tipo,
            "tipo_operacao": TipoOperacao.COMPRA,
            "data": data,
            "quantidade": quantidade,
            "preco_unitario": preco_unitario,
            "valor_total": valor_total,
            "taxas": taxas,
            "observacao": observacao
        }
        self.operacoes.append(operacao)
        
        # Atualizar ou criar ativo
        if ticker not in storage:
            storage[ticker] = {
                "ticker": ticker,
                "tipo": tipo,
                "nome": nome or ticker,
                "setor": setor,
                "quantidade": 0,
                "preco_medio": 0,
                "valor_investido": 0,
                "dividendos_recebidos": 0,
                "operacoes": []
            }
        
        ativo = storage[ticker]
        
        # Calcular novo preço médio
        valor_anterior = ativo["quantidade"] * ativo["preco_medio"]
        quantidade_nova = ativo["quantidade"] + quantidade
        
        if quantidade_nova > 0:
            ativo["preco_medio"] = (valor_anterior + valor_total) / quantidade_nova
        
        ativo["quantidade"] = quantidade_nova
        ativo["valor_investido"] = ativo["quantidade"] * ativo["preco_medio"]
        ativo["operacoes"].append(operacao["id"])
        
        if nome:
            ativo["nome"] = nome
        if setor:
            ativo["setor"] = setor
        
        self._save_data()
        
        return {
            "success": True,
            "message": f"Compra de {quantidade} {ticker} registrada",
            "operacao": operacao,
            "ativo": ativo
        }
    
    def vender(
        self,
        ticker: str,
        tipo: str,
        quantidade: int,
        preco_unitario: float,
        data: str = None,
        taxas: float = 0,
        observacao: str = ""
    ) -> Dict:
        """Registra venda de ativo"""
        storage = self._get_storage(tipo)
        ticker = ticker.upper()
        
        if ticker not in storage:
            return {
                "success": False,
                "message": f"Ativo {ticker} não encontrado na carteira"
            }
        
        ativo = storage[ticker]
        
        if quantidade > ativo["quantidade"]:
            return {
                "success": False,
                "message": f"Quantidade insuficiente. Disponível: {ativo['quantidade']}"
            }
        
        if data is None:
            data = datetime.now().strftime("%Y-%m-%d")
        
        valor_venda = quantidade * preco_unitario - taxas
        custo_medio = quantidade * ativo["preco_medio"]
        lucro_prejuizo = valor_venda - custo_medio
        lucro_prejuizo_pct = (lucro_prejuizo / custo_medio) * 100 if custo_medio > 0 else 0
        
        # Criar operação
        operacao = {
            "id": self._generate_id(),
            "ticker": ticker,
            "tipo_ativo": tipo,
            "tipo_operacao": TipoOperacao.VENDA,
            "data": data,
            "quantidade": quantidade,
            "preco_unitario": preco_unitario,
            "valor_total": valor_venda,
            "taxas": taxas,
            "custo_medio": custo_medio,
            "lucro_prejuizo": lucro_prejuizo,
            "lucro_prejuizo_pct": lucro_prejuizo_pct,
            "observacao": observacao
        }
        self.operacoes.append(operacao)
        
        # Atualizar ativo
        ativo["quantidade"] -= quantidade
        ativo["valor_investido"] = ativo["quantidade"] * ativo["preco_medio"]
        ativo["operacoes"].append(operacao["id"])
        
        # Remover ativo se zerou
        if ativo["quantidade"] == 0:
            # Manter histórico mas marcar como zerado
            ativo["preco_medio"] = 0
        
        self._save_data()
        
        return {
            "success": True,
            "message": f"Venda de {quantidade} {ticker} registrada",
            "lucro_prejuizo": lucro_prejuizo,
            "lucro_prejuizo_pct": lucro_prejuizo_pct,
            "resultado": "LUCRO" if lucro_prejuizo > 0 else "PREJUÍZO" if lucro_prejuizo < 0 else "EMPATE",
            "operacao": operacao,
            "ativo": ativo
        }
    
    def registrar_dividendo(
        self,
        ticker: str,
        tipo: str,
        valor_por_cota: float,
        data_pagamento: str = None,
        data_com: str = None,
        observacao: str = ""
    ) -> Dict:
        """Registra recebimento de dividendo"""
        storage = self._get_storage(tipo)
        ticker = ticker.upper()
        
        if ticker not in storage:
            return {
                "success": False,
                "message": f"Ativo {ticker} não encontrado na carteira"
            }
        
        ativo = storage[ticker]
        
        if data_pagamento is None:
            data_pagamento = datetime.now().strftime("%Y-%m-%d")
        
        valor_total = ativo["quantidade"] * valor_por_cota
        
        # Criar registro de dividendo
        dividendo = {
            "id": self._generate_id(),
            "ticker": ticker,
            "tipo_ativo": tipo,
            "data_pagamento": data_pagamento,
            "data_com": data_com,
            "quantidade": ativo["quantidade"],
            "valor_por_cota": valor_por_cota,
            "valor_total": valor_total,
            "observacao": observacao
        }
        self.dividendos.append(dividendo)
        
        # Atualizar ativo
        ativo["dividendos_recebidos"] = ativo.get("dividendos_recebidos", 0) + valor_total
        
        # Calcular yield on cost
        if ativo["valor_investido"] > 0:
            ativo["yield_on_cost"] = (ativo["dividendos_recebidos"] / ativo["valor_investido"]) * 100
        
        # Criar operação
        operacao = {
            "id": self._generate_id(),
            "ticker": ticker,
            "tipo_ativo": tipo,
            "tipo_operacao": TipoOperacao.DIVIDENDO,
            "data": data_pagamento,
            "quantidade": ativo["quantidade"],
            "preco_unitario": valor_por_cota,
            "valor_total": valor_total,
            "taxas": 0,
            "observacao": observacao
        }
        self.operacoes.append(operacao)
        ativo["operacoes"].append(operacao["id"])
        
        self._save_data()
        
        return {
            "success": True,
            "message": f"Dividendo de {ticker} registrado: R$ {valor_total:.2f}",
            "dividendo": dividendo,
            "ativo": ativo
        }
    
    def calcular_dividendo_esperado(
        self,
        ticker: str,
        tipo: str,
        quantidade: int,
        dividend_yield: float
    ) -> Dict:
        """Calcula dividendo esperado para uma quantidade"""
        # Buscar preço atual (simplificado - pode integrar com API)
        storage = self._get_storage(tipo)
        ticker = ticker.upper()
        
        if ticker in storage:
            preco_medio = storage[ticker]["preco_medio"]
        else:
            preco_medio = 0
        
        valor_investido = quantidade * preco_medio
        dividendo_anual_esperado = valor_investido * (dividend_yield / 100)
        dividendo_mensal_esperado = dividendo_anual_esperado / 12
        
        return {
            "ticker": ticker,
            "quantidade": quantidade,
            "valor_investido": valor_investido,
            "dividend_yield": dividend_yield,
            "dividendo_anual_esperado": dividendo_anual_esperado,
            "dividendo_mensal_esperado": dividendo_mensal_esperado
        }
    
    def simular_compra(
        self,
        valor_investir: float,
        preco_acao: float,
        dividend_yield: float
    ) -> Dict:
        """Simula uma compra e calcula retornos esperados"""
        quantidade = int(valor_investir / preco_acao)
        valor_real = quantidade * preco_acao
        sobra = valor_investir - valor_real
        
        dividendo_anual = valor_real * (dividend_yield / 100)
        dividendo_mensal = dividendo_anual / 12
        
        return {
            "valor_investir": valor_investir,
            "preco_acao": preco_acao,
            "quantidade_comprar": quantidade,
            "valor_real_investido": valor_real,
            "sobra": sobra,
            "dividend_yield": dividend_yield,
            "dividendo_anual_esperado": dividendo_anual,
            "dividendo_mensal_esperado": dividendo_mensal,
            "payback_anos": valor_real / dividendo_anual if dividendo_anual > 0 else 0
        }
    
    def simular_venda(
        self,
        ticker: str,
        tipo: str,
        preco_venda: float,
        quantidade: int = None
    ) -> Dict:
        """Simula uma venda e calcula lucro/prejuízo"""
        storage = self._get_storage(tipo)
        ticker = ticker.upper()
        
        if ticker not in storage:
            return {
                "success": False,
                "message": f"Ativo {ticker} não encontrado"
            }
        
        ativo = storage[ticker]
        
        if quantidade is None:
            quantidade = ativo["quantidade"]
        
        custo = quantidade * ativo["preco_medio"]
        valor_venda = quantidade * preco_venda
        lucro_prejuizo = valor_venda - custo
        lucro_prejuizo_pct = (lucro_prejuizo / custo) * 100 if custo > 0 else 0
        
        # Incluir dividendos recebidos no retorno total
        dividendos_proporcional = (ativo["dividendos_recebidos"] * quantidade / ativo["quantidade"]) if ativo["quantidade"] > 0 else 0
        retorno_total = lucro_prejuizo + dividendos_proporcional
        retorno_total_pct = (retorno_total / custo) * 100 if custo > 0 else 0
        
        return {
            "ticker": ticker,
            "quantidade": quantidade,
            "preco_medio": ativo["preco_medio"],
            "preco_venda": preco_venda,
            "custo_total": custo,
            "valor_venda": valor_venda,
            "lucro_prejuizo": lucro_prejuizo,
            "lucro_prejuizo_pct": lucro_prejuizo_pct,
            "resultado": "LUCRO" if lucro_prejuizo > 0 else "PREJUÍZO" if lucro_prejuizo < 0 else "EMPATE",
            "dividendos_recebidos": dividendos_proporcional,
            "retorno_total": retorno_total,
            "retorno_total_pct": retorno_total_pct
        }
    
    def atualizar_cotacao(self, ticker: str, tipo: str, preco_atual: float):
        """Atualiza cotação de um ativo"""
        storage = self._get_storage(tipo)
        ticker = ticker.upper()
        
        if ticker in storage:
            ativo = storage[ticker]
            ativo["preco_atual"] = preco_atual
            ativo["valor_atual"] = ativo["quantidade"] * preco_atual
            custo = ativo["quantidade"] * ativo["preco_medio"]
            ativo["lucro_prejuizo"] = ativo["valor_atual"] - custo
            ativo["lucro_prejuizo_pct"] = (ativo["lucro_prejuizo"] / custo * 100) if custo > 0 else 0
            self._save_data()
    
    def get_ativo(self, ticker: str, tipo: str) -> Optional[Dict]:
        """Retorna dados de um ativo"""
        storage = self._get_storage(tipo)
        return storage.get(ticker.upper())
    
    def get_ativos(self, tipo: str = None) -> List[Dict]:
        """Retorna lista de ativos"""
        ativos = []
        
        if tipo is None or tipo == TipoAtivo.ACAO:
            for ticker, data in self.acoes.items():
                if data["quantidade"] > 0:
                    ativos.append({**data, "tipo": TipoAtivo.ACAO})
        
        if tipo is None or tipo == TipoAtivo.FII:
            for ticker, data in self.fiis.items():
                if data["quantidade"] > 0:
                    ativos.append({**data, "tipo": TipoAtivo.FII})
        
        return ativos
    
    def get_resumo(self, tipo: str = None) -> Dict:
        """Retorna resumo da carteira"""
        ativos = self.get_ativos(tipo)
        
        total_investido = sum(a.get("valor_investido", 0) for a in ativos)
        valor_atual = sum(a.get("valor_atual", a.get("valor_investido", 0)) for a in ativos)
        lucro_prejuizo = valor_atual - total_investido
        lucro_prejuizo_pct = (lucro_prejuizo / total_investido * 100) if total_investido > 0 else 0
        dividendos_total = sum(a.get("dividendos_recebidos", 0) for a in ativos)
        
        return {
            "total_investido": total_investido,
            "valor_atual": valor_atual,
            "lucro_prejuizo": lucro_prejuizo,
            "lucro_prejuizo_pct": lucro_prejuizo_pct,
            "dividendos_total": dividendos_total,
            "quantidade_ativos": len(ativos),
            "retorno_total": lucro_prejuizo + dividendos_total,
            "retorno_total_pct": ((lucro_prejuizo + dividendos_total) / total_investido * 100) if total_investido > 0 else 0
        }
    
    def get_operacoes(self, ticker: str = None, tipo: str = None, limit: int = 50) -> List[Dict]:
        """Retorna histórico de operações"""
        ops = self.operacoes.copy()
        
        if ticker:
            ops = [o for o in ops if o.get("ticker", "").upper() == ticker.upper()]
        
        if tipo:
            ops = [o for o in ops if o.get("tipo_ativo") == tipo]
        
        # Ordenar por data (mais recente primeiro)
        ops = sorted(ops, key=lambda x: x.get("data", ""), reverse=True)
        
        return ops[:limit]
    
    def get_dividendos(self, ticker: str = None, ano: int = None) -> List[Dict]:
        """Retorna histórico de dividendos"""
        divs = self.dividendos.copy()
        
        if ticker:
            divs = [d for d in divs if d.get("ticker", "").upper() == ticker.upper()]
        
        if ano:
            divs = [d for d in divs if d.get("data_pagamento", "").startswith(str(ano))]
        
        # Ordenar por data
        divs = sorted(divs, key=lambda x: x.get("data_pagamento", ""), reverse=True)
        
        return divs
    
    def get_dividendos_por_mes(self, ano: int = None) -> Dict:
        """Retorna dividendos agrupados por mês"""
        if ano is None:
            ano = datetime.now().year
        
        meses = {f"{ano}-{m:02d}": 0 for m in range(1, 13)}
        
        for div in self.dividendos:
            data = div.get("data_pagamento", "")
            if data.startswith(str(ano)):
                mes = data[:7]
                if mes in meses:
                    meses[mes] += div.get("valor_total", 0)
        
        return meses
    
    def excluir_ativo(self, ticker: str, tipo: str) -> Dict:
        """Remove um ativo da carteira"""
        storage = self._get_storage(tipo)
        ticker = ticker.upper()
        
        if ticker in storage:
            del storage[ticker]
            self._save_data()
            return {"success": True, "message": f"Ativo {ticker} removido"}
        
        return {"success": False, "message": f"Ativo {ticker} não encontrado"}


# Instância global
_carteira_service = None

def get_carteira_service() -> CarteiraService:
    global _carteira_service
    if _carteira_service is None:
        _carteira_service = CarteiraService()
    return _carteira_service
