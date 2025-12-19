"""
VIRTUS - Gerador de Relatórios PDF
===================================

Gera relatórios de performance em PDF para download.
"""

import io
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger("virtus.reports")


@dataclass
class ReportConfig:
    """Configuração do relatório."""
    title: str = "VIRTUS Trading Report"
    subtitle: str = "Performance Analysis"
    logo_path: Optional[str] = None
    footer_text: str = "VIRTUS Trading System - Confidential"
    
    # Seções a incluir
    include_summary: bool = True
    include_trades: bool = True
    include_charts: bool = True
    include_risk_metrics: bool = True
    include_daily_breakdown: bool = True


class PDFReportGenerator:
    """
    Gerador de relatórios PDF.
    
    Uso:
        generator = PDFReportGenerator()
        pdf_bytes = await generator.generate_performance_report(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            trades=trades_list,
            metrics=metrics_dict
        )
    """
    
    def __init__(self, config: Optional[ReportConfig] = None):
        self.config = config or ReportConfig()
        self._ensure_dependencies()
    
    @property
    def pdf_available(self) -> bool:
        """Retorna se PDF está disponível."""
        return self._reportlab_available
    
    def _ensure_dependencies(self):
        """Verifica se dependências estão instaladas."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate
            self._reportlab_available = True
        except ImportError:
            self._reportlab_available = False
            logger.warning("reportlab não instalado. Usando gerador HTML alternativo.")
    
    async def generate_performance_report(
        self,
        start_date: datetime,
        end_date: datetime,
        trades: List[Dict],
        metrics: Dict[str, Any],
        account_info: Optional[Dict] = None,
    ) -> bytes:
        """Gera relatório de performance em PDF."""
        if self._reportlab_available:
            return self._generate_pdf(start_date, end_date, trades, metrics, account_info)
        else:
            return self._generate_html(start_date, end_date, trades, metrics, account_info)
    
    def _generate_pdf(
        self,
        start_date: datetime,
        end_date: datetime,
        trades: List[Dict],
        metrics: Dict[str, Any],
        account_info: Optional[Dict],
    ) -> bytes:
        """Gera PDF usando reportlab."""
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch, cm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            PageBreak, Image
        )
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=1*cm,
            leftMargin=1*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )
        
        styles = getSampleStyleSheet()
        
        # Estilos customizados
        styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1a1a2e'),
        ))
        
        styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=styles['Heading2'],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#16213e'),
        ))
        
        styles.add(ParagraphStyle(
            name='MetricValue',
            parent=styles['Normal'],
            fontSize=18,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#0f3460'),
        ))
        
        elements = []
        
        # === HEADER ===
        elements.append(Paragraph(self.config.title, styles['CustomTitle']))
        elements.append(Paragraph(
            f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}",
            styles['Normal']
        ))
        elements.append(Spacer(1, 20))
        
        # === RESUMO ===
        if self.config.include_summary:
            elements.append(Paragraph("📊 Resumo de Performance", styles['SectionHeader']))
            
            summary_data = [
                ["Métrica", "Valor"],
                ["Total de Trades", str(metrics.get('total_trades', 0))],
                ["Win Rate", f"{metrics.get('win_rate', 0):.1f}%"],
                ["Profit Factor", f"{metrics.get('profit_factor', 0):.2f}"],
                ["Lucro Total", f"${metrics.get('total_profit', 0):,.2f}"],
                ["Lucro Médio", f"${metrics.get('avg_profit', 0):,.2f}"],
                ["Maior Ganho", f"${metrics.get('max_profit', 0):,.2f}"],
                ["Maior Perda", f"${metrics.get('max_loss', 0):,.2f}"],
                ["Drawdown Máximo", f"{metrics.get('max_drawdown', 0):.2f}%"],
            ]
            
            summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f5f5f5')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dddddd')),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('TOPPADDING', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ]))
            
            elements.append(summary_table)
            elements.append(Spacer(1, 20))
        
        # === MÉTRICAS DE RISCO ===
        if self.config.include_risk_metrics:
            elements.append(Paragraph("⚠️ Métricas de Risco", styles['SectionHeader']))
            
            risk_data = [
                ["Métrica", "Valor", "Status"],
                ["Sharpe Ratio", f"{metrics.get('sharpe_ratio', 0):.2f}", self._get_status(metrics.get('sharpe_ratio', 0), 1, 2)],
                ["Sortino Ratio", f"{metrics.get('sortino_ratio', 0):.2f}", self._get_status(metrics.get('sortino_ratio', 0), 1, 2)],
                ["Max Drawdown", f"{metrics.get('max_drawdown', 0):.2f}%", self._get_status_inverse(metrics.get('max_drawdown', 0), 10, 5)],
                ["Recovery Factor", f"{metrics.get('recovery_factor', 0):.2f}", self._get_status(metrics.get('recovery_factor', 0), 1, 3)],
            ]
            
            risk_table = Table(risk_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
            risk_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e94560')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dddddd')),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ]))
            
            elements.append(risk_table)
            elements.append(Spacer(1, 20))
        
        # === LISTA DE TRADES ===
        if self.config.include_trades and trades:
            elements.append(PageBreak())
            elements.append(Paragraph("📈 Histórico de Trades", styles['SectionHeader']))
            
            trade_headers = ["Data", "Símbolo", "Tipo", "Volume", "Preço", "P/L"]
            trade_data = [trade_headers]
            
            for trade in trades[:50]:  # Limita a 50 trades
                trade_row = [
                    trade.get('time', '')[:10] if isinstance(trade.get('time'), str) else '',
                    trade.get('symbol', ''),
                    trade.get('type', ''),
                    f"{trade.get('volume', 0):.2f}",
                    f"{trade.get('price', 0):.2f}",
                    f"${trade.get('profit', 0):,.2f}",
                ]
                trade_data.append(trade_row)
            
            trade_table = Table(trade_data, colWidths=[1.2*inch, 1*inch, 0.8*inch, 0.8*inch, 1*inch, 1*inch])
            trade_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            
            elements.append(trade_table)
        
        # === FOOTER ===
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(
            f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')} | {self.config.footer_text}",
            styles['Normal']
        ))
        
        # Build PDF
        doc.build(elements)
        
        buffer.seek(0)
        return buffer.getvalue()
    
    def _get_status(self, value: float, warning: float, good: float) -> str:
        """Retorna status baseado no valor."""
        if value >= good:
            return "✅ Bom"
        elif value >= warning:
            return "⚠️ Médio"
        else:
            return "❌ Ruim"
    
    def _get_status_inverse(self, value: float, warning: float, good: float) -> str:
        """Retorna status inverso (menor é melhor)."""
        if value <= good:
            return "✅ Bom"
        elif value <= warning:
            return "⚠️ Médio"
        else:
            return "❌ Ruim"
    
    def _generate_html(
        self,
        start_date: datetime,
        end_date: datetime,
        trades: List[Dict],
        metrics: Dict[str, Any],
        account_info: Optional[Dict],
    ) -> bytes:
        """Gera relatório em HTML (fallback)."""
        html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>{self.config.title}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            text-align: center;
            padding: 30px;
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            color: white;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .header h1 {{ margin: 0; font-size: 28px; }}
        .header .date {{ opacity: 0.8; margin-top: 10px; }}
        .section {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            color: #1a1a2e;
            border-bottom: 2px solid #e94560;
            padding-bottom: 10px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
        }}
        .metric {{
            text-align: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        .metric .value {{
            font-size: 24px;
            font-weight: bold;
            color: #0f3460;
        }}
        .metric .label {{
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #1a1a2e;
            color: white;
        }}
        tr:nth-child(even) {{ background: #f9f9f9; }}
        .profit {{ color: #28a745; }}
        .loss {{ color: #dc3545; }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{self.config.title}</h1>
        <div class="date">{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}</div>
    </div>
    
    <div class="section">
        <h2>📊 Resumo de Performance</h2>
        <div class="metrics-grid">
            <div class="metric">
                <div class="value">{metrics.get('total_trades', 0)}</div>
                <div class="label">Total de Trades</div>
            </div>
            <div class="metric">
                <div class="value">{metrics.get('win_rate', 0):.1f}%</div>
                <div class="label">Win Rate</div>
            </div>
            <div class="metric">
                <div class="value">{metrics.get('profit_factor', 0):.2f}</div>
                <div class="label">Profit Factor</div>
            </div>
            <div class="metric">
                <div class="value {'profit' if metrics.get('total_profit', 0) >= 0 else 'loss'}">${metrics.get('total_profit', 0):,.2f}</div>
                <div class="label">Lucro Total</div>
            </div>
            <div class="metric">
                <div class="value">${metrics.get('avg_profit', 0):,.2f}</div>
                <div class="label">Lucro Médio</div>
            </div>
            <div class="metric">
                <div class="value">{metrics.get('max_drawdown', 0):.2f}%</div>
                <div class="label">Max Drawdown</div>
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2>📈 Últimos Trades</h2>
        <table>
            <thead>
                <tr>
                    <th>Data</th>
                    <th>Símbolo</th>
                    <th>Tipo</th>
                    <th>Volume</th>
                    <th>P/L</th>
                </tr>
            </thead>
            <tbody>
                {''.join(f'''
                <tr>
                    <td>{t.get('time', '')[:10] if isinstance(t.get('time'), str) else ''}</td>
                    <td>{t.get('symbol', '')}</td>
                    <td>{t.get('type', '')}</td>
                    <td>{t.get('volume', 0):.2f}</td>
                    <td class="{'profit' if t.get('profit', 0) >= 0 else 'loss'}">${t.get('profit', 0):,.2f}</td>
                </tr>
                ''' for t in trades[:20])}
            </tbody>
        </table>
    </div>
    
    <div class="footer">
        Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')} | {self.config.footer_text}
    </div>
</body>
</html>
"""
        return html.encode('utf-8')


