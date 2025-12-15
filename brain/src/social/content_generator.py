"""
VIRTUS Social Media - Content Generator
========================================

Gerador de conteúdo textual para posts de redes sociais.
Usa dados do Brain (análises, notícias, sinais) para criar posts.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pathlib import Path
import sys
import random

# Adiciona path do src
BRAIN_PATH = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BRAIN_PATH))


class PostType(Enum):
    """Tipos de posts disponíveis."""
    MARKET_ALERT = "market_alert"           # Alerta de mercado/oportunidade
    DAILY_SUMMARY = "daily_summary"         # Resumo diário do mercado
    NEWS_HIGHLIGHT = "news_highlight"       # Destaque de notícia importante
    TECHNICAL_ANALYSIS = "technical"        # Análise técnica
    WEEKLY_OUTLOOK = "weekly_outlook"       # Previsão semanal
    TRADING_TIP = "trading_tip"             # Dica de trading
    EDUCATIONAL = "educational"             # Conteúdo educacional
    PERFORMANCE = "performance"             # Performance dos bots


@dataclass
class PostContent:
    """Conteúdo de um post."""
    post_type: PostType
    title: str
    body: str
    caption: str  # Texto completo para o Instagram
    hashtags: List[str]
    
    # Dados para imagem
    image_data: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    symbol: Optional[str] = None
    sentiment: Optional[str] = None
    priority: str = "normal"  # low, normal, high, urgent


class ContentGenerator:
    """
    Gerador de conteúdo para posts.
    
    Cria textos profissionais e envolventes baseados nos dados do Brain.
    """
    
    def __init__(self):
        # Hashtags padrão por categoria
        self.base_hashtags = [
            "VirtusInvestimentos", "Trading", "MercadoFinanceiro"
        ]
        
        self.forex_hashtags = [
            "Forex", "ForexTrader", "ForexTrading", "DayTrader",
            "Trader", "TradingView", "ForexSignals"
        ]
        
        self.crypto_hashtags = [
            "Crypto", "Bitcoin", "Ethereum", "Criptomoedas",
            "BTC", "CryptoTrading", "CryptoInvestor"
        ]
        
        self.gold_hashtags = [
            "Gold", "Ouro", "XAUUSD", "GoldTrading",
            "Commodities", "PreciousMetals"
        ]
        
        self.education_hashtags = [
            "TradingEducation", "AprenderTrading", "Investidor",
            "EducacaoFinanceira", "Investimentos"
        ]
        
        # Templates de textos
        self._init_templates()
    
    def _init_templates(self):
        """Inicializa templates de texto."""
        
        # Introduções para alertas
        self.alert_intros = [
            "🔥 ALERTA DE MERCADO",
            "⚡ OPORTUNIDADE IDENTIFICADA",
            "📊 SETUP EM FORMAÇÃO",
            "🎯 MOMENTO DECISIVO",
            "💡 ATENÇÃO TRADERS",
        ]
        
        # Textos para tendência de alta
        self.bullish_texts = [
            "Mercado mostrando força compradora!",
            "Momentum positivo se desenvolvendo.",
            "Compradores dominando o cenário.",
            "Sinal de força no ativo.",
            "Tendência de alta ganhando força.",
        ]
        
        # Textos para tendência de baixa
        self.bearish_texts = [
            "Pressão vendedora se intensificando.",
            "Mercado demonstra fraqueza.",
            "Vendedores ganhando controle.",
            "Momento de cautela para posições compradas.",
            "Tendência de baixa predominante.",
        ]
        
        # Textos para mercado lateral
        self.neutral_texts = [
            "Mercado em consolidação.",
            "Momento de indecisão no ativo.",
            "Aguardando definição de direção.",
            "Range trading predominante.",
            "Acumulação em andamento.",
        ]
        
        # Dicas de trading
        self.trading_tips = [
            {
                "title": "Gestão de Risco",
                "body": "Nunca arrisque mais de 2% do seu capital em uma única operação. A gestão de risco é o que separa traders profissionais de amadores.",
            },
            {
                "title": "Disciplina é Tudo",
                "body": "O plano de trading existe para ser seguido. Operar por impulso é o caminho mais rápido para perdas consistentes.",
            },
            {
                "title": "Paciência no Setup",
                "body": "Os melhores traders são aqueles que sabem esperar. Não force operações - deixe o mercado vir até você.",
            },
            {
                "title": "Stop Loss Sempre",
                "body": "Stop loss não é opcional. Proteger seu capital deve ser a prioridade número 1 em qualquer operação.",
            },
            {
                "title": "Aceite as Perdas",
                "body": "Perdas fazem parte do jogo. O que importa é que seus ganhos sejam maiores que suas perdas ao longo do tempo.",
            },
            {
                "title": "Diário de Trading",
                "body": "Registre todas as suas operações. Analisar seus erros e acertos é fundamental para evolução.",
            },
            {
                "title": "Não Opere por Vingança",
                "body": "Após uma perda, afaste-se. Operar tentando recuperar prejuízo é receita para desastre.",
            },
            {
                "title": "Tendência é Sua Amiga",
                "body": "Operar a favor da tendência aumenta significativamente suas chances de sucesso.",
            },
            {
                "title": "Menos é Mais",
                "body": "Não é sobre quantidade de operações, mas qualidade. Um bom setup vale mais que dez operações forçadas.",
            },
            {
                "title": "Psicologia de Trading",
                "body": "80% do sucesso no trading é psicológico. Controle emocional é sua maior ferramenta.",
            },
        ]
        
        # Conteúdo educacional
        self.educational_content = [
            {
                "title": "O que é Stop Loss?",
                "body": "Stop Loss é uma ordem de saída automática que limita suas perdas quando o mercado vai contra sua posição. É a ferramenta mais importante de gestão de risco.",
            },
            {
                "title": "Suporte e Resistência",
                "body": "Suporte é o nível onde há interesse comprador suficiente para parar uma queda. Resistência é onde vendedores entram em ação. Identificá-los é fundamental.",
            },
            {
                "title": "O que é Alavancagem?",
                "body": "Alavancagem permite operar com mais capital do que você tem. É uma faca de dois gumes: amplifica ganhos, mas também as perdas. Use com responsabilidade.",
            },
            {
                "title": "Timeframes",
                "body": "Diferentes timeframes servem diferentes propósitos. Gráficos maiores mostram tendência, menores mostram entrada. Aprenda a usar múltiplos timeframes.",
            },
            {
                "title": "Risk/Reward",
                "body": "Relação risco/retorno ideal é de pelo menos 1:2. Se você arrisca R$100, seu alvo deve ser no mínimo R$200. Assim, você pode errar mais da metade e ainda lucrar.",
            },
        ]
    
    def _get_symbol_name(self, symbol: str) -> str:
        """Retorna nome legível do símbolo."""
        names = {
            "XAUUSD": "Ouro",
            "EURUSD": "Euro/Dólar",
            "GBPUSD": "Libra/Dólar",
            "USDJPY": "Dólar/Iene",
            "BTCUSD": "Bitcoin",
            "ETHUSD": "Ethereum",
        }
        return names.get(symbol, symbol)
    
    def _get_symbol_hashtags(self, symbol: str) -> List[str]:
        """Retorna hashtags relevantes para o símbolo."""
        if "XAU" in symbol:
            return self.gold_hashtags[:4]
        elif "BTC" in symbol or "ETH" in symbol:
            return self.crypto_hashtags[:4]
        else:
            return self.forex_hashtags[:4]
    
    def generate_market_alert(
        self,
        symbol: str,
        trend: str,
        price: float,
        support: Optional[float] = None,
        resistance: Optional[float] = None,
        analysis_text: Optional[str] = None,
    ) -> PostContent:
        """
        Gera post de alerta de mercado.
        
        Args:
            symbol: Símbolo do ativo
            trend: "bullish", "bearish", "neutral"
            price: Preço atual
            support: Nível de suporte
            resistance: Nível de resistência
            analysis_text: Texto adicional de análise
        """
        intro = random.choice(self.alert_intros)
        symbol_name = self._get_symbol_name(symbol)
        
        # Texto baseado na tendência
        if trend == "bullish":
            trend_text = random.choice(self.bullish_texts)
            trend_emoji = "📈"
            trend_word = "ALTA"
        elif trend == "bearish":
            trend_text = random.choice(self.bearish_texts)
            trend_emoji = "📉"
            trend_word = "BAIXA"
        else:
            trend_text = random.choice(self.neutral_texts)
            trend_emoji = "➡️"
            trend_word = "LATERAL"
        
        # Título
        title = f"{intro} | {symbol}"
        
        # Corpo
        body_lines = [
            f"{trend_emoji} {symbol_name} em momento decisivo!",
            "",
            f"• Tendência: {trend_word}",
            f"• Preço: ${price:,.2f}",
        ]
        
        if support:
            body_lines.append(f"• Suporte: ${support:,.2f}")
        if resistance:
            body_lines.append(f"• Resistência: ${resistance:,.2f}")
        
        body_lines.append("")
        body_lines.append(f"💡 {trend_text}")
        
        if analysis_text:
            body_lines.append("")
            body_lines.append(analysis_text)
        
        body = "\n".join(body_lines)
        
        # Caption completa para Instagram
        hashtags = self.base_hashtags + self._get_symbol_hashtags(symbol)
        hashtags_text = " ".join([f"#{tag}" for tag in hashtags])
        
        caption = f"""{intro} | {symbol}

