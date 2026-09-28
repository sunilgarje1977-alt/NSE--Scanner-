import requests, json, os, pyotp, concurrent.futures
from SmartApi import SmartConnect
import pandas as pd

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

def send_telegram(bot_token, chat_id, msg):
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        # FIX: data POST - Header Error जाणार नाही
        requests.post(url, data={"chat_id": chat_id, "text": msg}, timeout=10)
    except Exception as e:
        print(f"Telegram Error: {e}")

def get_token_map():
    local_file = "token_map.json"
    if os.path.exists(local_file):
        try:
            with open(local_file,'r') as f: return json.load(f)
        except: pass
    try:
        url="https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        data=requests.get(url,timeout=15).json()
        mp={}
        for i in data:
            if i.get('exch_seg')=='NSE' and i.get('symbol'):
                mp[i['symbol'].replace('-EQ','')]=i['token']
        with open(local_file,'w') as f: json.dump(mp,f)
        return mp
    except: return {}

TOKEN_MAP=get_token_map()

def get_top_movers():
    permanent = ["NTPC","POWERGRID","ONGC","RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","BANKBARODA","PNB","CANBK","BEL","HAL","BHEL","TATAPOWER","TATASTEEL","JSWSTEEL","HINDALCO","LT","MARUTI","TITAN","ZOMATO","PAYTM","IRFC","RVNL","BSE","CDSL","MCX","KAYNES","DIXON","POLYCAB","COFORGE","PERSISTENT","PFC","RECLTD","SUZLON","IEX","TATAELXSI","IDEA","YESBANK","IDFCFIRSTB","SAIL","NHPC"]
    return permanent, []

def analyze_symbol(args):
    sym, obj = args
    token=TOKEN_MAP.get(sym)
    if not token: return None
    try:
        param={"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":"2025-09-25 09:15","todate":"2025-09-28 15:30"}
        data=obj.getCandleData(param)
        if not data or 'data' not in data or not data['data']: return None
        df=pd.DataFrame(data['data'], columns=['ts','o','h','l','c','v'])
        if len(df)<30: return None
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
        cross_up = prev['ema9']<prev['ema15'] and last['ema9']>last['ema15']
        cross_dn = prev['ema9']>prev['ema15'] and last['ema9']<last['ema15']
        cbd3 = df['c'].iloc[-3:].is_monotonic_decreasing
        cbu3 = df['c'].iloc[-3:].is_monotonic_increasing
        bull_engulf = last['c']>last['o'] and prev['c']<prev['o']
        bear_engulf = last['c']<last['o'] and prev['c']>prev['o']
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
        if buy_score>=5: return (sym, "BUY", buy_score, buy_cond, ltp)
        if sell_score>=5: return (sym, "SELL", sell_score, sell_cond, ltp)
    except: return None
    return None

# --- MAIN FIX: strip() टाकलं - \n Error जाईल ---
api_key=(os.getenv("ANGEL_API_KEY") or "").strip()
client_id=(os.getenv("ANGEL_CLIENT_ID") or "").strip()
pwd=(os.getenv("ANGEL_PASSWORD") or "").strip()
totp_secret=(os.getenv("ANGEL_TOTP_SECRET") or "").strip()
bot_token=(os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
chat_id=(os.getenv("TELEGRAM_CHAT_ID") or "").strip()

obj=SmartConnect(api_key=api_key)
totp=pyotp.TOTP(totp_secret).now()
obj.generateSession(client_id,pwd,totp)

state=load_state()
active=state.get("active",[])
pending=state.get("pending",[])

gainers, _ = get_top_movers()

results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
    futures = [executor.submit(analyze_symbol, (sym, obj)) for sym in gainers]
    for f in concurrent.futures.as_completed(futures):
        r=f.result()
        if r: results.append(r)

new_signals=[]
for sym, side, score, conds, ltp in results:
    if any(x['symbol']==sym for x in active+pending): continue
    item={"symbol":sym, "side":side, "score":score, "price":ltp, "conds":",".join(conds), "time":pd.Timestamp.now().strftime("%H:%M")}
    if len(active)<2:
        active.append(item); new_signals.append(item)
    else:
        if len(pending)<6: pending.append(item)

save_state(active, pending)

active_str = ", ".join([str(a["side"]) + " " + str(a["symbol"]) for a in active])
pending_str = ", ".join([str(p["symbol"]) for p in pending[:3]])
new_str = "".join([f"{s['side']} {s['symbol']} {s['score']}/8 {s['conds']}\n" for s in new_signals])

now_time = pd.Timestamp.now().strftime("%H:%M")
msg = f"{now_time} SCAN {len(gainers)} | Active {len(active)}/2 Pending {len(pending)}\n"
if new_signals:
    msg += f"NEW:\n{new_str}\n"
else:
    msg += "No New Signal\n"
msg += f"ACTIVE: {active_str}\nPENDING: {pending_str}"

send_telegram(bot_token, chat_id, msg)
print(msg)
