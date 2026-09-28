import requests, json, os, pyotp, concurrent.futures
from SmartApi import SmartConnect
import pandas as pd
from datetime import datetime, timedelta

STATE_FILE = "active_trades.json"
PNL_FILE = "pnl_history.json"

def load_state():
    try:
        with open(STATE_FILE,"r") as f:
            return json.load(f)
    except:
        return {"active":[],"pending":[]}

def save_state(a,p):
    with open(STATE_FILE,"w") as f:
        json.dump({"active":a,"pending":p}, f)

def load_pnl():
    try:
        with open(PNL_FILE,"r") as f:
            return json.load(f)
    except:
        return []

def save_pnl(d):
    with open(PNL_FILE,"w") as f:
        json.dump(d[-200:], f)

def send_tg(tok,cid,msg):
    try:
        url = "https://api.telegram.org/bot" + tok + "/sendMessage"
        requests.post(url, data={"chat_id":cid,"text":msg}, timeout=20)
    except:
        pass

def get_token_map():
    try:
        url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        data = requests.get(url, timeout=30).json()
        mp={}
        for i in data:
            if i.get("exch_seg")=="NSE" and i.get("symbol"):
                mp[i["symbol"].replace("-EQ","")]=i["token"]
        return mp
    except:
        return {}

TOKEN_MAP = get_token_map()

LARGE = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","BHARTIARTL","ITC","LT","KOTAKBANK","BAJFINANCE","AXISBANK","ASIANPAINT","MARUTI","TITAN","SUNPHARMA","ULTRACEMCO","NTPC","POWERGRID","ONGC","ADANIENT","ADANIPORTS","JSWSTEEL","TATASTEEL","HINDALCO","COALINDIA","BEL","HAL","BSE","MCX","TATAPOWER","TATAMOTORS","WIPRO","TECHM","HCLTECH","GRASIM","CIPLA","DIVISLAB","BRITANNIA","M&M","BAJAJ-AUTO","INDUSINDBK","SBILIFE","PFC","RECLTD","IREDA","RVNL","IRFC","IRCTC","BEML","BHEL","GAIL","VEDL","LICI","HINDZINC","JSWENERGY","COFORGE","PERSISTENT","MPHASIS","DIXON","KAYNES","POLYCAB","LTIM","BSOFT","APOLLOHOSP","MAXHEALTH","AUROPHARMA","LUPIN","GODREJPROP","DLF","PIDILITIND","SRF","MUTHOOTFIN","BANKBARODA","PNB","CANBK","AUBANK","FEDERALBNK","JIOFIN","ADANIPOWER","TATAINVEST"]

MID = ["BANKBARODA","PNB","CANBK","IDFCFIRSTB","BANDHANBNK","AUBANK","FEDERALBNK","CUB","RBLBANK","PNBHOUSING","MUTHOOTFIN","CHOLAFIN","PFC","RECLTD","IREDA","RVNL","IRFC","IRCTC","BEML","BEL","HAL","BDL","BHEL","CONCOR","NHPC","SJVN","COALINDIA","NMDC","SAIL","VEDL","JINDALSTEL","JSWENERGY","TATAPOWER","COFORGE","PERSISTENT","MPHASIS","KPITTECH","DIXON","KAYNES","POLYCAB","KEI","LTIM","BSOFT","APOLLOHOSP","MAXHEALTH","FORTIS","AUROPHARMA","LUPIN","GODREJPROP","DLF","PIDILITIND","SRF","TATACHEM","AARTIIND","ATUL","TANLA","AFFLE","LATENTVIEW","CAMS","KFINTECH","CDSL","ANGELONE","ZOMATO","PAYTM","NYKAA","DELHIVERY","IDEA","YESBANK","SUZLON","IEX","TEJASNET","HFCL","RAILTEL","IRCON","MAZAGON","COCHINSHIP","PRAJIND","JWL","TITAGARH","GRSE","HUDCO","NBCC","ZENSAR","ROUTE","VBL"]

SMALL = ["ZOMATO","PAYTM","NYKAA","DELHIVERY","IDEA","YESBANK","SUZLON","IEX","CDSL","BSE","MCX","ANGELONE","MOTILALOFS","CAMS","KFINTECH","TEJASNET","HFCL","RAILTEL","IRCON","MAZAGON","GARDENREACH","COCHINSHIP","PRAJIND","TANLA","AFFLE","LATENTVIEW","EASEMYTRIP","CENTRALBK","UCOBANK","IOB","MAHABANK","UNIONBANK","BANKINDIA","INDIANB","PSB","JWL","TITAGARH","BDL","GRSE","HUDCO","NBCC","ZENSAR","ROUTE","VBL","TATAINVEST","ADANIPOWER","JIOFIN","ADANIGREEN","AWL","AMBUJACEM","ACC","JKCEMENT","RAMCOCEM","DALBHARAT","SHREECEM","ULTRACEMCO","GRASIM","AIAENG"]

