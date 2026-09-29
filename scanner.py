 # V39 - 5 MIN CANDLE HIGH VOLUME BOTTOM/TOP

def is_5min_high_volume_breakout(s):
    # s = 5min candle data
    
    # ===== BASIC FILTER - 150 FAKE BLOCK =====
    if s['score'] < 17: return False
    if s['volume'] < 2.0 * s['avg_5m_vol']: return False # High Volume Must - 2x
    if not (40 < s['ltp'] < 2500): return False
    
    # ===== BOTTOM BUY - 5 MIN CANDLE =====
    # Condition: खाली Support जवळ + High Volume + Bullish Candle
    if s['trend'] == "BUY":
        # 1. Bottom जवळ आहे का? Day Low पासून 0.8% वर
        if s['near_day_low_pct'] > 1.2: return False # Bottom नाही - मधेच आहे
        # 2. 5 Min Candle - Bullish Engulfing / Hammer / Big Green
        if not (s['candle_5m_close'] > s['candle_5m_open'] and s['candle_5m_body'] > 0.6): return False
        # 3. High Volume Bottom वर - Volume 2x + Price Low वर
        if not (s['vol_5m'] > 2.0 * s['avg_vol_5m'] and s['low_5m'] <= s['day_low']*1.005): return False
        # 4. 9EMA x 15EMA + VWAP x 9EMA Cross Bottom वर
        if not (s['ema9'] > s['ema15'] and s['vwap'] > s['ema9'] and s['ltp'] > s['vwap']): return False
        # 5. 52W Filter
        if not (88 < s['near_52h'] < 97.5): return False # Top 98.8% Block
        # 6. RSI
        if not (35 <= s['rsi_5m'] <= 55): return False # Bottom RSI - Oversold मधून वर
        
        # REAL BOTTOM BUY ✅
        # Example: SJVN Day Low 60.2, 5M Candle Low 60.2 High 61.7 Close 61.5 Vol 2.5x
        return True

    # ===== TOP SELL - 5 MIN CANDLE =====
    if s['trend'] == "SELL":
        # 1. Top जवळ
        if s['near_day_high_pct'] > 1.2: return False
        # 2. 5 Min Candle - Bearish Engulfing / Shooting Star / Big Red
        if not (s['candle_5m_close'] < s['candle_5m_open'] and s['candle_5m_body'] > 0.6): return False
        # 3. High Volume Top वर
        if not (s['vol_5m'] > 2.0 * s['avg_vol_5m'] and s['high_5m'] >= s['day_high']*0.995): return False
        # 4. 9EMA x 15EMA + VWAP Cross Top वर
        if not (s['ema9'] < s['ema15'] and s['vwap'] < s['ema9'] and s['ltp'] < s['vwap']): return False
        # 5. 52W Filter - 100.1% Block
        if not (108 < s['near_52l'] < 135): return False
        # 6. RSI
        if not (65 <= s['rsi_5m'] <= 85): return False # Top RSI - Overbought
        
        return True
    
    return False
