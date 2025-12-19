"""
VIRTUS - API Routes para Portfólio e Brain de Dividendos
========================================================

Endpoints para:
- Gerenciar portfólio (compras, vendas, dividendos)
- Obter projeções e métricas
- Acessar inteligência do Brain
- Criar planos de ação
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

router = APIRouter(prefix="/api/dividend-portfolio", tags=["Dividend Portfolio & Brain"])


# ==================== MODELS ====================

class TransactionType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    JCP = "jcp"


class AddTransactionRequest(BaseModel):
    ticker: str = Field(..., description="Código da ação (ex: PETR4)")
    type: TransactionType = Field(..., description="Tipo de transação")
    date: str = Field(..., description="Data (YYYY-MM-DD)")
    shares: int = Field(..., gt=0, description="Quantidade de ações")
    price: float = Field(..., gt=0, description="Preço por ação")
    fees: float = Field(0.0, ge=0, description="Taxas/corretagem")
    notes: str = Field("", description="Observações")


class AddBuyRequest(BaseModel):
    ticker: str
    date: str
    shares: int = Field(..., gt=0)
    price: float = Field(..., gt=0)
    fees: float = Field(0.0, ge=0)
    notes: str = ""


class AddSellRequest(BaseModel):
    ticker: str
    date: str
    shares: int = Field(..., gt=0)
    price: float = Field(..., gt=0)
    fees: float = Field(0.0, ge=0)
    notes: str = ""


class AddDividendRequest(BaseModel):
    ticker: str
    date: str
    shares: int = Field(..., gt=0)
    dividend_per_share: float = Field(..., gt=0)
    notes: str = ""


class CreatePlanRequest(BaseModel):
    capital: float = Field(..., gt=0, description="Capital disponível")
    strategy: str = Field("hybrid", description="Estratégia: dividend_capture, buy_and_hold, income_focus, hybrid")
    duration_days: int = Field(30, ge=7, le=365)


class UpdateConfigRequest(BaseModel):
    config: Dict[str, Any]


# ==================== PORTFOLIO ENDPOINTS ====================

@router.get("/transactions")
async def get_transactions(
    ticker: Optional[str] = None,
    type: Optional[TransactionType] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500)
):
    """Lista transações do portfólio."""
    try:
        from services.dividend_portfolio_service import get_portfolio_service
        service = get_portfolio_service()
        
        transactions = service.get_transactions(
            ticker=ticker,
            type_filter=type,
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "transactions": [t.to_dict() for t in transactions[:limit]],
            "total": len(transactions),
            "filters": {
                "ticker": ticker,
                "type": type.value if type else None,
                "start_date": start_date,
                "end_date": end_date
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transactions")
async def add_transaction(request: AddTransactionRequest):
    """Adiciona uma transação ao portfólio."""
    try:
        from services.dividend_portfolio_service import get_portfolio_service, TransactionType as TType
        service = get_portfolio_service()
        
        transaction = service.add_transaction(
            ticker=request.ticker,
            type=TType(request.type.value),
            date=request.date,
            shares=request.shares,
            price=request.price,
            fees=request.fees,
            notes=request.notes
        )
        
        return {
            "success": True,
            "transaction": transaction.to_dict(),
            "message": f"Transação de {request.type.value} registrada para {request.ticker}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/buy")
async def add_buy(request: AddBuyRequest):
    """Registra uma compra de ações."""
    try:
        from services.dividend_portfolio_service import get_portfolio_service
        service = get_portfolio_service()
        
        transaction = service.add_buy(
            ticker=request.ticker,
            date=request.date,
            shares=request.shares,
            price=request.price,
            fees=request.fees,
            notes=request.notes
        )
        
        return {
            "success": True,
            "transaction": transaction.to_dict(),
            "message": f"Compra de {request.shares} ações de {request.ticker} registrada"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sell")
async def add_sell(request: AddSellRequest):
    """Registra uma venda de ações."""
    try:
        from services.dividend_portfolio_service import get_portfolio_service
        service = get_portfolio_service()
        
        transaction = service.add_sell(
            ticker=request.ticker,
            date=request.date,
            shares=request.shares,
            price=request.price,
            fees=request.fees,
            notes=request.notes
        )
        
        return {
            "success": True,
            "transaction": transaction.to_dict(),
            "message": f"Venda de {request.shares} ações de {request.ticker} registrada"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dividend")
async def add_dividend(request: AddDividendRequest):
    """Registra recebimento de dividendo."""
    try:
        from services.dividend_portfolio_service import get_portfolio_service
        service = get_portfolio_service()
        
        transaction = service.add_dividend_received(
            ticker=request.ticker,
            date=request.date,
            shares=request.shares,
            dividend_per_share=request.dividend_per_share,
            notes=request.notes
        )
        
        return {
            "success": True,
            "transaction": transaction.to_dict(),
            "message": f"Dividendo de {request.ticker} registrado: R$ {request.shares * request.dividend_per_share:.2f}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/transactions/{transaction_id}")
async def delete_transaction(transaction_id: str):
    """Remove uma transação."""
    try:
        from services.dividend_portfolio_service import get_portfolio_service
        service = get_portfolio_service()
        
        success = service.delete_transaction(transaction_id)
        
        if success:
            return {"success": True, "message": "Transação removida"}
        else:
            raise HTTPException(status_code=404, detail="Transação não encontrada")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions")
async def get_positions():
    """Retorna posições atuais do portfólio."""
    try:
        from services.dividend_portfolio_service import get_portfolio_service
        service = get_portfolio_service()
        
        positions = await service.get_positions()
        
        return {
            "positions": [
                {
                    "ticker": p.ticker,
                    "company_name": p.company_name,
                    "shares": p.shares,
                    "avg_price": p.avg_price,
                    "total_invested": p.total_invested,
                    "current_price": p.current_price,
                    "current_value": p.current_value,
                    "profit_loss": p.profit_loss,
                    "profit_loss_percent": p.profit_loss_percent,
                    "dividends_received": p.dividends_received,
                    "yield_on_cost": p.yield_on_cost,
                    "last_update": p.last_update
                }
                for p in positions
            ],
            "total_positions": len(positions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_portfolio_summary():
    """Retorna resumo do portfólio."""
    try:
        from services.dividend_portfolio_service import get_portfolio_service
        service = get_portfolio_service()
        
        summary = await service.get_portfolio_summary()
        
        return {
            "total_invested": summary.total_invested,
            "total_current_value": summary.total_current_value,
            "total_profit_loss": summary.total_profit_loss,
            "total_profit_loss_percent": summary.total_profit_loss_percent,
            "total_dividends_received": summary.total_dividends_received,
            "total_dividends_projected": summary.total_dividends_projected,
            "yield_on_cost": summary.yield_on_cost,
            "monthly_dividend_avg": summary.monthly_dividend_avg,
            "positions_count": summary.positions_count,
            "last_update": summary.last_update
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projections")
async def get_dividend_projections(days_ahead: int = Query(90, ge=1, le=365)):
    """Retorna projeção de dividendos baseado nas posições."""
    try:
        from services.dividend_portfolio_service import get_portfolio_service
        service = get_portfolio_service()
        
        projections = await service.get_dividend_projections(days_ahead)
        
        total = sum(p.total_expected for p in projections)
        
        return {
            "projections": [
                {
                    "ticker": p.ticker,
                    "company_name": p.company_name,
                    "shares": p.shares,
                    "ex_date": p.ex_date,
                    "payment_date": p.payment_date,
                    "dividend_per_share": p.dividend_per_share,
                    "total_expected": p.total_expected,
                    "status": p.status
                }
                for p in projections
            ],
            "total_projected": total,
            "days_ahead": days_ahead
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evolution")
async def get_evolution_data(period: str = Query("1Y", regex="^(1M|3M|6M|1Y|ALL)$")):
    """Retorna dados para gráfico de evolução do patrimônio."""
    try:
        from services.dividend_portfolio_service import get_portfolio_service
        service = get_portfolio_service()
        
        data = await service.get_evolution_data(period)
        
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_portfolio_history(days: int = Query(365, ge=1, le=1825)):
    """Retorna histórico do portfólio."""
    try:
        from services.dividend_portfolio_service import get_portfolio_service
        service = get_portfolio_service()
        
        history = service.get_portfolio_history(days)
        
        return {
            "history": history,
            "period_days": days
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== BRAIN ENDPOINTS ====================

@router.get("/brain/config")
async def get_brain_config():
    """Retorna configuração do Brain."""
    try:
        from services.dividend_brain import get_dividend_brain
        brain = get_dividend_brain()
        
        return brain.get_config()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/brain/config")
async def update_brain_config(request: UpdateConfigRequest):
    """Atualiza configuração do Brain."""
    try:
        from services.dividend_brain import get_dividend_brain
        brain = get_dividend_brain()
        
        config = brain.update_config(request.config)
        
        return {
            "success": True,
            "config": config
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/brain/opportunities")
async def get_opportunities(capital: float = Query(10000, gt=0)):
    """Analisa oportunidades de investimento."""
    try:
        from services.dividend_brain import get_dividend_brain
        brain = get_dividend_brain()
        
        signals = await brain.analyze_opportunities(capital)
        
        return {
            "opportunities": [
                {
                    "id": s.id,
                    "ticker": s.ticker,
                    "company_name": s.company_name,
                    "signal_type": s.signal_type,
                    "score": s.score,
                    "current_price": s.current_price,
                    "target_entry": s.target_entry,
                    "target_exit": s.target_exit,
                    "stop_loss": s.stop_loss,
                    "suggested_buy_date": s.suggested_buy_date,
                    "ex_date": s.ex_date,
                    "suggested_sell_date": s.suggested_sell_date,
                    "expected_dividend": s.expected_dividend,
                    "dividend_yield": s.dividend_yield,
                    "expected_return": s.expected_return,
                    "risk_level": s.risk_level,
                    "reason": s.reason,
                    "valid_until": s.valid_until
                }
                for s in signals
            ],
            "total": len(signals),
            "capital": capital,
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/brain/signals")
async def get_active_signals():
    """Retorna sinais ativos."""
    try:
        from services.dividend_brain import get_dividend_brain
        brain = get_dividend_brain()
        
        signals = brain.get_active_signals()
        
        return {
            "signals": signals,
            "total": len(signals)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/brain/recommendations")
async def get_recommendations(capital: float = Query(10000, gt=0)):
    """Gera recomendações personalizadas."""
    try:
        from services.dividend_brain import get_dividend_brain
        brain = get_dividend_brain()
        
        recommendations = await brain.get_recommendations(capital)
        
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/brain/plan")
async def create_action_plan(request: CreatePlanRequest):
    """Cria plano de ação personalizado."""
    try:
        from services.dividend_brain import get_dividend_brain, Strategy
        brain = get_dividend_brain()
        
        strategy = Strategy(request.strategy)
        plan = await brain.create_action_plan(
            capital=request.capital,
            strategy=strategy,
            duration_days=request.duration_days
        )
        
        return {
            "success": True,
            "plan": {
                "id": plan.id,
                "name": plan.name,
                "strategy": plan.strategy.value,
                "available_capital": plan.available_capital,
                "allocated_capital": plan.allocated_capital,
                "actions": plan.actions,
                "expected_dividends": plan.expected_dividends,
                "expected_return": plan.expected_return,
                "start_date": plan.start_date,
                "end_date": plan.end_date,
                "status": plan.status,
                "created_at": plan.created_at
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/brain/plans")
async def get_action_plans():
    """Retorna planos de ação."""
    try:
        from services.dividend_brain import get_dividend_brain
        brain = get_dividend_brain()
        
        plans = brain.get_action_plans()
        
        return {
            "plans": plans,
            "total": len(plans)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/brain/alerts")
async def get_alerts():
    """Retorna alertas gerados pelo Brain."""
    try:
        from services.dividend_brain import get_dividend_brain
        brain = get_dividend_brain()
        
        # Verifica novos alertas
        alerts = await brain.check_alerts()
        
        return {
            "alerts": alerts,
            "total": len(alerts)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== SETTINGS ====================

@router.get("/settings")
async def get_settings():
    """Retorna configurações do portfólio."""
    try:
        from services.dividend_portfolio_service import get_portfolio_service
        service = get_portfolio_service()
        
        return service.get_settings()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/settings")
async def update_settings(settings: Dict[str, Any]):
    """Atualiza configurações do portfólio."""
    try:
        from services.dividend_portfolio_service import get_portfolio_service
        service = get_portfolio_service()
        
        updated = service.update_settings(settings)
        
        return {
            "success": True,
            "settings": updated
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