all_syms = list(dict.fromkeys(LARGE+MID+SMALL))[:1000]
cat_map = {}
for s in LARGE: cat_map[s]="LARGE"
for s in MID:
    if s not in cat_map: cat_map[s]="MID"
for s in SMALL:
    if s not in cat_map: cat_map[s]="SMALL"

print(f"1000 LIST | {len(all_syms)}")

def supertrend_simple(df):
    upper = (df["h"]+df["l"])/2 + 3* (df["h"]-df["l"]).rolling(10).mean()
    lower = (df["h"]+df["l"])/2 - 3* (df["h"]-df["l"]).rolling(10).mean()
    trend=1
    res=[]
    for i in range(len(df)):
        c=df["c"].iloc[i]
        if c<=lower.iloc[i]: trend=1
        elif c>=upper.iloc[i]: trend=-1
        res.append(trend)
    return res

def analyze(args):
    sym, obj, from_d, to_d = args
    token = TOKEN_MAP.get(sym)
    if not token: return None
    try:
        data = obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":from_d,"todate":to_d})
        if not data or "data" not in data or not data["data"]: return None
        df = pd.DataFrame(data["data"], columns=["ts","o","h","l","c","v"])
        if len(df) < 26: return None
        df["ema9"] = df["c"].ewm(span=9).mean()
        df["ema15"] = df["c"].ewm(span=15).mean()
        df["vwap"] = (df["c"]*df["v"]).cumsum() / df["v"].cumsum()
        delta = df["c"].diff()
        gain = delta.where(delta>0,0).rolling(14).mean()
        loss = -delta.where(delta<0,0).rolling(14).mean()
        df["rsi"] = 100 - (100/(1+gain/loss))
        df["macd"] = df["c"].ewm(span=12).mean() - df["c"].ewm(span=26).mean()
        df["macd_sig"] = df["macd"].ewm(span=9).mean()
        df["vol_avg"] = df["v"].rolling(20).mean()
        df["atr"] = (df["h"]-df["l"]).rolling(14).mean()
        st = supertrend_simple(df)
        last_st = st[-1]
        last = df.iloc[-1]
        prev = df.iloc[-2]
        ltp = float(last["c"])
        atr = float(last["atr"]) if pd.notna(last["atr"]) else ltp*0.007
        buy=0; sell=0; bc=[]; sc=[]
        if last["c"]>last["o"] and prev["c"]<prev["o"]: buy+=1; bc.append("ENGULF")
        if last["c"]<last["o"] and prev["c"]>prev["o"]: sell+=1; sc.append("ENGULF")
        if prev["ema9"]<prev["ema15"] and last["ema9"]>last["ema15"]: buy+=1; bc.append("9x15UP")
        if prev["ema9"]>prev["ema15"] and last["ema9"]<last["ema15"]: sell+=1; sc.append("9x15DN")
        if df["c"].iloc[-3:].is_monotonic_increasing: buy+=1; bc.append("3CBU")
        if df["c"].iloc[-3:].is_monotonic_decreasing: sell+=1; sc.append("3CBD")
        if last["ema9"]>last["vwap"]: buy+=1; bc.append("E9>V")
        if last["ema9"]<last["vwap"]: sell+=1; sc.append("E9<V")
        if last_st==1: buy+=1; bc.append("ST_G")
        else: sell+=1; sc.append("ST_R")
        if 40 <= last["rsi"] <= 70: buy+=1; bc.append(f"RSI{int(last['rsi'])}")
        if 20 <= last["rsi"] <= 60: sell+=1; sc.append(f"RSI{int(last['rsi'])}")
        if last["macd"]>last["macd_sig"]: buy+=1; bc.append("MACD+")
        if last["macd"]<last["macd_sig"]: sell+=1; sc.append("MACD-")
        if last["v"]>last["vol_avg"]*0.6: buy+=0.5; sell+=0.5; bc.append("VOL"); sc.append("VOL")
        cat = cat_map.get(sym,"SMALL")
        thresh = 5 if cat=="LARGE" else 3.5
        if buy>=thresh:
            sl = round(min(df["l"].tail(5).min(), ltp-atr*1.2),1)
            return {"sym":sym,"side":"BUY","score":buy,"cat":cat,"ltp":ltp,"sl":sl,"t1":round(ltp+atr*1.5,1),"t2":round(ltp+atr*3,1),"conds":bc}
        if sell>=thresh:
            sl = round(max(df["h"].tail(5).max(), ltp+atr*1.2),1)
            return {"sym":sym,"side":"SELL","score":sell,"cat":cat,"ltp":ltp,"sl":sl,"t1":round(ltp-atr*1.5,1),"t2":round(ltp-atr*3,1),"conds":sc}
    except:
        return None
    return None

api_key = os.getenv("ANGEL_API_KEY","").strip()
client_id = os.getenv("ANGEL_CLIENT_ID","").strip()
pwd = os.getenv("ANGEL_PASSWORD","").strip()
totp_secret = os.getenv("ANGEL_TOTP_SECRET","").strip()
bot_token = os.getenv("TELEGRAM_BOT_TOKEN","").strip()
chat_id = os.getenv("TELEGRAM_CHAT_ID","").strip()

