import os, time, requests, pyotp, yfinance as yf
import pandas as pd
from SmartApi import SmartConnect
from datetime import datetime

# Secrets
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN","").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID","").strip()
API_KEY = os.getenv("ANGEL_API_KEY","").strip()
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID","").strip()
PASSWORD = os.getenv("ANGEL_PASSWORD","").strip()
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET","").strip()

CAPITAL_PER_TRADE = 5000
MAX_TRADES_PER_DAY = 6
MAX_ACTIVE = 2
active_positions = {}
total_trades = 0

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try: requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode":"Markdown"}, timeout=15)
    except: pass
    print(msg)

def is_bullish_engulfing(df):
    c, p = df.iloc[-1], df.iloc[-2]
    return p['Close'] < p['Open'] and c['Close'] > c['Open'] and c['Open'] < p['Close'] and c['Close'] > p['Open']

def is_hammer(df):
    c = df.iloc[-1]
    body = abs(c['Close'] - c['Open'])
    lower_wick = min(c['Open'], c['Close']) - c['Low']
    upper_wick = c['High'] - max(c['Open'], c['Close'])
    return lower_wick > 2*body and upper_wick < body*0.5 and body > 0

def is_morning_star(df):
    if len(df) < 3: return False
    c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
    return c1['Close'] < c1['Open'] and abs(c2['Close']-c2['Open']) < (c1['High']-c1['Low'])*0.3 and c3['Close'] > c3['Open'] and c3['Close'] > (c1['Open']+c1['Close'])/2

def get_small_candle_sl(df):
    last5 = df.iloc[-6:-1]
    bodies = abs(last5['Close'] - last5['Open'])
    smallest_idx = bodies.idxmin()
    return float(df.loc[smallest_idx, 'Low'])

print("Login to Angel...")
smartApi = SmartConnect(api_key=API_KEY)
smartApi.generateSession(CLIENT_ID, PASSWORD, pyotp.TOTP(TOTP_SECRET).now())
print("Login OK!")

# SENSEX 1000 - इथे 100 टाकले आहेत, नंतर 1000 करू (Speed साठी)
STOCKS = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","BHARTIARTL","ITC","LT","KOTAKBANK","HINDUNILVR","AXISBANK","BAJFINANCE","MARUTI","ASIANPAINT","HCLTECH","SUNPHARMA","TITAN","ULTRACEMCO","WIPRO","NTPC","POWERGRID","M&M","ADANIENT","ONGC","COALINDIA","TATASTEEL","TECHM","HDFCLIFE","JSWSTEEL","GRASIM","ADANIPORTS","CIPLA","DRREDDY","TATAMOTORS","EICHERMOT","BRITANNIA","SHRIRAMFIN","HINDALCO","SBILIFE","INDUSINDBK","APOLLOHOSP","DIVISLAB","BPCL","TATACONSUM","LTIM","BAJAJ-AUTO","HEROMOTOCO","TRENT","BEL","VEDL","HAL","IRFC","ZOMATO","VBL","DMART","TATAPOWER","PIDILIT","SIEMENS","ABB","BHEL","SAIL","POLYCAB","COFORGE","PERSISTENT","LTTS","MPHASIS","CHOLAFIN","MUTHOOTFIN","RECLTD","PFC","GAIL","IOC","LICI","JIOFIN","ADANIPOWER","ADANIGREEN","NHPC","BANKBARODA","CANBK","PNB","INDIGO","SRF","DIXON","CUMMINSIND","BALKRISIND","ASTRAL","HINDZINC","NMDC","JINDALSTEL","TATACHEM","GODREJCP","DABUR","MARICO","COLPAL","UBL","MCDOWELL-N"]

breakouts = []
for i, symbol in enumerate(STOCKS, 1):
    try:
        if total_trades >= MAX_TRADES_PER_DAY: break
        if len(active_positions) >= MAX_ACTIVE: break
        print(f"{i}/{len(STOCKS)} {symbol}")

        # Daily Data
        df_daily = yf.Ticker(f"{symbol}.NS").history(period="60d", interval="1d")
        if len(df_daily) < 25: continue
        last = df_daily.iloc[-1]
        price = float(last['Close'])

        # 1. Price Filter 50-1500
        if not (50 <= price <= 1500): continue

        # 2. 2X Volume
        vol_avg = df_daily['Volume'].rolling(20).mean().iloc[-1]
        if last['Volume'] < 2 * vol_avg: continue

        # 3. First 15m High Break
        try:
            df_15m = yf.Ticker(f"{symbol}.NS").history(period="1d", interval="15m")
            if len(df_15m) > 1:
                first_15m_high = float(df_15m.iloc[0]['High'])
                if price <= first_15m_high: continue
        except: first_15m_high = 0

        # 4. 3 Patterns
        pattern = None
        if is_bullish_engulfing(df_daily): pattern = "Engulfing"
        elif is_hammer(df_daily): pattern = "Hammer"
        elif is_morning_star(df_daily): pattern = "MorningStar"
        else: continue

        # 5. Small Candle SL
        sl = get_small_candle_sl(df_daily)
        # 6. SL Filter 3.5%
        sl_dist_pct = (price - sl) / price * 100
        if sl_dist_pct > 3.5:
            sl = float(df_daily.iloc[-2]['Low'])

        # 7. Target 1:2
        target = price + (price - sl) * 2

        # 8. Trailing SL 30%
        # Entry
        if symbol not in active_positions:
            active_positions[symbol] = {"entry": price, "sl": sl, "target": target, "high": price, "pattern": pattern}
            total_trades += 1
            breakouts.append(f"{symbol} | {price:.0f} | {pattern} | SL:{sl:.0f} TGT:{target:.0f}")
            print(f" FOUND {symbol}")

    except Exception as e:
        print(f" Err {symbol}: {e}")
    time.sleep(0.15)

# 11. Daily P&L Report 3:30
pnl_text = ""
total_pnl = 0
for sym, pos in active_positions.items():
    try:
        live = float(yf.Ticker(f"{sym}.NS").history(period="1d")['Close'].iloc[-1])
        pnl = (live - pos['entry']) * (CAPITAL_PER_TRADE // pos['entry'])
        total_pnl += pnl
        # Trailing SL 30%
        if live > pos['high']:
            pos['high'] = live
            pos['sl'] = pos['high'] * 0.70
        pnl_text += f"\n• {sym}: {pnl:+.0f} Rs"
    except: pass

if breakouts:
    msg = f"🚀 *SENSEX 1000 Scanner - {len(breakouts)} Found*\n\n" + "\n".join([f"• {b}" for b in breakouts]) + f"\n\n*Capital:* 5000/Trade | Max 6/Day\n*Active:* {len(active_positions)}/2\n*P&L:* {total_pnl:.0f} Rs {pnl_text}\n\n_SL 3.5% Filter + 1:2 Target_"
else:
    msg = f"📊 *Daily 3:30 Report*\n\n{len(STOCKS)} Stocks स्कॅन\nआज Pattern Match नाही\nActive: {len(active_positions)} | Total: {total_trades}\nP&L: {total_pnl:.0f} Rs"

send_telegram(msg)
print("Done!")