{trend_emoji} {symbol_name} em momento decisivo!

📊 Análise Técnica:
• Tendência: {trend_word}
• Preço Atual: ${price:,.2f}
{f"• Suporte: ${support:,.2f}" if support else ""}
{f"• Resistência: ${resistance:,.2f}" if resistance else ""}

💡 {trend_text}

{analysis_text or ""}

⚠️ Lembre-se: Sempre use gestão de risco adequada.

{hashtags_text}"""
        
        return PostContent(
            post_type=PostType.MARKET_ALERT,
            title=title,
            body=body,
            caption=caption.strip(),
            hashtags=hashtags,
            symbol=symbol,
            sentiment=trend,
            priority="high" if trend in ["bullish", "bearish"] else "normal",
            image_data={
                "template": "market_alert",
                "symbol": symbol,
                "trend": trend,
                "price": price,
                "support": support,
                "resistance": resistance,
            }
        )
    
    def generate_news_post(
        self,
        title: str,
        summary: str,
        sentiment: str,
        related_symbols: List[str] = None,
        source: str = None,
    ) -> PostContent:
        """
        Gera post de notícia.
        
        Args:
            title: Título da notícia
            summary: Resumo
            sentiment: Sentimento ("bullish", "bearish", "neutral")
            related_symbols: Símbolos relacionados
            source: Fonte da notícia
        """
        # Emoji baseado no sentimento
        if sentiment == "bullish":
            sentiment_emoji = "💚"
            impact_text = "Impacto positivo esperado nos mercados."
        elif sentiment == "bearish":
            sentiment_emoji = "❤️"
            impact_text = "Pode pressionar os mercados para baixo."
        else:
            sentiment_emoji = "⚪"
            impact_text = "Impacto a ser avaliado."
        
        # Símbolos relacionados
        symbols_text = ""
        if related_symbols:
            symbols_text = f"\n\n📌 Ativos relacionados: {', '.join(related_symbols)}"
        
        # Hashtags
        hashtags = self.base_hashtags + ["Notícias", "MercadoHoje", "Economia"]
        if related_symbols:
            for sym in related_symbols[:2]:
                hashtags.append(sym.replace("/", ""))
        
        hashtags_text = " ".join([f"#{tag}" for tag in hashtags])
        
        body = f"""📰 {title}

