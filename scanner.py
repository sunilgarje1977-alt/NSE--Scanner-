import os, requests, talib
import pandas as pd
from datetime import datetime

# ========== TELEGRAM SETUP ==========
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except: pass

# ========== CONFIG - तुझं सगळं इथे ==========
TOTAL_CAPITAL = 30000 # तुझं Capital इथे बदल
MAX_TRADES = 6
ACTIVE_LIMIT = 2
CAPITAL_PER_TRADE = (TOTAL_CAPITAL * 5) / MAX_TRADES # 5x Leverage

# ========== 7 FILTERS + 5 CANDLE PATTERNS ==========
def check_rocket_stock(df_daily, df_15, symbol):
    o,h,l,c = df_15['open'], df_15['high'], df_15['low'], df_15['close']
    price = c.iloc[-1]

    # Filter 0: Price 50-1500
    if not (50 <= price <= 1500): return False, ""

    # 1: First 15 Min Break
    if price <= df_15['high'].iloc[0]: return False, ""

    # 2: Volume 2x (20 Days)
    avg_vol = df_daily['volume'].rolling(20).mean().iloc[-1]
    if df_daily['volume'].iloc[-1] < 2 * avg_vol: return False, ""

    # 3: 9 EMA Cross 21 EMA
    ema9, ema21 = talib.EMA(c, 9), talib.EMA(c, 21)
    if not (ema9.iloc[-2] < ema21.iloc[-2] and ema9.iloc[-1] > ema21.iloc[-1]): return False, ""

    # 4: Price > VWAP
    vwap = (c * df_15['volume']).cumsum() / df_15['volume'].cumsum()
    if price <= vwap.iloc[-1]: return False, ""

    # 5: Strong Candle Body > 60%
    body = abs(c.iloc[-1] - o.iloc[-1])
    rng = h.iloc[-1] - l.iloc[-1]
    if rng == 0 or (body/rng) < 0.6: return False, ""

    # 6: RSI > 55
    rsi = talib.RSI(c, 14).iloc[-1]
    if rsi <= 55: return False, ""

    # 7: Pivot Breakout (H+L+C)/3
    H, L, C = df_daily['high'].iloc[-2], df_daily['low'].iloc[-2], df_daily['close'].iloc[-2]
    pivot, R1 = (H+L+C)/3, (2*((H+L+C)/3) - L)
    if not (price > pivot and price >= R1*0.98): return False, ""

    # 8: तुझे 5 Candle Patterns
    is_hammer = talib.CDLHAMMER(o,h,l,c).iloc[-1]!= 0
    is_engulf = talib.CDLENGULFING(o,h,l,c).iloc[-1] > 0
    is_marubozu = talib.CDLMARUBOZU(o,h,l,c).iloc[-1] > 0
    is_mstar = talib.CDLMORNINGSTAR(o,h,l,c).iloc[-1]!= 0
    is_3sold = talib.CDL3WHITESOLDIERS(o,h,l,c).iloc[-1]!= 0

    pattern = ""
    if is_hammer: pattern="HAMMER 🔨"
    elif is_engulf: pattern="ENGULFING 🚀"
    elif is_marubozu: pattern="MARUBOZU 💪"
    elif is_mstar: pattern="MORNING STAR ⭐"
    elif is_3sold: pattern="3 SOLDIERS ⚔️"
    else: return False, ""

    return True, pattern

# ========== ORDER + QUEUE LOGIC (2 Active, Trailing SL) ==========
active_trades = 0
total_trades_done = 0

def place_order_final(symbol, price, pattern):
    global active_trades, total_trades_done
    if active_trades >= ACTIVE_LIMIT or total_trades_done >= MAX_TRADES:
        return

    qty = int(CAPITAL_PER_TRADE / price)
    # Angel API Order Place + Trailing SL 1%
    # smartApi.placeOrder({"symbol":symbol, "qty":qty, "sl": price*0.99, "trailing":True})

    active_trades += 1
    total_trades_done += 1
    msg
