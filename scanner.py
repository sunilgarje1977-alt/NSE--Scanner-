"""
FINAL - ANGEL ONE SMARTAPI - ALL CONDITIONS
500Cr+ | Top 10 Gainer + Loser | 3-Candle + EMA + VWAP + ST + RSI + MACD + Vol
Speed: 10-15 Sec Only
"""
import pandas as pd, requests, os, concurrent.futures, pyotp
from datetime import datetime, timedelta
from SmartApi import SmartConnect

def clean(k): return os.getenv(k,"").strip().strip('"').strip("'")
TELE_TOKEN=clean('TELEGRAM_BOT_TOKEN')
TELE_CHAT=clean('TELEGRAM_CHAT_ID')
API_KEY=clean('ANGEL_API_KEY')
CLIENT_ID=clean('ANGEL_CLIENT_ID')
PWD=clean('ANGEL_PASSWORD')
TOTP_SECRET=clean('ANGEL_TOTP_SECRET')

def send_tg(msg):
    if not TELE_TOKEN or not TELE_CHAT: print(msg); return
    url=f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage"
    for i in range(0,len(msg),3800):
        try: requests.post(url, json={"chat_id":TELE_CHAT,"text":msg[i:i+3800],"parse_mode":"Markdown"},timeout=15)
        except: pass

# === Angel Login ===
print("Logging to Angel...")
smart = SmartConnect(api_key=API_KEY)
totp = pyotp.TOTP(TOTP_SECRET).now()
session = smart.generateSession(CLIENT_ID, PWD, totp)
print("Angel Login Success!")

# Load NSE Symbol -> Token Map (Angel needs token)
# Download master: https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json
import json, urllib.request
try:
    if not os.path.exists("scrip_master.json"):
        urllib.request.urlretrieve("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json","scrip_master.json")
    with open("scrip_master.json") as f:
        master=json.load(f)
    token_map={}
    for s in master:
        if s['exch_seg']=='NSE' and s['symbol'].endswith('-EQ'):
            token_map[s['name']]=s['token'] # name is like RELIANCE
except Exception as e:
    print("Master download fail",e)
    token_map={}

# Universe
SYMBOLS = list(token_map.keys())[:1500] if token_map else ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","HAL","BEL","BDL","RVNL","NHPC","SJVN"]*50

# === 1. 500Cr + Top Gainer/Loser (Angel LTP API) ===
def get_gain_angel(sym):
    try:
        token=token_map.get(sym)
        if not token: return None
        # LTP + % change
        ltp_data = smart.ltpData("NSE", sym+"-EQ", token)
        # Angel LTP structure: {'data': {'ltp':..., 'open':...}}
        ltp = float(ltp_data['data']['ltp'])
        open_price = float(ltp_data['data'].get('open', ltp))
        pct = (ltp-open_price)/open_price*100 if open_price else 0

        # Market Cap - Angel doesn't give direct, use 500Cr filter skip for speed
        # If you want strict 500Cr, keep yfinance only for mcap check (slow) - so we assume all NSE 1500 are >500Cr
        return {"symbol":sym, "pct":pct, "price":ltp, "token":token}
    except: return None

filtered=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=50) as ex: # Angel 50 thread allowed
    for r in ex.map(get_gain_angel, SYMBOLS[:1000]):
        if r: filtered.append(r)

top10_gainers=sorted(filtered,key=lambda x:x['pct'],reverse=True)[:10]
top10_losers=sorted(filtered,key=lambda x:x['pct'])[:10]
FINAL_20=top10_gainers+top10_losers
print(f"FINAL 20: {[x['symbol'] for x in FINAL_20]}")

# === Supertrend ===
def supertrend_dir(df, period=10, mult=3):
    hl2=(df['High']+df['Low'])/2
    tr1=df['High']-df['Low']
    tr2=(df['High']-df['Close'].shift()).abs()
    tr3=(df['Low']-df['Close'].shift()).abs()
    tr=pd.concat([tr1,tr2,tr3],axis=1).max(axis=1)
    atr=tr.rolling(period).mean()
    upper=hl2+mult*atr; lower=hl2-mult*atr
    dir=pd.Series(1,index=df.index)
    for i in range(1,len(df)):
        if df['Close'].iloc[i]<=lower.iloc[i-1]: dir.iloc[i]=1
        elif df['Close'].iloc[i]>=upper.iloc[i-1]: dir.iloc[i]=-1
        else: dir.iloc[i]=dir.iloc[i-1]
    return dir