{summary}

{sentiment_emoji} {impact_text}
{symbols_text}"""
        
        caption = f"""📰 NOTÍCIA DO MERCADO

{title}

{summary}

{sentiment_emoji} {impact_text}
{symbols_text}

🔔 Acompanhe a Virtus para análises em tempo real!

{hashtags_text}"""
        
        return PostContent(
            post_type=PostType.NEWS_HIGHLIGHT,
            title=title,
            body=body,
            caption=caption.strip(),
            hashtags=hashtags,
            sentiment=sentiment,
            priority="high" if sentiment in ["bullish", "bearish"] else "normal",
            image_data={
                "template": "news_highlight",
                "title": title,
                "body": summary,
                "trend": sentiment,
            }
        )
    
    def generate_daily_summary(
        self,
        highlights: List[Dict[str, Any]],
        market_sentiment: str = "neutral",
    ) -> PostContent:
        """
        Gera post de resumo diário.
        
        Args:
            highlights: Lista de destaques do dia
            market_sentiment: Sentimento geral do mercado
        """
        date_str = datetime.now().strftime("%d/%m/%Y")
        
        # Monta lista de destaques
        highlights_text = ""
        for h in highlights[:5]:
            symbol = h.get("symbol", "")
            change = h.get("change", 0)
            emoji = "📈" if change >= 0 else "📉"
            highlights_text += f"{emoji} {symbol}: {change:+.2f}%\n"
        
        # Sentimento geral
        if market_sentiment == "bullish":
            sentiment_text = "🟢 Mercado com viés positivo"
        elif market_sentiment == "bearish":
            sentiment_text = "🔴 Mercado com viés negativo"
        else:
            sentiment_text = "⚪ Mercado misto"
        
        body = f"""📊 Destaques do dia:

