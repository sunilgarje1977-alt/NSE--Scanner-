import os, time, requests, json
from datetime import datetime, timedelta
import pandas as pd
import talib
import pyotp
from SmartApi import SmartConnect

# ===== CONFIG =====
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PASSWORD = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP")

CAPITAL_PER_TRADE = 5000
MAX_TRADES = 6
ACTIVE_LIMIT = 2
active_trades = 0
total_trades_done = 0
active_positions = {}

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        print(msg)
    except Exception as e:
        print(e)

# ===== ANGEL LOGIN =====
smartApi = SmartConnect(api_key=API_KEY)
try:
    totp = pyotp.TOTP(TOTP_SECRET).now()
    data = smartApi.generateSession(CLIENT_ID, PASSWORD, totp)
    print("Login Success")
    send_telegram(f"✅ Login Success {datetime.now().strftime('%H:%M')}")
except Exception as e:
    print(f"Login Fail {e}")
    send_telegram(f"Login Fail {e}")

# ===== HELPER: CANDLE DATA =====
def get_candles(token, interval, days=20):
    try:
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        historicParam = {
            "exchange": "NSE", "symboltoken": token,
            "interval": interval,
            "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
            "todate": to_date.strftime("%Y-%m-%d %H:%M")
        }
        data = smartApi.getCandleData(historicParam)
        df = pd.DataFrame(data['data'], columns=['timestamp','open','high','low','close','volume'])
        return df
    except: return None

# ===== 1. TUMCHI STRATEGY: 2X + SMALL CANDLE SL =====
def check_rocket_stock(df_15, df_daily):
    try:
        price = df_15['close'].iloc[-1]
        if not (50 <= price <= 1500): return None

        # 2X Volume Logic
        avg_vol = df_daily['volume'].rolling(20).mean().iloc[-1]
        if df_daily['volume'].iloc[-1] < 2 * avg_vol: return None

        # First 15m High Break
        first_high = df_15['high'].iloc[0]
        if price <= first_high: return None

        # 3 Pattern Check
        o,h,l,c = df_15['open'], df_15['high'], df_15['low'], df_15['close']
        engulf = talib.CDLENGULFING(o,h,l,c).iloc[-1]==100
        hammer = talib.CDLHAMMER(o,h,l,c).iloc[-1]==100
        morning = talib.CDLMORNINGSTAR(o,h,l,c).iloc[-1]==100
        if not (engulf or hammer or morning): return None

        # SL = छोट्या Candle चा Low
        prev = df_15.iloc[-6:-1].copy()
        prev['body'] = abs(prev['close'] - prev['open'])
        smallest_low = prev.loc[prev['body'].idxmin(), 'low']
        sl = smallest_low
        if (price - sl)*100/price > 3.5:
            sl = df_15['low'].iloc[-2]

        target = price + (price - sl)*2
        return {"price": price, "sl": round(sl,2), "target": round(target,2)}
    except: return None

# ===== 2. ORDER + TRAILING =====
def place_order_final(symbol, info, token):
    global active_trades, total_trades_done
    if active_trades >= ACTIVE_LIMIT or total_trades_done >= MAX_TRADES:
        return

    qty = max(1, int(CAPITAL_PER_TRADE / info['price']))

    # REAL ORDER (Live करायचा असेल तर # काढ)
    # smartApi.placeOrder({"variety":"NORMAL","tradingsymbol":f"{symbol}-EQ","symboltoken":token,"transactiontype":"BUY","exchange":"NSE","ordertype":"MARKET","producttype":"INTRADAY","duration":"DAY","quantity":qty})

    active_positions[symbol] = {"entry": info['price'], "sl": info['sl'], "target": info['target'], "high": info['price'], "token": token}
    active_trades += 1
    total_trades_done += 1

    msg = f"🚀 BUY {symbol}\nPrice: {info['price']}\nSL: {info['sl']} (Small Candle)\nTGT: {info['target']}\nQty: {qty} | 2X Vol ✅"
    send_telegram(msg)

def trail_sl_logic():
    global active_trades
    for symbol, pos in list(active_positions.items()):
        try:
            ltp = smartApi.ltpData("NSE", f"{symbol}-EQ", pos["token"])['data']['ltp']
            if ltp > pos["high"]: pos["high"] = ltp

            new_sl = pos["high"] * 0.98 # 2% Trailing
            if new_sl > pos["sl"]:
                pos["sl"] = new_sl
                send_telegram(f"🔒 TRAIL {symbol} SL->{round(new_sl,2)} LTP {ltp}")

            if ltp <= pos["sl"] or ltp >= pos["target"]:
                send_telegram(f"✅ EXIT {symbol} @ {ltp} P/L {(ltp-pos['entry'])*100/pos['entry']:.1f}%")
                del active_positions[symbol]
                active_trades -= 1
        except Exception as e:
            print(e)

# ===== 3. MAIN LOOP =====
def main():
    send_telegram("✅ Scanner STARTED: 30k Capital | Max 6 Trades | 2X Vol | Small Candle SL | 2% Trail")

    # Angel Instrument List (तुझ्याकडे असेल)
    # येथे Sample साठी 20 Stocks
    STOCK_LIST = [
        {"symbol":"RELIANCE","token":"2885"}, {"symbol":"TCS","token":"11536"},
        {"symbol":"WHIRLPOOL","token":"11321"}, {"symbol":"INFY","token":"1594"},
    ]

    while True:
        now = datetime.now()
        # फक्त 9:30 ते 3:00 पर्यंत चालवा
        if not (9 <= now.hour <= 15):
            time.sleep(60)
            continue

        for stock in STOCK_LIST:
            if active_trades >= ACTIVE_LIMIT or total_trades_done >= MAX_TRADES: break
            if stock["symbol"] in active_positions: continue

            df_15 = get_candles(stock["token"], "FIFTEEN_MINUTE", 2)
            df_daily = get_candles(stock["token"], "ONE_DAY", 30)
            if df_15 is None or df_daily is None or len(df_15)<10: continue

            result = check_rocket_stock(df_15, df_daily)
            if result:
                place_order_final(stock["symbol"], result, stock["token"])

        trail_sl_logic()
        time.sleep(60)

if __name__ == "__main__":
    main()
def daily_report():
    # 3:30 चा Report
    try:
        total_pnl = 0
        msg = "📊 *आजचा SENSEX 1000 Report*\n\n"
        for sym, pos in active_positions.items():
            ltp = smartApi.ltpData("NSE", f"{sym}-EQ", pos["token"])['data']['ltp']
            pnl = (ltp - pos['entry']) * (CAPITAL_PER_TRADE / pos['entry'])
            total_pnl += pnl
            msg += f"{sym}: {pnl:.0f} Rs\n"
        
        msg += f"\nTotal Trades: {total_trades_done}/6\nTotal P&L: {total_pnl:.0f} Rs\nActive: {active_trades}"
        send_telegram(msg)
    except: pass
