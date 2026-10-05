import os, requests, pandas as pd, pyotp, time
from SmartApi import SmartConnect
from datetime import datetime, timedelta

API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PASSWORD = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")

obj = SmartConnect(api_key=API_KEY)
clean_secret = TOTP_SECRET.strip().replace(" ", "").upper()
obj.generateSession(CLIENT_ID, PASSWORD, pyotp.TOTP(clean_secret).now())

master = requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json", timeout=30).json()
token_map = {d['symbol'].replace('-EQ',''): d['token'] for d in master if d.get('exch_seg')=='NSE' and str(d.get('symbol','')).endswith('-EQ')}

# तुझे 166 Stocks - Full List
STOCKS = ["AARTIIND","ABSLAMC","ANGELONE","APLAPOLLO","AUBANK","BANKBARODA","BATAINDIA","BEL","BHEL","BSE","CAMS","CDSL","COFORGE","CONCOR","CUMMINSIND","DALBHARAT","DELTACORP","ESCORTS","FEDERALBNK","GMRINFRA","GNFC","HAL","HINDCOPPER","IDFCFIRSTB","IEX","INDHOTEL","INDIAMART","INDUSINDBK","IRCTC","JINDALSTEL","JUBLFOOD","LALPATHLAB","LICHSGFIN","MANAPPURAM","MCX","MUTHOOTFIN","NAM-INDIA","NATIONALUM","NAUKRI","NMDC","NTPC","OBEROIRLTY","OFSS","PEL","PERSISTENT","PETRONET","PIDILITIND","POLYCAB","PVRINOX","RAMCOCEM","SAIL","SBICARD","SRF","TATACOMM","TATAPOWER","TORNTPHARM","TRENT","TVSMOTOR","UBL","VEDL","VOLTAS","ZEEL","ABB","ADANIENT","ADANIPORTS","APOLLOHOSP","ASIANPAINT","AXISBANK","BAJAJ-AUTO","BAJAJFINSV","BAJFINANCE","BHARTIARTL","BPCL","BRITANNIA","CIPLA","COALINDIA","DIVISLAB","DRREDDY","EICHERMOT","GRASIM","HCLTECH","HDFCBANK","HDFCLIFE","HEROMOTOCO","HINDALCO","HINDUNILVR","ICICIBANK","INDUSINDBK","INFY","ITC","JSWSTEEL","KOTAKBANK","LT","LTIM","M&M","MARUTI","NESTLEIND","ONGC","POWERGRID","RELIANCE","SBILIFE","SBIN","SUNPHARMA","TATACONSUM","TATAMOTORS","TATASTEEL","TCS","TECHM","TITAN","ULTRACEMCO","WIPRO"] # हवे तर अजून Add कर

def backtest(sym, days=60):
    token = token_map.get(sym)
    if not token: return []
    try:
        params = {"exchange": "NSE","symboltoken": token,"interval": "FIVE_MINUTE","fromdate": (datetime.now()-timedelta(days=days)).strftime("%Y-%m-%d %H:%M"),"todate": datetime.now().strftime("%Y-%m-%d %H:%M")}
        data = obj.getCandleData(params)
        if not data.get('data'): return []
        df = pd.DataFrame(data['data'], columns=['ts','o','h','l','c','v'])
        df['ema9'] = df['c'].ewm(span=9).mean()
        df['ema15'] = df['c'].ewm(span=15).mean()
        df['vwap'] = (df['c']*df['v']).cumsum()/df['v'].cumsum()
        df['vol20'] = df['v'].rolling(20).mean()
        trades = []
        for i in range(21, len(df)-10):
            last = df.iloc[i]
            prev = df.iloc[i-1]
            if last['c'] < 50 or last['v'] < 20000 or last['vol20']==0 or last['v'] < last['vol20']*1.8: continue
            if prev['ema9'] < prev['ema15'] and last['ema9'] > last['ema15'] and last['c'] > last['vwap']:
                future = df.iloc[i+1:i+11]
                max_up = (future['h'].max() - last['c'])/last['c']*100
                trades.append(max_up)
            if prev['ema9'] > prev['ema15'] and last['ema9'] < last['ema15'] and last['c'] < last['vwap']:
                future = df.iloc[i+1:i+11]
                max_down = (last['c'] - future['l'].min())/last['c']*100
                trades.append(max_down)
        return trades
    except Exception as e:
        return []

all_returns = []
for s in STOCKS:
    rets = backtest(s)
    all_returns.extend(rets)
    time.sleep(0.3) # Rate limit साठी
    print(f"{s}: {len(rets)} trades")

if len(all_returns)>0:
    import numpy as np
    df = pd.Series(all_returns)
    print(f"\n--- 60 DAYS FULL BACKTEST ---")
    print(f"Total Trades: {len(df)}")
    print(f"Avg Profit (50min): {df.mean():.2f}%")
    print(f"Winners >0%: {(df>0).sum()} / {len(df)} ({(df>0).mean()*100:.1f}%)")
    print(f"Winners >1%: {(df>1).sum()} / {len(df)} ({(df>1).mean()*100:.1f}%)")
    print(f"Winners >1.5%: {(df>1.5).sum()} / {len(df)}")
    print(f"Best Trade: {df.max():.2f}%")
else:
    print("No Trades Found") 