# Instância global
report_generator = PDFReportGenerator()


# ============================================================================
# ROUTES FASTAPI
# ============================================================================

from fastapi import APIRouter, Query
from fastapi.responses import Response, StreamingResponse

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("/performance")
async def generate_performance_report(
    start_date: str = Query(..., description="Data inicial (YYYY-MM-DD)"),
    end_date: str = Query(..., description="Data final (YYYY-MM-DD)"),
    format: str = Query("pdf", description="Formato: pdf ou html"),
):
    """Gera relatório de performance."""
    from datetime import datetime
    
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    # TODO: Buscar trades e métricas reais do banco
    trades = []  # Implementar busca
    metrics = {
        "total_trades": 0,
        "win_rate": 0,
        "profit_factor": 0,
        "total_profit": 0,
        "avg_profit": 0,
        "max_profit": 0,
        "max_loss": 0,
        "max_drawdown": 0,
        "sharpe_ratio": 0,
        "sortino_ratio": 0,
        "recovery_factor": 0,
    }
    
    pdf_bytes = await report_generator.generate_performance_report(
        start_date=start,
        end_date=end,
        trades=trades,
        metrics=metrics,
    )
    
    if format == "html":
        return Response(
            content=pdf_bytes,
            media_type="text/html",
        )
    
    filename = f"virtus_report_{start_date}_{end_date}.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


