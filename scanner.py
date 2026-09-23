import os, time, requests, traceback
from datetime import datetime
import pandas as pd
import talib
from SmartApi import SmartConnect

# ===== CONFIG =====
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID")
API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PASSWORD = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP")

CAPITAL_TOTAL = 30000
CAPITAL_PER_TRADE = 5000
MAX_TRADES = 6
ACTIVE_LIMIT = 2
active_trades = 0
total_trades_done = 0

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except: pass

# ===== ANGEL LOGIN =====
smartApi = SmartConnect(api_key=API_KEY)
try:
    import pyotp
    totp = pyotp.TOTP(TOTP_SECRET).now()
    smartApi.generateSession(CLIENT_ID, PASSWORD, totp)
    print("Angel Login Success")
except Exception as e:
    print(f"Login Fail: {e}")

# ===== SCANNER LOGIC =====
def check_rocket_stock(df_15, df_daily):
    try:
        # Filter 1: Price 50 to 1500
        price = df_15['close'].iloc[-1]
        if not (50 <= price <= 1500):
            return None

        # Filter 2: Volume 2X (20 Days) - TUMCHI DEMAND
        avg_vol = df_daily['volume'].rolling(20).mean().iloc[-1]
        curr_vol = df_daily['volume'].iloc[-1]
        if curr_vol < 2 * avg_vol:
            return None

        # Filter 3: First 15 Min High Break
        first_high = df_15['high'].iloc[0]
        if price < first_high:
            return None

        # Filter 4: 5 Candle Patterns (TA-Lib)
        open_p, high_p, low_p, close_p = df_15['open'], df_15['high'], df_15['low'], df_15['close']
        patterns = {
            "Bullish Engulfing": talib.CDLENGULFING(open_p, high_p, low_p, close_p).iloc[-1] == 100,
            "Hammer": talib.CDLHAMMER(open_p, high_p, low_p, close_p).iloc[-1] == 100,
            "Morning Star": talib.CDLMORNINGSTAR(open_p, high_p, low_p, close_p).iloc[-1] == 100,
            "Piercing": talib.CDLPIERCING(open_p, high_p, low_p, close_p).iloc[-1] == 100,
            "3 White Soldiers": talib.CDL3WHITESOLDIERS(open_p, high_p, low_p, close_p).iloc[-1] == 100,
        }
        found_pattern = [k for k,v in patterns.items() if v]
        if not found_pattern:
            return None

        # ===== TUMCHI SL LOGIC: छोट्या Candle चा Low =====
        df_prev = df_15.iloc[-6:-1].copy()
        df_prev['body'] = abs(df_prev['close'] - df_prev['open'])
        smallest_low = df_prev.loc[df_prev['body'].idxmin(), 'low']

        stoploss = smallest_low
        sl_perc = (price - stoploss) * 100 / price

        # Safety: SL 0.8% to 3.5% च्या आतच हवा
        if sl_perc < 0.8 or sl_perc > 3.5:
            stoploss = df_15['low'].iloc[-2] # जर खूप लांब असेल तर मागची Candle Low

        target = price + (price - stoploss) * 2 # 1:2 Risk Reward

        return {
            "price": price,
            "sl": round(stoploss, 2),
            "target": round(target, 2),
            "pattern": found_pattern[0],
            "sl_perc": round(sl_perc, 2)
        }
    except Exception as e:
        print(f"Check Error: {e}")
        return None

def place_order_final(symbol, info):
    global active_trades, total_trades_done
    if active_trades >= ACTIVE_LIMIT or total_trades_done >= MAX_TRADES:
        print("Limit Reached")
        return

    qty = int(CAPITAL_PER_TRADE / info['price'])
    if qty == 0: return

    # --- Angel Order (आत्ता Print करतोय, हवं असेल तर Uncomment कर) ---
    # orderparams = {"variety":"NORMAL","tradingsymbol":symbol,"symboltoken":token,"transactiontype":"BUY","exchange":"NSE","ordertype":"MARKET","producttype":"INTRADAY","duration":"DAY","quantity":qty}
    # smartApi.placeOrder(orderparams)

    active_trades += 1
    total_trades_done += 1

    msg = f"🚀 BREAKOUT: {symbol}\nPrice: {info['price']}\nPattern: {info['pattern']}\nSL: {info['sl']} (छोटी Candle Low)\nTarget: {info['target']}\nRisk: {info['sl_perc']}%\nQty: {qty} | Vol 2X ✅"
    print(msg)
    send_telegram(msg)

# ===== MAIN LOOP =====
# इथे तुझी 1000 Stocks ची List Loop होईल
# for symbol in nifty_1000_list:
# df_15 = smartApi.getCandleData(...)
# df_daily =...
# result = check_rocket_stock(df_15, df_daily)
# if result: place_order_final(symbol, result)

# Test साठी
send_telegram(f"NSE Scanner Started: 2X Vol + Small Candle SL Logic Active ✅ Time: {datetime.now().strftime('%H:%M')}")
