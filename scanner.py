import os, json, pyotp, urllib.request, pandas as pd, requests
from datetime import datetime, timedelta
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

# ===== CANDLE PATTERN LOGIC =====
def get_candle_patterns(df):
    if len(df)<3: return []
    c1=df.iloc[-3]; c2=df.iloc[-2]; c=df.iloc[-1]
    pats=[]
    body=abs(c['Close']-c['Open'])
    if body==0: body=0.01
    
    # 1. Hammer
    lower=min(c['Open'],c['Close'])-c['Low']; upper=c['High']-max(c['Open'],c['Close'])
    if lower > body*2 and upper < body*0.5: pats.append("HAMMER")
    # 2. Inverted Hammer
    if upper > body*2 and lower < body*0.5: pats.append("INV_HAMMER")
    # 3. Bullish Engulfing
    if c2['Close']<c2['Open'] and c['Close']>c['Open'] and c['Close']>c2['Open'] and c['Open']<c2['Close']: pats.append("BULL_ENGULF")
    # 4. Bearish Engulfing
    if c2['Close']>c2['Open'] and c['Close']<c['Open'] and c['Open']>c2['Close'] and c['Close']<c2['Open']: pats.append("BEAR_ENGULF")
    # 5. Morning Star
    if c1['Close']<c1['Open'] and abs(c2['Close']-c2['Open'])<c2['Close']*0.015 and c['Close']>c['Open'] and c['Close']>(c1['Open']+c1['Close'])/2: pats.append("MORNING_STAR")
    # 6. Evening Star
    if c1['Close']>c1['Open'] and abs(c2['Close']-c2['Open'])<c2['Close']*0.015 and c['Close']<c['Open'] and c['Close']<(c1['Open']+c1['Close'])/2: pats.append("EVENING_STAR")
    # 7. Three White Soldiers
    if c1['Close']>c1['Open'] and c2['Close']>c2['Open'] and c['Close']>c['Open'] and c2['Close']>c1['Close'] and c['Close']>c2['Close']: pats.append("3_WHITE")
    # 8. Three Black Crows
    if c1['Close']<c1['Open'] and c2['Close']<c2['Open'] and c['Close']<c['Open'] and c2['Close']<c1['Close'] and c['Close']<c2['Close']: pats.append("3_BLACK")
    return pats

def get_nse_movers():
    try:
        headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"}
        s=requests.Session(); s.get("https://www.nseindia.com", headers=headers, timeout=5)
        gain=s.get("https://www.nseindia.com/api/live-analysis-variations?index=gainers", headers=headers, timeout=5).json()
        lose=s.get("https://www.nseindia.com/api/live-analysis-variations?index=losers", headers=headers, timeout=5).json()
        g=[x['symbol'] for x in gain['NIFTY']['data'][:40]] if 'NIFTY' in gain else []
        l=[x['symbol'] for x in lose['NIFTY']['data'][:40]] if 'NIFTY' in lose else []
        if g: return list(dict.fromkeys(g+l)) # 80 stocks
    except: pass
    return ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","HAL","BEL","BDL","RVNL","NHPC","PFC","RECLTD","IRFC","TATASTEEL","BHARTIARTL","ITC","LT","M&M","SBIN","ADANIENT","ADANIPORTS","TATAPOWER","TATAMOTORS","ZOMATO","PAYTM","IRCTC","VBL","TITAN","DMART","BAJFINANCE","KDDL","NITCO","GREENPANEL","NETWEB","ALLCARGO","JKCEMENT","POWERGRID"]

