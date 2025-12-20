"""
Rotas para Gestão Patrimonial
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from dataclasses import asdict

from services.patrimonio_service import get_patrimonio_service

router = APIRouter(prefix="/api/patrimonio", tags=["Patrimônio"])


class AtualizarOutrosInput(BaseModel):
    """Input para atualizar outros ativos"""
    valor: float


@router.get("/resumo")
async def get_resumo():
    """Retorna resumo do patrimônio"""
    service = get_patrimonio_service()
    resumo = service.get_resumo()
    
    return {
        "success": True,
        "data": asdict(resumo)
    }


@router.get("/composicao")
async def get_composicao():
    """Retorna composição do patrimônio"""
    service = get_patrimonio_service()
    composicao = service.get_composicao()
    
    return {
        "success": True,
        "data": composicao
    }


@router.get("/historico")
async def get_historico(days: int = 30):
    """Retorna histórico do patrimônio"""
    service = get_patrimonio_service()
    historico = service.get_historico(days)
    
    return {
        "success": True,
        "days": days,
        "data": historico
    }


@router.post("/outros")
async def atualizar_outros(data: AtualizarOutrosInput):
    """Atualiza valor de outros ativos"""
    service = get_patrimonio_service()
    service.update_outros(data.valor)
    
    return {
        "success": True,
        "message": f"Outros ativos atualizado para R$ {data.valor:.2f}"
    }


@router.post("/snapshot")
async def criar_snapshot():
    """Força criação de snapshot do patrimônio"""
    service = get_patrimonio_service()
    service._save_snapshot()
    
    return {
        "success": True,
        "message": "Snapshot criado"
    }
