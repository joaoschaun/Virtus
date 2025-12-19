"""
Diagnóstico de por que os bots não estão entrando em trades
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "src"))

import MetaTrader5 as mt5
import pandas as pd
import numpy as np


def diagnose_market():
    """Diagnóstico completo das condições de mercado"""
    
    if not mt5.initialize():
        print("❌ Falha ao inicializar MT5")
        return
    
    print("=" * 60)
    print("🔍 DIAGNÓSTICO - POR QUE OS BOTS NÃO ESTÃO ENTRANDO")
    print("=" * 60)
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Account check
    account = mt5.account_info()
    if account:
        print(f"✅ Conta: {account.login} ({account.server})")
        print(f"   Saldo: ${account.balance:.2f}")
        print(f"   Trade Allowed: {account.trade_allowed}")
        print(f"   Expert Allowed: {account.trade_expert}")
    else:
        print("❌ Não conseguiu obter info da conta")
        return
    
    print()
    
    symbols = ['XAUUSD', 'EURUSD', 'GBPUSD']
    
    for symbol in symbols:
        print(f"{'='*50}")
        print(f"📊 {symbol}")
        print(f"{'='*50}")
        
        # Symbol info
        info = mt5.symbol_info(symbol)
        if not info:
            print(f"   ❌ Símbolo não encontrado")
            continue
        
        # Tick
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            print(f"   ❌ Sem dados de tick")
            continue
        
        # Spread
        spread = tick.ask - tick.bid
        point = info.point
        spread_points = spread / point
        
        # Para forex, convertemos para pips (1 pip = 10 points geralmente)
        if symbol in ['EURUSD', 'GBPUSD']:
            spread_pips = spread_points / 10
            max_spread = 2.0  # pips
        else:  # XAUUSD
            spread_pips = spread_points / 10
            max_spread = 3.0  # pips
        
        print(f"\n   📈 PREÇO E SPREAD:")
        print(f"   Bid: {tick.bid:.5f}")
        print(f"   Ask: {tick.ask:.5f}")
        print(f"   Spread: {spread_pips:.2f} pips", end="")
        if spread_pips > max_spread:
            print(f" ❌ (muito alto! máx: {max_spread})")
        else:
            print(f" ✅ (ok)")
        
        # Obtém dados históricos
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 100)
        if rates is None or len(rates) < 50:
            print(f"   ❌ Dados históricos insuficientes")
            continue
        
        df = pd.DataFrame(rates)
        df['datetime'] = pd.to_datetime(df['time'], unit='s')
        
        # Calcula indicadores básicos
        print(f"\n   📉 INDICADORES TÉCNICOS:")
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        print(f"   RSI(14): {current_rsi:.1f}", end="")
        if current_rsi < 30:
            print(" 🟢 (oversold - possível compra)")
        elif current_rsi > 70:
            print(" 🔴 (overbought - possível venda)")
        else:
            print(" ⚪ (neutro)")
        
        # EMAs
        ema9 = df['close'].ewm(span=9).mean().iloc[-1]
        ema21 = df['close'].ewm(span=21).mean().iloc[-1]
        ema50 = df['close'].ewm(span=50).mean().iloc[-1]
        
        print(f"   EMA9: {ema9:.5f}")
        print(f"   EMA21: {ema21:.5f}")
        print(f"   EMA50: {ema50:.5f}")
        
        trend = "ALTA" if ema9 > ema21 > ema50 else "BAIXA" if ema9 < ema21 < ema50 else "INDEFINIDA"
        print(f"   Tendência: {trend}")
        
        # ATR (volatilidade)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = np.maximum(high_low, np.maximum(high_close, low_close))
        atr = tr.rolling(14).mean().iloc[-1]
        atr_pct = (atr / tick.bid) * 100
        
        print(f"   ATR(14): {atr:.5f} ({atr_pct:.3f}%)", end="")
        if atr_pct < 0.05:
            print(" ⚠️ (muito baixa - mercado parado)")
        elif atr_pct > 0.5:
            print(" ⚠️ (muito alta - muito arriscado)")
        else:
            print(" ✅ (ok)")
        
        # Bollinger Bands
        sma20 = df['close'].rolling(20).mean().iloc[-1]
        std20 = df['close'].rolling(20).std().iloc[-1]
        bb_upper = sma20 + 2 * std20
        bb_lower = sma20 - 2 * std20
        bb_position = (tick.bid - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0.5
        
        print(f"   BB Upper: {bb_upper:.5f}")
        print(f"   BB Lower: {bb_lower:.5f}")
        print(f"   Posição BB: {bb_position:.1%}", end="")
        if bb_position < 0.1:
            print(" 🟢 (próximo ao suporte)")
        elif bb_position > 0.9:
            print(" 🔴 (próximo à resistência)")
        else:
            print(" ⚪ (meio da banda)")
        
        # ADX (força da tendência)
        plus_dm = df['high'].diff()
        minus_dm = -df['low'].diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        plus_di = 100 * (plus_dm.rolling(14).mean() / tr.rolling(14).mean())
        minus_di = 100 * (minus_dm.rolling(14).mean() / tr.rolling(14).mean())
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(14).mean().iloc[-1]
        
        print(f"   ADX(14): {adx:.1f}", end="")
        if adx < 20:
            print(" ⚪ (sem tendência - ranging)")
        elif adx < 40:
            print(" 🟡 (tendência moderada)")
        else:
            print(" 🟢 (tendência forte)")
        
        # ANÁLISE DE SETUP
        print(f"\n   🎯 ANÁLISE DE SETUP:")
        
        setup_score = 0
        setup_reasons = []
        
        # Critério 1: RSI extremo
        if current_rsi < 30:
            setup_score += 1
            setup_reasons.append("RSI oversold")
        elif current_rsi > 70:
            setup_score += 1
            setup_reasons.append("RSI overbought")
        
        # Critério 2: Preço na banda
        if bb_position < 0.15 or bb_position > 0.85:
            setup_score += 1
            setup_reasons.append("Preço extremo BB")
        
        # Critério 3: Tendência definida com ADX
        if adx > 25 and trend != "INDEFINIDA":
            setup_score += 1
            setup_reasons.append(f"Tendência {trend} com ADX forte")
        
        # Critério 4: Spread ok
        if spread_pips <= max_spread:
            setup_score += 1
            setup_reasons.append("Spread adequado")
        
        # Critério 5: Volatilidade ok
        if 0.05 <= atr_pct <= 0.5:
            setup_score += 1
            setup_reasons.append("Volatilidade adequada")
        
        print(f"   Score: {setup_score}/5")
        if setup_reasons:
            print(f"   Fatores positivos: {', '.join(setup_reasons)}")
        
        if setup_score >= 3:
            print(f"   ✅ CONDIÇÕES FAVORÁVEIS PARA ENTRADA!")
        else:
            print(f"   ⚠️ Aguardando melhores condições...")
            missing = []
            if current_rsi >= 30 and current_rsi <= 70:
                missing.append("RSI neutro (precisa <30 ou >70)")
            if 0.15 <= bb_position <= 0.85:
                missing.append("Preço no meio das bandas")
            if adx < 25:
                missing.append(f"ADX baixo ({adx:.0f}) - sem tendência clara")
            if spread_pips > max_spread:
                missing.append(f"Spread alto ({spread_pips:.1f} pips)")
            if atr_pct < 0.05:
                missing.append("Volatilidade muito baixa")
            if missing:
                print(f"   Razões: {', '.join(missing)}")
        
        print()
    
    # Horário de mercado
    print("=" * 50)
    print("🕐 SESSÃO DE MERCADO")
    print("=" * 50)
    hour = datetime.utcnow().hour
    
    if 22 <= hour or hour < 7:
        session = "ASIÁTICA"
        quality = "⚠️ Baixa liquidez para forex"
    elif 7 <= hour < 12:
        session = "LONDRES"
        quality = "✅ Alta liquidez"
    elif 12 <= hour < 17:
        session = "NEW YORK"
        quality = "✅ Alta liquidez"
    elif 17 <= hour < 22:
        session = "TARDE NY / INÍCIO ASIA"
        quality = "⚠️ Liquidez moderada"
    
    print(f"   Sessão atual: {session}")
    print(f"   Qualidade: {quality}")
    print(f"   Hora UTC: {datetime.utcnow().strftime('%H:%M')}")
    
    mt5.shutdown()
    
    print()
    print("=" * 60)
    print("📋 RESUMO")
    print("=" * 60)
    print("""
Os bots podem não estar entrando por:

1. 📊 Confluência insuficiente - O sistema requer múltiplas 
   confirmações (RSI, BB, trend, ADX) alinhadas

2. ⏰ Horário - Algumas sessões têm baixa liquidez

3. 📈 Mercado sem tendência (ADX < 25) - Sistema aguarda
   condições mais claras

4. 🎚️ Thresholds conservadores - min_confluence = 60%
   requer vários indicadores concordando

SOLUÇÃO: Se quiser mais entradas, pode:
- Reduzir min_confluence de 0.6 para 0.5
- Reduzir min_risk_reward de 1.5 para 1.2
- Habilitar modo scalping que é mais agressivo
""")


if __name__ == "__main__":
    diagnose_market()