def analyze(sym):
    try:
        token=token_map.get(sym)
        if not token: return None
        data=smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIFTEEN_MINUTE","fromdate":(datetime.now()-timedelta(days=5)).strftime("%Y-%m-%d %H:%M"),"todate":datetime.now().strftime("%Y-%m-%d %H:%M")})['data']
        df=pd.DataFrame(data, columns=['Time','Open','High','Low','Close','Volume'])
        if len(df)<40: return None
        
        ltp=df['Close'].iloc[-1]
        # ===== PENNY FILTER - KSHITIJPOL सारखे बंद =====
        if ltp < 20: return None
        if df['Volume'].iloc[-1] < 5000: return None

        # Indicators
        df['EMA9']=df['Close'].ewm(9).mean(); df['EMA15']=df['Close'].ewm(15).mean()
        df['TP']=(df['High']+df['Low']+df['Close'])/3
        df['VWAP']=(df['TP']*df['Volume']).cumsum()/df['Volume'].cumsum()
        delta=df['Close'].diff(); gain=delta.clip(lower=0).ewm(alpha=1/14).mean(); loss=(-delta.clip(upper=0)).ewm(alpha=1/14).mean()
        df['RSI']=100-(100/(1+gain/loss))
        df['MACD']=df['Close'].ewm(12).mean()-df['Close'].ewm(26).mean()
        # Supertrend
        hl2=(df['High']+df['Low'])/2; tr=pd.concat([df['High']-df['Low'], (df['High']-df['Close'].shift()).abs(), (df['Low']-df['Close'].shift()).abs()], axis=1).max(axis=1)
        atr=tr.rolling(10).mean(); up=hl2+3*atr; lo=hl2-3*atr
        st_dir = -1 if df['Close'].iloc[-1] > up.iloc[-2] else 1

        c=df.iloc[-1]; c3h=df['High'].iloc[-4:-1].max(); c3l=df['Low'].iloc[-4:-1].min()
        vol_avg=df['Volume'].iloc[-11:-1].mean()
        patterns=get_candle_patterns(df)

        buy_pat = any(p in patterns for p in ["HAMMER","INV_HAMMER","BULL_ENGULF","MORNING_STAR","3_WHITE"])
        sell_pat = any(p in patterns for p in ["BEAR_ENGULF","EVENING_STAR","3_BLACK"])

        # 7 Condition Score
        buy_score=sum([c['Close']>c3h, c['EMA9']>c['VWAP'], c['EMA15']>c['VWAP'], st_dir<0, c['RSI']>55, df['MACD'].iloc[-1]>0, c['Volume']>vol_avg])
        sell_score=sum([c['Close']<c3l, c['EMA9']<c['VWAP'], c['EMA15']<c['VWAP'], st_dir>0, c['RSI']<45, df['MACD'].iloc[-1]<0, c['Volume']>vol_avg])

        # Pattern असेल तर +1 Bonus
        if buy_pat: buy_score+=1
        if sell_pat: sell_score+=1

        # Final Logic: 5/7 + Pattern compulsory for Strong
        if buy_score>=6 and buy_pat:
            sl=min(c3l, ltp*0.98)
            if abs(ltp-sl) < ltp*0.004: return None # SL खूप जवळ
            r=ltp-sl
            return {"type":"BUY","sym":sym,"sc":f"{buy_score}/8","pat":"+".join(patterns),"ltp":ltp,"sl":sl,"t1":ltp+r*2,"t2":ltp+r*5}
        
        if sell_score>=6 and sell_pat:
            sl=max(c3h, ltp*1.02)
            if abs(sl-ltp) < ltp*0.004: return None
            r=sl-ltp
            return {"type":"SELL","sym":sym,"sc":f"{sell_score}/8","pat":"+".join(patterns),"ltp":ltp,"sl":sl,"t1":ltp-r*2,"t2":ltp-r*5}

    except Exception as e: return None
    return None

# ===== MAIN RUN =====
movers=get_nse_movers()
buys=[]; sells=[]
for s in movers[:60]:
    res=analyze(s)
    if res:
        if res['type']=='BUY' and len(buys)<10: buys.append(res)
        if res['type']=='SELL' and len(sells)<10: sells.append(res)

msg=f"⚡ *FAST NSE 750 + 8 PATTERNS | {datetime.now().strftime('%H:%M')}*\n_Large+Mid+Small Gainers/Losers_\n"
msg+=f"\n🟢 *BUY (3 Candle BO + 5/7 + Pattern)*\n"
if buys:
    for r in buys: msg+=f"\nBUY {r['sym']} {r['sc']} {r['pat']} E:{r['ltp']:.1f} SL:{r['sl']:.1f} T1:{r['t1']:.1f} 50% T2:{r['t2']:.1f} Trail"
else: msg+="\nNo Strong BUY Pattern Today"

msg+=f"\n\n🔴 *SELL (3 Candle BD + 5/7 + Pattern)*\n"
if sells:
    for r in sells: msg+=f"\nSELL {r['sym']} {r['sc']} {r['pat']} E:{r['ltp']:.1f} SL:{r['sl']:.1f} T1:{r['t1']:.1f} 50% T2:{r['t2']:.1f} Trail"
else: msg+="\nNo Strong SELL Pattern Today"

msg+=f"\n\n_Strategy: 3 Candle BO/BD + EMA9/15>VWAP + Supertrend + RSI + MACD + Vol + {8} Patterns_"
print(msg); send_tg(msg) 
