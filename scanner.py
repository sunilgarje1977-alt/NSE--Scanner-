import os, json, time
import pandas as pd
from SmartApi import SmartConnect
import pyotp
from datetime import datetime, timedelta

# Env from your scanner.yml - तुझेच नाव
API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PASSWORD = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")

# Login - Angel
obj = SmartConnect(api_key=API_KEY)
totp = pyotp.TOTP(TOTP_SECRET).now()
session = obj.generateSession(CLIENT_ID, PASSWORD, totp)
print(f"Angel Login: {session['status']}")

# --- NSE Smallcap Token List ---
# तुझ्या 5000.py मधून - आता 400 साठी हीच पद्धत
SYMBOL_TOKENS = {
    "BANDHANBNK": "22639", "WELCORP": "11483", "DPWIRES": "24755",
    "GROWW": "54323", "DMART": "10940", "PFOCUS": "5263"
    # TODO: तुझी 400 ची List इथे टाक - 5000.py मधून Copy कर
}

def get_data(token):
    try:
        params = {
            "exchange": "NSE", "symboltoken": token, "interval": "FIVE_MINUTE",
            "fromdate": (datetime.now()-timedelta(days=3)).strftime("%Y-%m-%d %H:%M"),
            "todate": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        data = obj.getCandleData(params)
        if not data or 'data' not in data or not data['data']:
            return None
        df = pd.DataFrame(data['data'], columns=['ts','open','high','low','close','volume'])
        df['ema9'] = df['close'].ewm(span=9).mean()
        df['ema15'] = df['close'].ewm(span=15).mean()
        df['vwap'] = (df['close']*df['volume']).cumsum()/df['volume'].cumsum()
        df['vol_avg20'] = df['volume'].rolling(20).mean()
        return df
    except Exception as e:
        print(f"Error {token}: {e}")
        return None

results = []
for sym, token in SYMBOL_TOKENS.items():
    df = get_data(token)
    if df is None or len(df) < 30:
        continue
    last = df.iloc[-1]
    prev = df.iloc[-2]

    # 1. Circuit Filter - DPWIRES सारखा - 15% वर NO TRADE
    if abs(last['close']/prev['close'] - 1) > 0.15:
        print(f"{sym}: ❌ CIRCUIT - Skip")
        continue

    # 2. Volume Filter - तू सांगितलास - 1.5x
    if last['volume'] < last['vol_avg20'] * 1.5:
        print(f"{sym}: ❌ Volume नाही - Skip")
        continue

    # 3. EMA VWAP Cross - DONE Rule
    long_cond = (last['ema9'] > last['vwap'] and last['ema15'] > last['vwap'] 
                 and last['ema9'] > last['ema15'] and last['close'] > last['vwap'])
    short_cond = (last['ema9'] < last['vwap'] and last['ema15'] < last['vwap']
                  and last['ema9'] < last['ema15'] and last['close'] < last['vwap'])

    if long_cond:
        results.append({"symbol": sym, "signal": "LONG", "price": round(last['close'],2)})
        print(f"{sym}: ✅ LONG")
    elif short_cond:
        results.append({"symbol": sym, "signal": "SHORT", "price": round(last['close'],2)})
        print(f"{sym}: 🔴 SHORT")
    else:
        print(f"{sym}: DONE - Cross नाही")

    time.sleep(0.4) # Angel Limit

# Telegram ला पाठव
if results:
    import requests
    msg = f"V51 Scanner - {len(results)} Signals:\n" + "\n".join([f"{r['symbol']} - {r['signal']} @ {r['price']}" for r in results])
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id": chat_id, "text": msg})

print(f"Final: {results}") 
