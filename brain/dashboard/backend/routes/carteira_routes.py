"""
Rotas para Carteira de Investimentos (Ações e FIIs)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from services.carteira_service import get_carteira_service, TipoAtivo
from services.patrimonio_service import get_patrimonio_service

router = APIRouter(prefix="/api/carteira", tags=["Carteira"])


# ============ MODELS ============

class CompraInput(BaseModel):
    """Input para compra de ativo"""
    ticker: str
    tipo: str  # acao ou fii
    quantidade: int
    preco_unitario: float
    data: Optional[str] = None
    nome: Optional[str] = ""
    setor: Optional[str] = ""
    taxas: Optional[float] = 0
    observacao: Optional[str] = ""


class VendaInput(BaseModel):
    """Input para venda de ativo"""
    ticker: str
    tipo: str
    quantidade: int
    preco_unitario: float
    data: Optional[str] = None
    taxas: Optional[float] = 0
    observacao: Optional[str] = ""


class DividendoInput(BaseModel):
    """Input para registro de dividendo"""
    ticker: str
    tipo: str
    valor_por_cota: float
    data_pagamento: Optional[str] = None
    data_com: Optional[str] = None
    observacao: Optional[str] = ""


class SimularCompraInput(BaseModel):
    """Input para simulação de compra"""
    valor_investir: float
    preco_acao: float
    dividend_yield: float


class SimularVendaInput(BaseModel):
    """Input para simulação de venda"""
    ticker: str
    tipo: str
    preco_venda: float
    quantidade: Optional[int] = None


class AtualizarCotacaoInput(BaseModel):
    """Input para atualizar cotação"""
    ticker: str
    tipo: str
    preco_atual: float


# ============ ROTAS ============

@router.get("/resumo")
async def get_resumo(tipo: Optional[str] = None):
    """Retorna resumo da carteira"""
    service = get_carteira_service()
    resumo = service.get_resumo(tipo)
    
    # Atualizar patrimônio
    patrimonio = get_patrimonio_service()
    if tipo == TipoAtivo.ACAO or tipo is None:
        resumo_acoes = service.get_resumo(TipoAtivo.ACAO)
        patrimonio.update_acoes(
            resumo_acoes["valor_atual"],
            resumo_acoes["lucro_prejuizo"]
        )
    if tipo == TipoAtivo.FII or tipo is None:
        resumo_fiis = service.get_resumo(TipoAtivo.FII)
        patrimonio.update_fiis(
            resumo_fiis["valor_atual"],
            resumo_fiis["lucro_prejuizo"]
        )
    
    return {
        "success": True,
        "data": resumo
    }


@router.get("/ativos")
async def get_ativos(tipo: Optional[str] = None):
    """Retorna lista de ativos na carteira"""
    service = get_carteira_service()
    ativos = service.get_ativos(tipo)
    
    return {
        "success": True,
        "count": len(ativos),
        "data": ativos
    }


@router.get("/ativo/{tipo}/{ticker}")
async def get_ativo(tipo: str, ticker: str):
    """Retorna dados de um ativo específico"""
    service = get_carteira_service()
    ativo = service.get_ativo(ticker, tipo)
    
    if not ativo:
        raise HTTPException(status_code=404, detail=f"Ativo {ticker} não encontrado")
    
    return {
        "success": True,
        "data": ativo
    }


@router.post("/comprar")
async def comprar(data: CompraInput):
    """Registra compra de ativo"""
    service = get_carteira_service()
    result = service.comprar(
        ticker=data.ticker,
        tipo=data.tipo,
        quantidade=data.quantidade,
        preco_unitario=data.preco_unitario,
        data=data.data,
        nome=data.nome,
        setor=data.setor,
        taxas=data.taxas,
        observacao=data.observacao
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    # Atualizar patrimônio
    _sync_patrimonio()
    
    return result


@router.post("/vender")
async def vender(data: VendaInput):
    """Registra venda de ativo"""
    service = get_carteira_service()
    result = service.vender(
        ticker=data.ticker,
        tipo=data.tipo,
        quantidade=data.quantidade,
        preco_unitario=data.preco_unitario,
        data=data.data,
        taxas=data.taxas,
        observacao=data.observacao
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    # Atualizar patrimônio
    _sync_patrimonio()
    
    return result


@router.post("/dividendo")
async def registrar_dividendo(data: DividendoInput):
    """Registra recebimento de dividendo"""
    service = get_carteira_service()
    result = service.registrar_dividendo(
        ticker=data.ticker,
        tipo=data.tipo,
        valor_por_cota=data.valor_por_cota,
        data_pagamento=data.data_pagamento,
        data_com=data.data_com,
        observacao=data.observacao
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    # Atualizar patrimônio com dividendo
    patrimonio = get_patrimonio_service()
    patrimonio.add_dividendo(result["dividendo"]["valor_total"])
    
    return result


@router.post("/simular/compra")
async def simular_compra(data: SimularCompraInput):
    """Simula uma compra e calcula retornos esperados"""
    service = get_carteira_service()
    result = service.simular_compra(
        valor_investir=data.valor_investir,
        preco_acao=data.preco_acao,
        dividend_yield=data.dividend_yield
    )
    
    return {
        "success": True,
        "data": result
    }


@router.post("/simular/venda")
async def simular_venda(data: SimularVendaInput):
    """Simula uma venda e calcula lucro/prejuízo"""
    service = get_carteira_service()
    result = service.simular_venda(
        ticker=data.ticker,
        tipo=data.tipo,
        preco_venda=data.preco_venda,
        quantidade=data.quantidade
    )
    
    if not result.get("success", True) == False:
        return {
            "success": True,
            "data": result
        }
    
    raise HTTPException(status_code=400, detail=result["message"])


@router.post("/cotacao")
async def atualizar_cotacao(data: AtualizarCotacaoInput):
    """Atualiza cotação de um ativo"""
    service = get_carteira_service()
    service.atualizar_cotacao(
        ticker=data.ticker,
        tipo=data.tipo,
        preco_atual=data.preco_atual
    )
    
    # Atualizar patrimônio
    _sync_patrimonio()
    
    return {
        "success": True,
        "message": f"Cotação de {data.ticker} atualizada para R$ {data.preco_atual:.2f}"
    }


@router.get("/operacoes")
async def get_operacoes(ticker: Optional[str] = None, tipo: Optional[str] = None, limit: int = 50):
    """Retorna histórico de operações"""
    service = get_carteira_service()
    operacoes = service.get_operacoes(ticker, tipo, limit)
    
    return {
        "success": True,
        "count": len(operacoes),
        "data": operacoes
    }


@router.get("/dividendos")
async def get_dividendos(ticker: Optional[str] = None, ano: Optional[int] = None):
    """Retorna histórico de dividendos"""
    service = get_carteira_service()
    dividendos = service.get_dividendos(ticker, ano)
    
    total = sum(d.get("valor_total", 0) for d in dividendos)
    
    return {
        "success": True,
        "count": len(dividendos),
        "total": total,
        "data": dividendos
    }


@router.get("/dividendos/mensal")
async def get_dividendos_mensal(ano: Optional[int] = None):
    """Retorna dividendos agrupados por mês"""
    service = get_carteira_service()
    meses = service.get_dividendos_por_mes(ano)
    
    return {
        "success": True,
        "ano": ano or datetime.now().year,
        "data": meses
    }


@router.delete("/ativo/{tipo}/{ticker}")
async def excluir_ativo(tipo: str, ticker: str):
    """Remove um ativo da carteira"""
    service = get_carteira_service()
    result = service.excluir_ativo(ticker, tipo)
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    
    # Atualizar patrimônio
    _sync_patrimonio()
    
    return result


def _sync_patrimonio():
    """Sincroniza carteira com patrimônio"""
    carteira = get_carteira_service()
    patrimonio = get_patrimonio_service()
    
    resumo_acoes = carteira.get_resumo(TipoAtivo.ACAO)
    resumo_fiis = carteira.get_resumo(TipoAtivo.FII)
    
    patrimonio.update_acoes(
        resumo_acoes.get("valor_atual", resumo_acoes.get("total_investido", 0)),
        resumo_acoes.get("lucro_prejuizo", 0)
    )
    patrimonio.update_fiis(
        resumo_fiis.get("valor_atual", resumo_fiis.get("total_investido", 0)),
        resumo_fiis.get("lucro_prejuizo", 0)
    )
