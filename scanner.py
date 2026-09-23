import os, time, requests, pyotp, logzero
import pandas as pd
from datetime import datetime, timedelta
from SmartApi import SmartConnect

# Secrets मधून Key घेणार
API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PASSWORD = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

smart = SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PASSWORD, pyotp.TOTP(TOTP_SECRET).now())

def send_tg(msg):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def is_strong(df):
    l, p = df.iloc[-1], df.iloc[-2]
    body = abs(l['close']-l['open'])
    rng = l['high']-l['low']
    if rng==0: return False
    return (body/rng>0.7 and l['close']>l['open']) or (p['close']<p['open'] and l['close']>l['open'] and l['close']>p['open'])

def get_candles(token, interval, days):
    to_date = datetime.now()
    from_date = to_date - timedelta(days=days)
    params = {"exchange":"NSE","symboltoken":token,"interval":interval,"fromdate":from_date.strftime("%Y-%m-%d %H:%M"),"todate":to_date.strftime("%Y-%m-%d %H:%M")}
    try:
        data = smart.getCandleData(params)
        return pd.DataFrame(data['data'], columns=['datetime','open','high','low','close','volume'])
    except: return pd.DataFrame()

def scan(symbol, token):
    df5 = get_candles(token, "FIVE_MINUTE", 2)
    dfd = get_candles(token, "ONE_DAY", 60)
    if len(df5)<10 or len(dfd)<30: return
    today = datetime.now().strftime("%Y-%m-%d")
    df5['datetime']=pd.to_datetime(df5['datetime'])
    dft = df5[df5['datetime'].dt.strftime("%Y-%m-%d")==today]
    if len(dft)<4: return
    
    curr = dft.iloc[-1]['close']
    first3_high = dft.iloc[0:3]['high'].max() # 9:15, 9:20, 9:25
    cond1 = curr > first3_high # 9:15 Breakout
    cond2 = dfd['volume'].iloc[-1] > dfd['volume'].iloc[-21:-1].mean()*2 # 2x Vol
    ema9 = dfd['close'].ewm(span=9).mean()
    ema21 = dfd['close'].ewm(span=21).mean()
    cond3 = ema9.iloc[-1] > ema21.iloc[-1] # 9>21
    dft['vwap'] = (dft['close']*dft['volume']).cumsum()/dft['volume'].cumsum()
    cond4 = curr > dft.iloc[-1]['vwap']
    delta = dfd['close'].diff()
    rsi = 100 - (100/(1+delta.where(delta>0,0).rolling(14).mean() / -delta.where(delta<0,0).rolling(14).mean()))
    cond5 = rsi.iloc[-1] > 55
    cond6 = is_strong(dft)
    
    if all([cond1,cond2,cond3,cond4,cond5,cond6]):
        send_tg(f"🚀 *{symbol}* 9:15 BREAKOUT\nPrice: {curr}\nVol 2x | RSI {rsi.iloc[-1]:.1f}\nStrong Candle + VWAP Above")
        print(symbol)

# तुझी NSE List - इथे Token टाक
for s in [{"symbol":"SAIL","token":"758"},{"symbol":"BHEL","token":"438"}]:
    scan(s["symbol"], s["token"])
    time.sleep(0.4)
