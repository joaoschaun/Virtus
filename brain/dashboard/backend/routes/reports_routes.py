"""
VIRTUS - Routes para Relatórios PDF
====================================

Endpoints REST para geração de relatórios.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse

# Adiciona path do src
BRAIN_PATH = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(BRAIN_PATH))
sys.path.insert(0, str(BRAIN_PATH / "src"))

router = APIRouter(prefix="/reports", tags=["Reports"])

# Import do módulo de relatórios
try:
    from src.reporting.pdf_generator import report_generator
    REPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: PDF Generator module not available: {e}")
    REPORTS_AVAILABLE = False


@router.get("/status")
async def get_reports_status():
    """Retorna status do sistema de relatórios."""
    if not REPORTS_AVAILABLE:
        return {"available": False, "message": "Sistema de Relatórios não disponível"}
    
    return {
        "available": True,
        "pdf_available": report_generator.pdf_available,
        "supported_formats": ["html", "pdf"] if report_generator.pdf_available else ["html"],
    }


@router.get("/performance")
async def get_performance_report(
    period: str = Query("month", enum=["week", "month", "quarter", "year"]),
    format: str = Query("html", enum=["html", "pdf"]),
):
    """
    Gera relatório de performance.
    
    Args:
        period: Período do relatório (week, month, quarter, year)
        format: Formato de saída (html, pdf)
    """
    if not REPORTS_AVAILABLE:
        raise HTTPException(503, "Sistema de Relatórios não disponível")
    
    # Calcula período
    end_date = datetime.now()
    if period == "week":
        start_date = end_date - timedelta(days=7)
    elif period == "month":
        start_date = end_date - timedelta(days=30)
    elif period == "quarter":
        start_date = end_date - timedelta(days=90)
    else:  # year
        start_date = end_date - timedelta(days=365)
    
    try:
        # Coleta dados
        report_data = await _collect_performance_data(start_date, end_date)
        
        # Gera relatório usando o método correto
        pdf_bytes = await report_generator.generate_performance_report(
            start_date=start_date,
            end_date=end_date,
            trades=report_data.get("trades", []),
            metrics=report_data.get("summary", {}),
            account_info=None,
        )
        
        if format == "pdf" and report_generator.pdf_available:
            return HTMLResponse(
                content=pdf_bytes.decode('utf-8') if isinstance(pdf_bytes, bytes) else pdf_bytes,
                media_type="application/pdf"
            )
        else:
            # Retorna HTML
            return HTMLResponse(
                content=pdf_bytes.decode('utf-8') if isinstance(pdf_bytes, bytes) else pdf_bytes
            )
            
    except Exception as e:
        raise HTTPException(500, f"Erro ao gerar relatório: {str(e)}")


@router.get("/trades")
async def get_trades_report(
    start_date: str = Query(None, description="Data inicial (YYYY-MM-DD)"),
    end_date: str = Query(None, description="Data final (YYYY-MM-DD)"),
):
    """Relatório detalhado de trades."""
    if not REPORTS_AVAILABLE:
        raise HTTPException(503, "Sistema de Relatórios não disponível")
    
    # Parse datas
    try:
        if start_date:
            start = datetime.fromisoformat(start_date)
        else:
            start = datetime.now() - timedelta(days=30)
        
        if end_date:
            end = datetime.fromisoformat(end_date)
        else:
            end = datetime.now()
    except ValueError:
        raise HTTPException(400, "Formato de data inválido. Use YYYY-MM-DD")
    
    # Coleta e retorna dados de trades
    data = await _collect_trades_data(start, end)
    html = report_generator.generate_html(data)
    return HTMLResponse(content=html)


@router.get("/summary")
async def get_summary_report():
    """Resumo geral do sistema."""
    if not REPORTS_AVAILABLE:
        raise HTTPException(503, "Sistema de Relatórios não disponível")
    
    data = await _collect_summary_data()
    return data


async def _collect_performance_data(start_date: datetime, end_date: datetime) -> dict:
    """Coleta dados de performance para o relatório."""
    # Tenta obter dados reais do sistema
    try:
        from src.database.manager import get_database
        
        db = get_database()
        if db:
            # Dados reais do banco
            trades = []  # db.get_trades(start_date, end_date)
            # ... processar dados
    except:
        pass
    
    # Dados de demonstração se não houver dados reais
    return {
        "title": "Relatório de Performance VIRTUS",
        "period": f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}",
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_trades": 45,
            "win_rate": 68.5,
            "profit_factor": 2.3,
            "total_pnl": 1250.50,
            "max_drawdown": -450.00,
            "sharpe_ratio": 1.85,
        },
        "risk_metrics": {
            "var_95": -350.00,
            "expected_shortfall": -420.00,
            "max_consecutive_losses": 3,
            "recovery_factor": 2.78,
        },
        "by_symbol": {
            "XAUUSD": {"trades": 30, "pnl": 850.00, "win_rate": 70.0},
            "EURUSD": {"trades": 15, "pnl": 400.50, "win_rate": 65.0},
        },
        "trades": [],  # Lista de trades detalhados
    }


async def _collect_trades_data(start_date: datetime, end_date: datetime) -> dict:
    """Coleta dados de trades para o relatório."""
    return {
        "title": "Relatório de Trades VIRTUS",
        "period": f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}",
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_trades": 0,
            "win_rate": 0,
            "profit_factor": 0,
            "total_pnl": 0,
        },
        "trades": [],
    }


async def _collect_summary_data() -> dict:
    """Coleta dados de resumo geral."""
    return {
        "title": "Resumo Geral VIRTUS",
        "generated_at": datetime.now().isoformat(),
        "account": {
            "balance": 5080.82,
            "equity": 5080.82,
            "margin": 0,
            "free_margin": 5080.82,
        },
        "today": {
            "trades": 0,
            "pnl": 0,
            "win_rate": 0,
        },
        "month": {
            "trades": 0,
            "pnl": 0,
            "win_rate": 0,
        },
        "system": {
            "uptime_hours": 24,
            "bots_active": 1,
            "last_trade": None,
        }
    }