# ============================================================================
# EXEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        generator = PDFReportGenerator()
        
        trades = [
            {"time": "2024-01-15 10:30", "symbol": "XAUUSD", "type": "BUY", "volume": 0.01, "price": 2050.50, "profit": 45.20},
            {"time": "2024-01-15 14:20", "symbol": "EURUSD", "type": "SELL", "volume": 0.02, "price": 1.0850, "profit": -12.30},
            {"time": "2024-01-16 09:15", "symbol": "XAUUSD", "type": "BUY", "volume": 0.01, "price": 2055.00, "profit": 28.50},
        ]
        
        metrics = {
            "total_trades": 150,
            "win_rate": 62.5,
            "profit_factor": 1.85,
            "total_profit": 1250.00,
            "avg_profit": 8.33,
            "max_profit": 125.00,
            "max_loss": -45.00,
            "max_drawdown": 5.2,
            "sharpe_ratio": 1.45,
            "sortino_ratio": 1.82,
            "recovery_factor": 2.3,
        }
        
        pdf = await generator.generate_performance_report(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            trades=trades,
            metrics=metrics,
        )
        
        # Salva para teste
        with open("test_report.html", "wb") as f:
            f.write(pdf)
        
        print(f"Relatório gerado: {len(pdf)} bytes")
    
    asyncio.run(test())