obj = SmartConnect(api_key=api_key)
obj.generateSession(client_id, pwd, pyotp.TOTP(totp_secret).now())

today = datetime.now()
from_d = (today - timedelta(days=5)).strftime("%Y-%m-%d 09:15")
to_d = today.strftime("%Y-%m-%d 15:30")

state = load_state()
pnl_hist = load_pnl()

closed=[]
new_active=[]
for trade in state.get("active",[]):
    sym = trade.get("symbol")
    token = TOKEN_MAP.get(sym)
    if not token:
        new_active.append(trade)
        continue
    try:
        data = obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":from_d,"todate":to_d})
        df = pd.DataFrame(data["data"], columns=["ts","o","h","l","c","v"])
        ltp = float(df.iloc[-1]["c"])
        entry = float(trade.get("price",ltp))
        sl = float(trade.get("sl",entry))
        t1 = float(trade.get("t1",entry))
        t2 = float(trade.get("t2",entry))
        side = trade.get("side")
        status="OPEN"; pnl=0
        if side=="BUY":
            if ltp<=sl: status="SL"; pnl=sl-entry
            elif ltp>=t2: status="T2"; pnl=t2-entry
            elif ltp>=t1: status="T1"; pnl=t1-entry
        else:
            if ltp>=sl: status="SL"; pnl=entry-sl
            elif ltp<=t2: status="T2"; pnl=entry-t2
            elif ltp<=t1: status="T1"; pnl=entry-t1
        if status!="OPEN":
            closed.append({"symbol":sym,"side":side,"status":status,"pnl":round(pnl,2)})
            pnl_hist.append({"date":today.strftime("%Y-%m-%d"),"symbol":sym,"pnl":round(pnl,2),"status":status})
        else:
            trade["ltp"]=ltp
            new_active.append(trade)
    except:
        new_active.append(trade)

results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=30) as ex:
    futs=[ex.submit(analyze,(s,obj,from_d,to_d)) for s in all_syms]
    for f in concurrent.futures.as_completed(futs):
        r=f.result()
        if r: results.append(r)

def get_top(cat, side):
    filt=[x for x in results if x["cat"]==cat and x["side"]==side]
    if not filt: return None
    return sorted(filt, key=lambda x: x["score"], reverse=True)[0]

final_6=[]
for combo in [("LARGE","BUY"),("LARGE","SELL"),("MID","BUY"),("MID","SELL"),("SMALL","BUY"),("SMALL","SELL")]:
    t=get_top(combo[0], combo[1])
    if t: final_6.append(t)

combined_active = new_active[:]
for x in final_6[:2]:
    if not any(a["symbol"]==x["sym"] for a in combined_active):
        combined_active.append({"symbol":x["sym"],"side":x["side"],"cat":x["cat"],"price":x["ltp"],"sl":x["sl"],"t1":x["t1"],"t2":x["t2"],"time":today.strftime("%H:%M"),"score":x["score"]})
combined_active = combined_active[:4]

pending=[]
for x in final_6[2:]:
    pending.append({"symbol":x["sym"],"side":x["side"],"cat":x["cat"],"price":x["ltp"],"sl":x["sl"],"t1":x["t1"],"t2":x["t2"]})

save_state(combined_active, pending)
save_pnl(pnl_hist)

today_pnl = sum([p["pnl"] for p in pnl_hist if p["date"]==today.strftime("%Y-%m-%d")])
total_pnl = sum([p["pnl"] for p in pnl_hist])
win = len([p for p in pnl_hist if p["pnl"]>0])
loss = len([p for p in pnl_hist if p["pnl"]<0])

msg = "🎯 1000 STOCK | 5Min | " + today.strftime("%d %b %H:%M") + "\n"
msg = msg + f"Scan {len(all_syms)} | Found {len(results)}\n"
msg = msg + "--------------------------------\n"
if closed:
    msg = msg + "CLOSED:\n"
    for c in closed:
        msg = msg + f"{c['side']} {c['symbol']} {c['status']} PnL:{c['pnl']}\n"
    msg = msg + "--------------------------------\n"
for x in final_6:
    cond = ",".join(x["conds"][:3])
    msg = msg + f"{x['side']} {x['sym']}({x['cat']}) {x['score']}/8\nE:{x['ltp']:.1f} SL:{x['sl']:.1f} T1:{x['t1']} T2:{x['t2']}\n{cond}\n\n"
if not final_6:
    msg = msg + "No Setup - Next 5Min\n"
msg = msg + "--------------------------------\n"
if combined_active:
    for a in combined_active:
        ltp_s = f" LTP:{a.get('ltp','')}" if "ltp" in a else ""
        msg = msg + f"{a['side']} {a['symbol']} E:{a['price']}{ltp_s}\n"
    msg = msg + "--------------------------------\n"
msg = msg + f"Today:{today_pnl:.1f} Total:{total_pnl:.1f} W:{win} L:{loss}\n"

send_tg(bot_token, chat_id, msg)
print(msg)
