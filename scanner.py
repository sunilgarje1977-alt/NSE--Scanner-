import os, json, pyotp, urllib.request, pandas as pd, requests
from datetime import datetime
from SmartApi import SmartConnect

def clean(k): return os.getenv(k,"").strip().strip('"').strip("'")
API_KEY=clean('ANGEL_API_KEY'); CLIENT_ID=clean('ANGEL_CLIENT_ID'); PWD=clean('ANGEL_PASSWORD'); TOTP_SECRET=clean('ANGEL_TOTP_SECRET')
TELE_TOKEN=clean('TELEGRAM_BOT_TOKEN'); TELE_CHAT=clean('TELEGRAM_CHAT_ID')

smart=SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID,PWD,pyotp.TOTP(TOTP_SECRET).now())

def send_tg(msg):
    try: requests.get(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", params={"chat_id":TELE_CHAT, "text":msg, "parse_mode":"Markdown"}, timeout=10)
    except: pass

if not os.path.exists("scrip_master.json"):
    urllib.request.urlretrieve("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json","scrip_master.json")
with open("scrip_master.json") as f: master=json.load(f)
token_map={s['name']:s['token'] for s in master if s['exch_seg']=='NSE' and s['symbol'].endswith('-EQ')}

# ===== FAST NSE GAINERS/LOSERS =====
def get_nse_top_movers():
    try:
        headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"}
        s=requests.Session()
        s.get("https://www.nseindia.com", headers=headers, timeout=5)
        gain=s.get("https://www.nseindia.com/api/live-analysis-variations?index=gainers", headers=headers, timeout=5).json()
        lose=s.get("https://www.nseindia.com/api/live-analysis-variations?index=losers", headers=headers, timeout=5).json()
        g=[x['symbol'] for x in gain['NIFTY']['data'][:25]] if 'NIFTY' in gain else []
        l=[x['symbol'] for x in lose['NIFTY']['data'][:25]] if 'NIFTY' in lose else []
        if g: return g+l
    except: pass
    # Fallback - Hardcoded Large+Mid+Small Top Volume
    return ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","HAL","BEL","BDL","RVNL","NHPC","PFC","RECLTD","IRFC","TATASTEEL","BHARTIARTL","ITC","LT","M&M","SBIN","ADANIENT","ADANIPORTS","TATAPOWER","TATAMOTORS","ZOMATO","PAYTM","IRCTC","VBL","TITAN","DMART","BAJFINANCE"]

def check_fast(symbol):
    try:
        token=token_map.get(symbol)
        if not token: return None
        data=smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIFTEEN_MINUTE","fromdate":(datetime.now()-pd.Timedelta(days=4)).strftime("%Y-%m-%d %H:%M"),"todate":datetime.now().strftime("%Y-%m-%d %H:%M")})['data']
        df=pd.DataFrame(data, columns=['Time','Open','High','Low','Close','Volume'])
        if len(df)<40: return None
        df['EMA9']=df['Close'].ewm(9).mean(); df['EMA15']=df['Close'].ewm(15).mean()
        df['TP']=(df['High']+df['Low']+df['Close'])/3; df['VWAP']=(df['TP']*df['Volume']).cumsum()/df['Volume'].cumsum()
        delta=df['Close'].diff(); gain=delta.clip(lower=0).ewm(alpha=1/14).mean(); loss=(-delta.clip(upper=0)).ewm(alpha=1/14).mean()
        df['RSI']=100-(100/(1+gain/loss)); df['MACD']=df['Close'].ewm(12).mean()-df['Close'].ewm(26).mean()
        hl2=(df['High']+df['Low'])/2; tr=pd.concat([(df['High']-df['Low']),(df['High']-df['Close'].shift()).abs(),(df['Low']-df['Close'].shift()).abs()],axis=1).max(axis=1)
        atr=tr.rolling(10).mean(); lower=hl2-3*atr; upper=hl2+3*atr
        sdir=-1 if df['Close'].iloc[-1]>=upper.iloc[-2] else 1

        c=df.iloc[-1]; c3h=df['High'].iloc[-4:-1].max(); c3l=df['Low'].iloc[-4:-1].min()
        vol_avg=df['Volume'].iloc[-11:-1].mean()

        buy_score=sum([c['Close']>c3h, c['EMA9']>c['VWAP'], c['EMA15']>c['VWAP'], sdir<0, c['RSI']>55, df['MACD'].iloc[-1]>0, c['Volume']>vol_avg*1.1])
        sell_score=sum([c['Close']<c3l, c['EMA9']<c['VWAP'], c['EMA15']<c['VWAP'], sdir>0, c['RSI']<45, df['MACD'].iloc[-1]<0, c['Volume']>vol_avg*1.1])

        ltp=c['Close']; atr_v=atr.iloc[-1]
        if buy_score>=5:
            sl=min(c3l, ltp-atr_v*1.5); r=ltp-sl
            return {"type":"BUY","sym":symbol,"sc":buy_score,"ltp":ltp,"sl":sl,"t1":ltp+r*2,"t2":ltp+r*5}
        if sell_score>=5:
            sl=max(c3h, ltp+atr_v*1.5); r=sl-ltp
            return {"type":"SELL","sym":symbol,"sc":sell_score,"ltp":ltp,"sl":sl,"t1":ltp-r*2,"t2":ltp-r*5}
    except: return None

# ===== MAIN FAST =====
movers=get_nse_top_movers() # 50 Stocks - 2 Sec मध्ये
print(f"Checking: {movers[:5]}...")

buys=[]; sells=[]
for sym in movers[:40]: # फक्त 40 वर Check
    res=check_fast(sym)
    if res:
        if res['type']=='BUY' and len(buys)<10: buys.append(res)
        if res['type']=='SELL' and len(sells)<10: sells.append(res)

msg=f"⚡ *FAST NSE 750 | {datetime.now().strftime('%H:%M')}*\n_Large+Mid+Small Top Gainers/Losers_\n"

if buys:
    msg+="\n🟢 *BUY (3 Candle BO + 5/7)*\n"
    for r in buys: msg+=f"\nBUY {r['sym']} {r['sc']}/7 E:{r['ltp']:.1f} SL:{r['sl']:.1f} T1:{r['t1']:.1f} [50%] T2:{r['t2']:.1f} [Trail]"
else: msg+="\n🟢 BUY - No Match\n"

if sells:
    msg+="\n\n🔴 *SELL (3 Candle BD + 5/7)*\n"
    for r in sells: msg+=f"\nSELL {r['sym']} {r['sc']}/7 E:{r['ltp']:.1f} SL:{r['sl']:.1f} T1:{r['t1']:.1f} [50%] T2:{r['t2']:.1f} [Trail]"
else: msg+="\n\n🔴 SELL - No Match\n"

msg+="\n\n_Strategy: 3 Candle + EMA9/15>VWAP + Supertrend + RSI + MACD + Vol_"

print(msg)
send_tg(msg)
