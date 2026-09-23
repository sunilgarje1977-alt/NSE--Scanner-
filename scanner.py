import os, time, requests
from datetime import datetime, timedelta
import pandas as pd
import talib, pyotp
from SmartApi import SmartConnect
from concurrent.futures import ThreadPoolExecutor

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
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except: pass

# ===== LOGIN =====
smartApi = SmartConnect(api_key=API_KEY)
smartApi.generateSession(CLIENT_ID, PASSWORD, pyotp.TOTP(TOTP_SECRET).now())
print("Login Success")

def get_candles(token, interval, days=20):
    try:
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        param = {"exchange":"NSE","symboltoken":token,"interval":interval,
                 "fromdate":from_date.strftime("%Y-%m-%d %H:%M"),
                 "todate":to_date.strftime("%Y-%m-%d %H:%M")}
        data = smartApi.getCandleData(param)
        return pd.DataFrame(data['data'], columns=['timestamp','open','high','low','close','volume'])
    except: return None

def check_rocket_stock(df_15, df_daily):
    try:
        price = df_15['close'].iloc[-1]
        if not (50 <= price <= 1500): return None
        avg_vol = df_daily['volume'].rolling(20).mean().iloc[-1]
        if df_daily['volume'].iloc[-1] < 2 * avg_vol: return None
        if price <= df_15['high'].iloc[0]: return None

        o,h,l,c = df_15['open'], df_15['high'], df_15['low'], df_15['close']
        if not (talib.CDLENGULFING(o,h,l,c).iloc[-1]==100 or talib.CDLHAMMER(o,h,l,c).iloc[-1]==100 or talib.CDLMORNINGSTAR(o,h,l,c).iloc[-1]==100):
            return None

        prev = df_15.iloc[-6:-1].copy()
        prev['body'] = abs(prev['close'] - prev['open'])
        sl = prev.loc[prev['body'].idxmin(), 'low']
        if (price - sl)*100/price > 3.5: sl = df_15['low'].iloc[-2]
        target = price + (price - sl)*2
        return {"price": price, "sl": round(sl,2), "target": round(target,2)}
    except: return None

def place_order_final(symbol, info, token):
    global active_trades, total_trades_done
    if active_trades >= ACTIVE_LIMIT or total_trades_done >= MAX_TRADES: return
    qty = max(1, int(CAPITAL_PER_TRADE / info['price']))
    active_positions[symbol] = {"entry": info['price'], "sl": info['sl'], "target": info['target'], "high": info['price'], "token": token}
    active_trades += 1
    total_trades_done += 1
    send_telegram(f"🚀 BUY {symbol} @ {info['price']}\nSL: {info['sl']} TGT: {info['target']} Qty:{qty}")

def trail_sl_logic():
    global active_trades
    for sym in list(active_positions.keys()):
        try:
            pos = active_positions[sym]
            ltp = smartApi.ltpData("NSE", f"{sym}-EQ", pos["token"])['data']['ltp']
            if ltp > pos["high"]: pos["high"] = ltp
            trail_sl = pos["high"] - (pos["high"]-pos["entry"])*0.3
            if ltp <= pos["sl"] or ltp <= trail_sl or ltp >= pos["target"]:
                send_telegram(f"✅ EXIT {sym} @ {ltp}")
                del active_positions[sym]
                active_trades -= 1
        except: pass

def daily_report():
    try:
        total_pnl = 0
        msg = "📊 *आजचा SENSEX 1000 Report*\n\n"
        for sym, pos in active_positions.items():
            ltp = smartApi.ltpData("NSE", f"{sym}-EQ", pos["token"])['data']['ltp']
            pnl = (ltp - pos['entry']) * (CAPITAL_PER_TRADE / pos['entry'])
            total_pnl += pnl
            msg += f"{sym}: {pnl:.0f} Rs\n"
        msg += f"\nTotal Trades: {total_trades_done}/6\nTotal P&L: {total_pnl:.0f} Rs"
        send_telegram(msg)
    except: pass

def load_1000_stocks():
    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    data = requests.get(url).json()
    stocks = []
    for item in data:
        if item['exch_seg']=='NSE' and item['symbol'].endswith('-EQ') and item['instrumenttype']=='':
            stocks.append({"symbol": item['name'], "token": item['token']})
        if len(stocks) >= 1000: break
    return stocks

ALL_STOCKS = load_1000_stocks()

def scan_one(stock):
    if stock["symbol"] in active_positions: return
    if active_trades >= ACTIVE_LIMIT: return
    df_15 = get_candles(stock["token"], "FIFTEEN_MINUTE", 2)
    df_daily = get_candles(stock["token"], "ONE_DAY", 30)
    if df_15 is None or len(df_15)<20: return
    result = check_rocket_stock(df_15, df_daily)
    if result:
        place_order_final(stock["symbol"], result, stock["token"])

def main():
    send_telegram("✅ SENSEX 1000 Scanner LIVE: 30k | 6 Trades | 3:30 Report")
    while True:
        if 9 <= datetime.now().hour <= 15:
            with ThreadPoolExecutor(max_workers=10) as executor:
                executor.map(scan_one, ALL_STOCKS)
        trail_sl_logic()
        now = datetime.now()
        if now.hour == 15 and now.minute == 30:
            daily_report()
            time.sleep(70)
        time.sleep(120)

if __name__ == "__main__":
    main()
