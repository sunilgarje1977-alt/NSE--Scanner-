import requests, json, os, time, pyotp
from SmartApi import SmartConnect
import pandas as pd

# On Time साठी 70 Sec Wait
print("Waiting 70 sec for Candle Close...")
time.sleep(70)

STATE_FILE = "active_trades.json"

def load_state():
    if not os.path.exists(STATE_FILE): return {"active":[], "pending":[]}
    try:
        with open(STATE_FILE,'r') as f:
            data=json.load(f)
            if not isinstance(data.get("active"), list): data["active"]=[]
            if not isinstance(data.get("pending"), list): data["pending"]=[]
            return data
    except: return {"active":[], "pending":[]}

def save_state(active, pending):
    with open(STATE_FILE,'w') as f:
        json.dump({"active":active, "pending":pending}, f)

def get_token_map():
    try:
        url="https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        data=requests.get(url,timeout=20).json()
        mp={}
        for i in data:
            if i.get('exch_seg')=='NSE' and i.get('symbol'):
                sym=i['symbol'].replace('-EQ','')
                mp[sym]=i['token']
        return mp
    except: return {}

TOKEN_MAP=get_token_map()

def get_top_movers():
    headers={"User-Agent":"Mozilla/5.0"}
    s=requests.Session()
    try: s.get("https://www.nseindia.com",headers=headers,timeout=5)
    except: pass

    permanent = ["NTPC","POWERGRID","ONGC","RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","BANKBARODA","PNB","CANBK","BEL","HAL","BHEL","TATAPOWER","TATASTEEL","JSWSTEEL","HINDALCO","LT","MARUTI","TITAN","ZOMATO","PAYTM","IRFC","RVNL","BSE","CDSL","MCX","KAYNES","DIXON","POLYCAB","COFORGE","PERSISTENT","PFC","RECLTD","SUZLON","IEX","TATAELXSI","IDEA","YESBANK","IDFCFIRSTB","SAIL","NHPC","COALINDIA","ADANIENT","ADANIPORTS"]

    gainers=list(permanent); losers=list(permanent)
    for idx in ["NIFTY 100","NIFTY MIDCAP 150","NIFTY SMALLCAP 250"]:
        try:
            url=f"https://www.nseindia.com/api/equity-stockIndices?index={idx.replace(' ','%20')}"
            r=s.get(url,headers=headers,timeout=10).json()
            if 'data' in r:
                df=pd.DataFrame(r['data'])
                df=df[df['lastPrice']>30]
                df=df.sort_values('pChange',ascending=False)
                gainers.extend(df.head(30)['symbol'].tolist())
                losers.extend(df.tail(30)['symbol'].tolist())
        except: continue

    gainers=list(dict.fromkeys(gainers))[:50]
    losers=list(dict.fromkeys(losers))[:50]
    print(f"SCAN LIST: Gainers {len(gainers)} Losers {len(losers)}")
    return gainers, losers

def get_candles(obj, token):
    try:
        param={"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":"2025-09-25 09:15","todate":"2025-09-28 15:30"}
        data=obj.getCandleData(param)
        if not data or 'data' not in data or not data['data']: return None
        df=pd.DataFrame(data['data'], columns=['ts','o','h','l','c','v'])
        return df
    except: return None

