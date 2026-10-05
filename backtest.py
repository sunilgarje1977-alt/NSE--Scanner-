import pandas as pd, pyotp, requests
from SmartApi import SmartConnect
from datetime import datetime, timedelta
import os

# --- तुझे Keys इथे टाक ---
API_KEY = "तुझा API KEY"
CLIENT_ID = "तुझा CLIENT ID"
PASSWORD = "तुझा PASSWORD"
TOTP_SECRET = "तुझा TOTP SECRET"

obj = SmartConnect(api_key=API_KEY)
obj.generateSession(CLIENT_ID, PASSWORD, pyotp.TOTP(TOTP_SECRET).now())

master = requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json", timeout=30).json()
token_map = {d['symbol'].replace('-EQ',''): d['token'] for d in master if d.get('exch_seg')=='NSE' and str(d.get('symbol','')).endswith('-EQ')}

STOCKS = ["AARTIIND","ABSLAMC","ANGELONE","BEL","BSE","CAMS","CDSL","COFORGE","HAL","IEX","BANKBARODA","BHEL"] # Test साठी 12 टाकलेत, हवे तर 166 टाक

def backtest(sym, days=5):
    token = token_map.get(sym)
    if not token: return []
    params = {"exchange": "NSE","symboltoken": token,"interval": "FIVE_MINUTE","fromdate": (datetime.now()-timedelta(days=days)).strftime("%Y-%m-%d %H:%M"),"todate": datetime.now().strftime("%Y-%m-%d %H:%M")}
    data = obj.getCandleData(params)
    if not data.get('data'): return []
    df = pd.DataFrame(data['data'], columns=['ts','o','h','l','c','v'])
    df['ema9'] = df['c'].ewm(span=9).mean()
    df['ema15'] = df['c'].ewm(span=15).mean()
    df['vwap'] = (df['c']*df['v']).cumsum()/df['v'].cumsum()
    df['vol20'] = df['v'].rolling(20).mean()

    trades = []
    for i in range(21, len(df)):
        last = df.iloc[i]
        prev = df.iloc[i-1]
        if last['c'] < 50: continue
        if last['v'] < 20000: continue
        if last['v'] < last['vol20']*1.8: continue

        if prev['ema9'] < prev['ema15'] and last['ema9'] > last['ema15'] and last['c'] > last['vwap']:
            # पुढच्या 10 Candle मध्ये किती Profit?
            future = df.iloc[i+1:i+11]
            if len(future)>0:
                max_up = (future['h'].max() - last['c'])/last['c']*100
                trades.append([sym, "LONG", round(last['c'],2), round(max_up,2)])

        if prev['ema9'] > prev['ema15'] and last['ema9'] < last['ema15'] and last['c'] < last['vwap']:
            future = df.iloc[i+1:i+11]
            if len(future)>0:
                max_down = (last['c'] - future['l'].min())/last['c']*100
                trades.append([sym, "SHORT", round(last['c'],2), round(max_down,2)])
    return trades

all_trades = []
for s in STOCKS:
    all_trades.extend(backtest(s))

df_result = pd.DataFrame(all_trades, columns=['Stock','Side','Entry','Max_Profit_%_in_50min'])
print(df_result)
print(f"\nTotal Trades: {len(df_result)}")
if len(df_result)>0:
    print(f"Avg Profit Potential: {df_result['Max_Profit_%_in_50min'].mean():.2f}%")
    print(f"Winners >1%: {(df_result['Max_Profit_%_in_50min']>1).sum()} / {len(df_result)}")