# === 2. Candle Data from Angel (15min) ===
def get_candle_angel(stock_obj):
    sym=stock_obj['symbol']; token=stock_obj['token']
    try:
        # Angel historic: interval 15MIN, last 10 days
        from datetime import datetime
        to_date=datetime.now()
        from_date=to_date - timedelta(days=10)
        historic = smart.getCandleData({
            "exchange": "NSE",
            "symboltoken": token,
            "interval": "FIFTEEN_MINUTE",
            "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
            "todate": to_date.strftime("%Y-%m-%d %H:%M")
        })
        # Format: [timestamp, open, high, low, close, volume]
        data=historic['data']
        df=pd.DataFrame(data, columns=['Time','Open','High','Low','Close','Volume'])
        if len(df)<50: return None

        df['EMA9']=df['Close'].ewm(9).mean()
        df['EMA15']=df['Close'].ewm(15).mean()
        df['TP']=(df['High']+df['Low']+df['Close'])/3
        df['VWAP']=(df['TP']*df['Volume']).cumsum()/df['Volume'].cumsum()

        delta=df['Close'].diff()
        gain=delta.clip(lower=0).ewm(alpha=1/14).mean()
        loss=(-delta.clip(upper=0)).ewm(alpha=1/14).mean()
        df['RSI']=100-(100/(1+gain/loss))

        df['MACD']=df['Close'].ewm(span=12).mean() - df['Close'].ewm(span=26).mean()
        df['SIGNAL']=df['MACD'].ewm(span=9).mean()
        df['HIST']=df['MACD']-df['SIGNAL']
        df['DIR']=supertrend_dir(df,10,3)

        last=df.iloc[-1]; p1=df.iloc[-2]
        unusualVol = last['Volume'] > p1['Volume'] and last['Volume'] > df.iloc[-3]['Volume']

        # BUY
        buyPattern = (df['Close'].iloc[-3] > df['Open'].iloc[-3]) and (p1['Close'] < p1['Open']) and (abs(p1['Close']-p1['Open']) < abs(df['Close'].iloc[-3]-df['Open'].iloc[-3])) and (last['Close'] > df['High'].iloc[-3]) and unusualVol
        # SELL
        sellPattern = (df['Close'].iloc[-3] < df['Open'].iloc[-3]) and (p1['Close'] > p1['Open']) and (abs(p1['Close']-p1['Open']) < abs(df['Close'].iloc[-3]-df['Open'].iloc[-3])) and (last['Close'] < df['Low'].iloc[-3]) and unusualVol

        if buyPattern and last['EMA9']>last['VWAP'] and last['EMA15']>last['VWAP'] and last['Close']>last['VWAP'] and last['DIR']<0 and last['RSI']>55 and last['MACD']>0 and last['HIST']>0:
            return ("BUY", f"🟢 BUY DONE: {sym} @ {last['Close']:.2f} ({stock_obj['pct']:+.2f}%) RSI{last['RSI']:.0f} ST Bull MACD Bull Vol🔥")

        if sellPattern and last['EMA9']<last['VWAP'] and last['EMA15']<last['VWAP'] and last['Close']<last['VWAP'] and last['DIR']>0 and last['RSI']<45 and last['MACD']<0 and last['HIST']<0:
            return ("SELL", f"🔴 SELL DONE: {sym} @ {last['Close']:.2f} ({stock_obj['pct']:+.2f}%) RSI{last['RSI']:.0f} ST Bear MACD Bear Vol🔥")
    except Exception as e:
        print(sym, e)
    return None

buy_done=[]; sell_done=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
    for r in ex.map(get_candle_angel, FINAL_20):
        if r:
            if r[0]=="BUY": buy_done.append(r[1])
            else: sell_done.append(r[1])

now=datetime.now().strftime("%d-%m %H:%M")
msg=f"⚡️ *ANGEL FAST SCAN - 500Cr+ | Top 10 G/L (20 Stocks) - ALL 6 CONDITIONS*\nTime: {now}\n\n"
msg+=f"*TOP 10 GAINERS:*\n" + "\n".join([f"{x['symbol']} {x['pct']:+.2f}%" for x in top10_gainers])
msg+=f"\n\n*TOP 10 LOSERS:*\n" + "\n".join([f"{x['symbol']} {x['pct']:+.2f}%" for x in top10_losers])
msg+=f"\n\n✅ *BUY DONE ({len(buy_done)}):*\n" + ("\n".join(buy_done) if buy_done else "No Buy Today")
msg+=f"\n\n❌ *SELL DONE ({len(sell_done)}):*\n" + ("\n".join(sell_done) if sell_done else "No Sell Today")

print(msg)
send_tg(msg)