def analyze(df):
    if df is None or len(df)<30: return None
    df['ema9']=df['c'].ewm(span=9).mean()
    df['ema15']=df['c'].ewm(span=15).mean()
    df['vwap']=(df['c']*df['v']).cumsum()/df['v'].cumsum()
    delta=df['c'].diff()
    gain=delta.where(delta>0,0).rolling(14).mean()
    loss=-delta.where(delta<0,0).rolling(14).mean()
    rs= gain/loss
    df['rsi']=100-(100/(1+rs))
    df['st_dir']= (df['c'] > df['c'].ewm(span=10).mean()).astype(int)
    df['st_dir']= df['st_dir'].apply(lambda x: 1 if x==1 else -1)
    ema12=df['c'].ewm(span=12).mean()
    ema26=df['c'].ewm(span=26).mean()
    df['macd']=ema12-ema26
    df['macd_sig']=df['macd'].ewm(span=9).mean()
    df['vol_avg']=df['v'].rolling(20).mean()

    last=df.iloc[-1]; prev=df.iloc[-2]
    ltp=last['c']; vol=last['v']; vavg=last['vol_avg']

    bull_engulf = last['c']>last['o'] and prev['c']<prev['o'] and last['c']>prev['o']
    bear_engulf = last['c']<last['o'] and prev['c']>prev['o'] and last['c']<prev['o']
    cross_up = prev['ema9']<prev['ema15'] and last['ema9']>last['ema15']
    cross_dn = prev['ema9']>prev['ema15'] and last['ema9']<last['ema15']
    cbd3 = df['c'].iloc[-3:].is_monotonic_decreasing
    cbu3 = df['c'].iloc[-3:].is_monotonic_increasing

    buy_score=0; sell_score=0
    buy_cond=[]; sell_cond=[]

    if bull_engulf: buy_score+=1; buy_cond.append("BULL_ENGULF")
    if bear_engulf: sell_score+=1; sell_cond.append("BEAR_ENGULF")
    if cross_up: buy_score+=1; buy_cond.append("9x15 UP")
    if cross_dn: sell_score+=1; sell_cond.append("9x15DN")
    if cbu3: buy_score+=1; buy_cond.append("3CBU")
    if cbd3: sell_score+=1; sell_cond.append("3CBD")
    if last['ema9']>last['vwap']: buy_score+=1; buy_cond.append("E9>V")
    if last['ema9']<last['vwap']: sell_score+=1; sell_cond.append("E9<V")
    if last['ema15']>last['vwap']: buy_score+=1; buy_cond.append("E15>V")
    if last['ema15']<last['vwap']: sell_score+=1; sell_cond.append("E15<V")
    if last['st_dir']==1: buy_score+=1; buy_cond.append("ST_G")
    if last['st_dir']==-1: sell_score+=1; sell_cond.append("ST_R")
    if last['rsi']>40 and last['rsi']<70: buy_score+=1; buy_cond.append(f"RSI{int(last['rsi'])}")
    if last['rsi']<60 and last['rsi']>20: sell_score+=1; sell_cond.append(f"RSI{int(last['rsi'])}")
    if last['macd']>last['macd_sig']: buy_score+=1; buy_cond.append("MACD+")
    if last['macd']<last['macd_sig']: sell_score+=1; sell_cond.append("MACD-")

    vol_need = vavg*0.5 if ltp<500 else vavg*0.7
    if vol>vol_need:
        buy_score+=0.5; sell_score+=0.5
        buy_cond.append("VOL"); sell_cond.append("VOL")

    if buy_score>=5: return ("BUY", buy_score, buy_cond, ltp)
    if sell_score>=5: return ("SELL", sell_score, sell_cond, ltp)
    return None

api_key=os.getenv("ANGEL_API_KEY")
client_id=os.getenv("ANGEL_CLIENT_ID")
pwd=os.getenv("ANGEL_PASSWORD")
totp_secret=os.getenv("ANGEL_TOTP_SECRET")
bot_token=os.getenv("TELEGRAM_BOT_TOKEN")
chat_id=os.getenv("TELEGRAM_CHAT_ID")

obj=SmartConnect(api_key=api_key)
totp=pyotp.TOTP(totp_secret).now()
data=obj.generateSession(client_id,pwd,totp)

state=load_state()
active=state.get("active",[])
pending=state.get("pending",[])

gainers, losers = get_top_movers()
all_syms = gainers + losers

new_signals=[]
for sym in all_syms:
    token=TOKEN_MAP.get(sym)
    if not token: continue
    df=get_candles(obj, token)
    res=analyze(df)
    if res:
        side, score, conds, ltp = res
        if any(x['symbol']==sym for x in active+pending): continue
        item={"symbol":sym, "side":side, "score":score, "price":ltp, "conds":",".join(conds), "time":pd.Timestamp.now().strftime("%H:%M")}
        if len(active)<2:
            active.append(item); new_signals.append(item)
        else:
            if len(pending)<6: pending.append(item)

save_state(active, pending)

# FIXED: f-string Error काढला - आता 100% चालेल
active_str = ", ".join([str(a["side"]) + " " + str(a["symbol"]) for a in active])
pending_str = ", ".join([str(p["symbol"]) for p in pending[:3]])
new_str = ""
for s in new_signals:
    emoji = "BUY" if s["side"]=="BUY" else "SELL"
    new_str += f"{emoji} {s['symbol']} {s['score']}/8 {s['conds']}\n"

now_time = pd.Timestamp.now().strftime("%H:%M")
msg = f"{now_time} SCAN {len(all_syms)} | Active {len(active)}/2 Pending {len(pending)}\n"
if new_signals:
    msg += f"NEW {len(new_signals)} ACTIVE:\n{new_str}\n"
else:
    msg += "No New Signal\n"
msg += f"ACTIVE: {active_str}\nPENDING: {pending_str}"

requests.get(f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}&text={msg}")
print(msg)