{highlights_text}
{sentiment_text}"""
        
        hashtags = self.base_hashtags + ["ResumoDiário", "MercadoHoje", "Análise"]
        hashtags_text = " ".join([f"#{tag}" for tag in hashtags])
        
        caption = f"""📅 RESUMO DO DIA | {date_str}

Bom dia, traders! Aqui está o resumo do mercado:

📊 Destaques:
{highlights_text}
{sentiment_text}

💬 O que esperar:
Acompanhe nosso perfil para análises ao longo do dia!

{hashtags_text}"""
        
        return PostContent(
            post_type=PostType.DAILY_SUMMARY,
            title=f"Resumo do Dia - {date_str}",
            body=body,
            caption=caption.strip(),
            hashtags=hashtags,
            sentiment=market_sentiment,
            image_data={
                "template": "daily_summary",
                "body": body,
            }
        )
    
    def generate_trading_tip(self) -> PostContent:
        """Gera post com dica de trading."""
        tip = random.choice(self.trading_tips)
        
        hashtags = self.base_hashtags + self.education_hashtags[:4]
        hashtags_text = " ".join([f"#{tag}" for tag in hashtags])
        
        caption = f"""💡 DICA DO DIA | {tip['title']}

{tip['body']}

📚 Conhecimento é a base do sucesso no trading!

Salve este post para consultar depois! 🔖

{hashtags_text}"""
        
        return PostContent(
            post_type=PostType.TRADING_TIP,
            title=tip['title'],
            body=tip['body'],
            caption=caption.strip(),
            hashtags=hashtags,
            priority="low",
            image_data={
                "template": "quote",
                "body": tip['body'],
            }
        )
    
    def generate_educational(self) -> PostContent:
        """Gera post educacional."""
        content = random.choice(self.educational_content)
        
        hashtags = self.base_hashtags + self.education_hashtags[:4]
        hashtags_text = " ".join([f"#{tag}" for tag in hashtags])
        
        caption = f"""📚 APRENDA | {content['title']}

{content['body']}

💬 Tem dúvidas? Deixe nos comentários!

Siga @virtusinvestimentos para mais conteúdo educacional.

{hashtags_text}"""
        
        return PostContent(
            post_type=PostType.EDUCATIONAL,
            title=content['title'],
            body=content['body'],
            caption=caption.strip(),
            hashtags=hashtags,
            priority="low",
            image_data={
                "template": "quote",
                "body": content['body'],
            }
        )
    
    def generate_from_brain_analysis(
        self,
        analysis: Dict[str, Any],
    ) -> Optional[PostContent]:
        """
        Gera post a partir de análise do Brain.
        
        Args:
            analysis: Dados de análise do Brain
            
        Returns:
            PostContent ou None se não houver conteúdo relevante
        """
        symbol = analysis.get("symbol")
        if not symbol:
            return None
        
        # Extrai dados
        price = analysis.get("price", 0)
        trend = analysis.get("trend", "neutral")
        support = analysis.get("support")
        resistance = analysis.get("resistance")
        confidence = analysis.get("confidence", 0)
        
        # Só gera post se confiança for alta
        if confidence < 0.7:
            return None
        
        # Texto adicional baseado na análise
        analysis_text = None
        if analysis.get("signal") == "buy":
            analysis_text = "Nossa análise indica potencial de entrada compradora."
        elif analysis.get("signal") == "sell":
            analysis_text = "Sinal de venda identificado pelo sistema."
        
        return self.generate_market_alert(
            symbol=symbol,
            trend=trend,
            price=price,
            support=support,
            resistance=resistance,
            analysis_text=analysis_text,
        )
