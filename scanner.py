from SmartApi import SmartConnect
import pyotp
import pandas as pd
import json, os
from datetime import datetime, timedelta

# --- ANGEL KEY - इथे तुझी Key टाक ---
API_KEY = os.getenv("ANGEL_API_KEY")  # GitHub Secret मधून येईल
CLIENT_CODE = os.getenv("ANGEL_CLIENT_CODE")
PASSWORD = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")

# Login
obj = SmartConnect(api_key=API_KEY)
totp = pyotp.TOTP(TOTP_SECRET).now()
session = obj.generateSession(CLIENT_CODE, PASSWORD, totp)
print("Login:", session['message'])

# NSE Smallcap 400 Tokens - तुझ्या 5000.py मधून घे
# हा File मी तुझ्या Repo वरून घेतला
try:
    with open('trades_state.json','r') as f:
        TOKENS = json.load(f)
except:
    # Demo - तुझे 10 Symbols
    TOKENS = {"BANDHANBNK": "22639", "WELCORP": "11483", "DPWIRES": "24755"}

def get_data(token):
    param = {
        "exchange": "NSE", "symboltoken": token, "interval": "FIVE_MINUTE",
        "fromdate": (datetime.now()-timedelta(days=2)).strftime("%Y-%m-%d %H:%M"),
        "todate": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    data = obj.getCandleData(param)
    if not data['data']: return None
    df = pd.DataFrame(data['data'], columns=['ts','o','h','l','c','v'])
    df['ema9'] = df['c'].ewm(span=9).mean()
    df['ema15'] = df['c'].ewm(span=15).mean()
    df['vwap'] = (df['c']*df['v']).cumsum()/df['v'].cumsum()
    df['vol20'] = df['v'].rolling(20).mean()
    return df

# Scan Start
results = []
for sym, token in TOKENS.items():
    df = get_data(token)
    if df is None or len(df)<30: continue
    last = df.iloc[-1]
    prev = df.iloc[-2]

    # 1. Circuit - DPWIRES Filter
    if abs(last['c']/prev['c']-1) > 0.15:
        continue  # DONE - Cross नाही

    # 2. Volume Check - तू सांगितलास
    if last['v'] < last['vol20']*1.5:
        continue  # Volume नाही

    # 3. EMA VWAP Cross - तुझा Main Rule
    long_c = last['ema9']>last['vwap'] and last['ema15']>last['vwap'] and last['ema9']>last['ema15'] and last['c']>last['vwap']
    short_c = last['ema9']<last['vwap'] and last['ema15']<last['vwap'] and last['ema9']<last['ema15'] and last['c']<last['vwap']

    if long_c:
        results.append({"symbol": sym, "signal": "LONG", "price": last['c'], "sl": last['vwap']*0.995})
    elif short_c:
        results.append({"symbol": sym, "signal": "SHORT", "price": last['c'], "sl": last['vwap']*1.005})

# Save
pd.DataFrame(results).to_csv("today_signals.csv", index=False)
print(f"Done: {len(results)} signals - {results}")
