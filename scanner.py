import os, json, pyotp, urllib.request, pandas as pd, requests
from datetime import datetime, timedelta, timezone
from SmartApi import SmartConnect

def clean(k): return os.getenv(k,"").strip().strip('"').strip("'")
API_KEY=clean('ANGEL_API_KEY'); CLIENT_ID=clean('ANGEL_CLIENT_ID'); PWD=clean('ANGEL_PASSWORD'); TOTP_SECRET=clean('ANGEL_TOTP_SECRET')
TELE_TOKEN=clean('TELEGRAM_BOT_TOKEN'); TELE_CHAT=clean('TELEGRAM_CHAT_ID')

smart=SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID,PWD,pyotp.TOTP(TOTP_SECRET).now())

def send_tg(msg):
    try: requests.get(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", params={"chat_id":TELE_CHAT,"text":msg}, timeout=15)
    except: pass

IST = timezone(timedelta(hours=5, minutes=30))
ist_now = datetime.now(IST)

if not os.path.exists("scrip_master.json"):
    urllib.request.urlretrieve("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json","scrip_master.json")
with open("scrip_master.json") as f: master=json.load(f)
token_map={s['name']:s['token'] for s in master if s['exch_seg']=='NSE' and s['symbol'].endswith('-EQ')}

# === TOP GAINER = BUY ONLY, TOP LOSER = SELL ONLY ===
def get_nse_750_movers():
    headers={"User-Agent":"Mozilla/5.0"}
    s=requests.Session()
    try: s.get("https://www.nseindia.com",headers=headers,timeout=5)
    except: pass
    
    gainers=[]; losers=[]
    for idx in ["NIFTY 100","NIFTY MIDCAP 150","NIFTY SMALLCAP 250"]:
        try:
            url=f"https://www.nseindia.com/api/equity-stockIndices?index={idx.replace(' ','%20')}"
            r=s.get(url,headers=headers,timeout=10).json()
            if 'data' in r:
                data=[x for x in r['data'] if x.get('lastPrice',0)>50]
                df=pd.DataFrame(data).sort_values('pChange', ascending=False)
                # Large+Mid+Small मधून प्रत्येकी 7 Gainer + 7 Loser
                gainers.extend(df.head(7)['symbol'].tolist())
                losers.extend(df.tail(7)['symbol'].tolist())
        except: continue

    if len(gainers)<15:
        gainers=["POLYCAB","DIXON","KAYNES","BSE","HAL","BEL","BHEL","PFC","RECLTD","RVNL","TATAPOWER","TATAMOTORS","JSWSTEEL","RELIANCE","MARUTI","TITAN","NTPC","POWERGRID","COALINDIA","M&M","KPITTECH"]
        losers=["SUZLON","IDEA","YESBANK","IRFC","SAIL","NHPC","SJVN","NMDC","BANKBARODA","PNB","CANBK","IDFCFIRSTB","ZOMATO","IRCTC","IEX","CDSL","MCX","TATAELXSI","LTTS","COFORGE","PERSISTENT"]

    print(f"GAINERS {len(gainers)}: {gainers[:5]} | LOSERS {len(losers)}: {losers[:5]}")
    return gainers[:21], losers[:21] # Large7+Mid7+Small7 = 21+21 = 42

def get_pat(df):
    if len(df)<4: return []
    c1=df.iloc[-2]; c=df.iloc[-1]
    pats=[]; body=abs(c['Close']-c['Open'])+1.0
    low=min(c['Open'],c['Close'])-c['Low']; up=c['High']-max(c['Open'],c['Close'])
    if low>body*2.0 and c['Close']>c['Open']: pats.append("HAMMER")
    if up>body*2.0 and c['Close']<c['Open']: pats.append("INV_HAMMER")
    vol_ok=c['Volume']>df['Volume'].iloc[-6:-1].mean()*1.05
    if c1['Close']<c1['Open'] and c['Close']>c['Open'] and c['Close']>c1['Open'] and vol_ok: pats.append("BULL_ENGULF")
    if c1['Close']>c1['Open'] and c['Close']<c['Open'] and c['Close']<c1['Open'] and vol_ok: pats.append("BEAR_ENGULF")
    return pats

def analyze(sym, mode):
    try:
        token=token_map.get(sym)
        if not token: return None
        fdate=(ist_now-timedelta(days=5)).strftime("%Y-%m-%d %H:%M"); tdate=ist_now.strftime("%Y-%m-%d %H:%M")
        data=smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIFTEEN_MINUTE","fromdate":fdate,"todate":tdate})['data']
        df=pd.DataFrame(data,columns=['Time','Open','High','Low','Close','Volume'])
        if len(df)<30: return None
        ltp=df['Close'].iloc[-1]
        if ltp<50: return None
        df['EMA9']=df['Close'].ewm(9).mean(); df['EMA15']=df['Close'].ewm(15).mean()
        df['TP']=(df['High']+df['Low']+df['Close'])/3; df['VWAP']=(df['TP']*df['Volume']).cumsum()/df['Volume'].cumsum()
        delta=df['Close'].diff(); gain=delta.clip(lower=0).ewm(alpha=1/14).mean(); loss=(-delta.clip(upper=0)).ewm(alpha=1/14).mean()
        df['RSI']=100-(100/(1+gain/loss)); df['MACD']=df['Close'].ewm(12).mean()-df['Close'].ewm(26).mean()
        hl2=(df['High']+df['Low'])/2; tr=pd.concat([df['High']-df['Low'],(df['High']-df['Close'].shift()).abs(),(df['Low']-df['Close'].shift()).abs()],axis=1).max(axis=1)
        atr=tr.rolling(10).mean(); up=hl2+3*atr; st=-1 if df['Close'].iloc[-1]>up.iloc[-2] else 1
        c=df.iloc[-1]; c3h=df['High'].iloc[-4:-1].max(); c3l=df['Low'].iloc[-4:-1].min(); vavg=df['Volume'].iloc[-11:-1].mean()
        pats=get_pat(df)
        
        # === CONDITION MATCH ===
        if mode=="GAINER":
            buy_score=sum([c['Close']>c3h, c['EMA9']>c['VWAP'], c['EMA15']>c['VWAP'], st<0, c['RSI']>50, df['MACD'].iloc[-1]>0, c['Volume']>vavg*0.9])
            if buy_score>=5:
                sl=min(c3l,ltp*0.985); r=ltp-sl
                if r<ltp*0.003: return None
                tier="STAR ⭐" if any(p in pats for p in ["HAMMER","BULL_ENGULF"]) else "GOOD"
                return {"t":"BUY","s":sym,"sc":f"{buy_score}/7","p":"+ ".join(pats) if pats else "TOP GAINER 5/7","ltp":ltp,"sl":sl,"t1":ltp+r*2,"t2":ltp+r*4,"tier":tier}
        else: # LOSER
            sell_score=sum([c['Close']<c3l, c['EMA9']<c['VWAP'], c['EMA15']<c['VWAP'], st>0, c['RSI']<50, df['MACD'].iloc[-1]<0, c['Volume']>vavg*0.9])
            if sell_score>=5:
                sl=max(c3h,ltp*1.015); r=sl-ltp
                if r<ltp*0.003: return None
                tier="STAR ⭐" if any(p in pats for p in ["INV_HAMMER","BEAR_ENGULF"]) else "GOOD"
                return {"t":"SELL","s":sym,"sc":f"{sell_score}/7","p":"+ ".join(pats) if pats else "TOP LOSER 5/7","ltp":ltp,"sl":sl,"t1":ltp-r*2,"t2":ltp-r*4,"tier":tier}
    except: return None

gainers_list, losers_list = get_nse_750_movers()
buys=[]; sells=[]

for sym in gainers_list:
    res=analyze(sym, "GAINER")
    if res and len(buys)<10: buys.append(res)

for sym in losers_list:
    res=analyze(sym, "LOSER")
    if res and len(sells)<10: sells.append(res)

msg=f"🔥 LIVE MATCHED | {ist_now.strftime('%d %b %H:%M')} IST\nGainer=BUY Only | Loser=SELL Only\nLARGE7+MID7+SMALL7\n\nTOP GAINER BUY ({len(buys)}):\n"
for r in buys: msg+=f"{r['tier']} {r['t']} {r['s']} {r['sc']} {r['p']} E:{r['ltp']:.1f} SL:{r['sl']:.1f} T1:{r['t1']:.1f} T2:{r['t2']:.1f}\n"
if not buys: msg+="No BUY in Gainers Now\n"

msg+=f"\nTOP LOSER SELL ({len(sells)}):\n"
for r in sells: msg+=f"{r['tier']} {r['t']} {r['s']} {r['sc']} {r['p']} E:{r['ltp']:.1f} SL:{r['sl']:.1f} T1:{r['t1']:.1f} T2:{r['t2']:.1f}\n"
if not sells: msg+="No SELL in Losers Now\n"

print(msg); send_tg(msg)
