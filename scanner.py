import requests, json, os, pyotp, concurrent.futures
from SmartApi import SmartConnect
import pandas as pd
from datetime import datetime, timedelta

STATE_FILE = "active_trades.json"
PNL_FILE = "pnl_history.json"

def load_state():
    try:
        with open(STATE_FILE,"r") as f: return json.load(f)
    except: return {"active":[],"pending":[]}
def save_state(a,p):
    with open(STATE_FILE,"w") as f: json.dump({"active":a,"pending":p}, f)
def load_pnl():
    try:
        with open(PNL_FILE,"r") as f: return json.load(f)
    except: return []
def save_pnl(d):
    with open(PNL_FILE,"w") as f: json.dump(d[-500:], f)
def send_tg(tok,cid,msg):
    try:
        requests.post(f"https://api.telegram.org/bot{tok}/sendMessage", data={"chat_id":cid,"text":msg}, timeout=30)
    except: pass

def get_token_map():
    data = requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json", timeout=30).json()
    mp={}
    for i in data:
        if i.get("exch_seg")=="NSE" and i.get("symbol"):
            mp[i["symbol"].replace("-EQ","")]=i["token"]
    return mp
TOKEN_MAP = get_token_map()

# 1000 LIST
LARGE = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","BHARTIARTL","ITC","LT","KOTAKBANK","BAJFINANCE","AXISBANK","ASIANPAINT","MARUTI","TITAN","SUNPHARMA","ULTRACEMCO","NTPC","POWERGRID","ONGC","ADANIENT","ADANIPORTS","JSWSTEEL","TATASTEEL","HINDALCO","COALINDIA","BEL","HAL","BSE","MCX","TATAPOWER","TATAMOTORS","WIPRO","TECHM","HCLTECH","GRASIM","CIPLA","DIVISLAB","BRITANNIA","M&M","BAJAJ-AUTO","INDUSINDBK","SBILIFE","PFC","RECLTD","IREDA","RVNL","IRFC","IRCTC","BEML","BHEL","GAIL","VEDL","LICI","HINDZINC","JSWENERGY","COFORGE","PERSISTENT","MPHASIS","DIXON","KAYNES","POLYCAB","LTIM","BSOFT","APOLLOHOSP","MAXHEALTH","AUROPHARMA","LUPIN","GODREJPROP","DLF","PIDILITIND","SRF","MUTHOOTFIN","BANKBARODA","PNB","CANBK","AUBANK","FEDERALBNK","JIOFIN","ADANIPOWER","TATAINVEST","AARTIIND","TATACHEM","DEEPAKNTR","ATUL","AFFLE","CAMS","CDSL","ANGELONE","AARTIPHARM","ALKEM","HDFCAMC","ICICIGI","ICICIPRULI","INDHOTEL","INDIGO","NAUKRI","SIEMENS","TRENT","TVSMOTOR","ZYDUSLIFE"]
MID = ["BANKBARODA","PNB","CANBK","IDFCFIRSTB","BANDHANBNK","AUBANK","FEDERALBNK","CUB","RBLBANK","PNBHOUSING","MUTHOOTFIN","CHOLAFIN","PFC","RECLTD","IREDA","RVNL","IRFC","IRCTC","BEML","BEL","HAL","BDL","BHEL","CONCOR","NHPC","SJVN","NMDC","SAIL","VEDL","JINDALSTEL","JSWENERGY","TATAPOWER","COFORGE","PERSISTENT","KPITTECH","DIXON","KAYNES","POLYCAB","KEI","APOLLOHOSP","MAXHEALTH","FORTIS","AUROPHARMA","GODREJPROP","DLF","SRF","AARTIIND","TANLA","AFFLE","LATENTVIEW","CAMS","KFINTECH","CDSL","ANGELONE","ZOMATO","PAYTM","NYKAA","DELHIVERY","IDEA","YESBANK","SUZLON","IEX","TEJASNET","HFCL","RAILTEL","IRCON","MAZAGON","COCHINSHIP","PRAJIND","JWL","TITAGARH","GRSE","HUDCO","NBCC","ZENSAR","ROUTE","VBL","JUBLFOOD","KALYANKJIL","KAJARIACER","LALPATHLAB","LAURUSLABS","LTF","LTTS","M&MFIN","MANAPPURAM","MARICO","MCX","MGL","MOTHERSON","MRF","NATCOPHARM","NCC","OBEROIRLTY","OIL","PAGEIND","PEL","PETRONET","PIIND","POLYCAB","PRESTIGE","SAIL","SBICARD","SONACOMS","SUNTV","TATACHEM","TATACOMM","TORNTPHARM","UBL","UPL","VOLTAS","ZFCVINDIA"]
SMALL = ["ZOMATO","PAYTM","NYKAA","DELHIVERY","IDEA","YESBANK","SUZLON","IEX","CDSL","BSE","MCX","ANGELONE","CAMS","KFINTECH","TEJASNET","HFCL","RAILTEL","IRCON","MAZAGON","GARDENREACH","COCHINSHIP","PRAJIND","TANLA","AFFLE","LATENTVIEW","EASEMYTRIP","CENTRALBK","UCOBANK","IOB","MAHABANK","UNIONBANK","BANKINDIA","INDIANB","PSB","JWL","TITAGARH","BDL","GRSE","HUDCO","NBCC","ZENSAR","ROUTE","VBL","TATAINVEST","ADANIPOWER","JIOFIN","ADANIGREEN","AWL","AMBUJACEM","ACC","JKCEMENT","RAMCOCEM","DALBHARAT","SHREECEM","AIAENG","AADHARHFC","AAVAS","AEGISLOG","AETHER","AHLUCONT","ANANDRATHI","APARINDS","APTUS","ASAHIINDIA","ASTERDM","AVANTIFEED","BALRAMCHIN","BAYERCROP","BIRLACORPN","BLUEDART","BLUESTARCO","BBTC","BOSCHLTD","CAPLIPOINT","CARBORUNIVM","CASTROLIND","CEATLTD","CENTURYPLY","CERA","CHALET","CHAMBLFERT","CUMMINSIND","CYIENT","DATAPATTNS","EIDPARRY","ELECON","ELGIEQUIP","EMAMILTD","ENDURANCE","ENGINERSIN","ESCORTS","ETERNAL","FEDERALBNK","FORTIS","GAIL","GODREJCP","HONAUT","HONASA","HUDCO","IIFL","INDIAMART","INOXWIND","IPCALAB","IRB","JINDALSTEL","JSWINFRA","KANSAINER","KARURVYSYA","KPRMILL","KRBL","LICHSGFIN","LTF","M&MFIN","MGL","MOTHERSON","NATIONALUM","NBCC","NCC","NHPC","NMDC","OIL","PATANJALI","PEL","PFC","PNBHOUSING","RECLTD","SBICARD","SIEMENS","SJVN","SRF","SUPREMEIND","SYNGENE","TATACOMM","TORNTPOWER","TRENT","UBL","UNIONBANK","VEDL","VOLTAS","YESBANK"]

all_syms = list(dict.fromkeys(LARGE+MID+SMALL))[:1000]
cat_map = {}
for s in LARGE: cat_map[s]="LARGE"
for s in MID:
    if s not in cat_map: cat_map[s]="MID"
for s in SMALL:
    if s not in cat_map: cat_map[s]="SMALL"

def supertrend_simple(df):
    upper = (df["h"]+df["l"])/2 + 3*(df["h"]-df["l"]).rolling(10).mean()
    lower = (df["h"]+df["l"])/2 - 3*(df["h"]-df["l"]).rolling(10).mean()
    trend=1; res=[]
    for i in range(len(df)):
        c=df["c"].iloc[i]
        try:
            if c<=lower.iloc[i]: trend=1
            elif c>=upper.iloc[i]: trend=-1
        except: pass
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
        df["vwap"] = (df["c"]*df["v"]).cumsum()/df["v"].cumsum()
        delta = df["c"].diff()
        gain = delta.where(delta>0,0).rolling(14).mean()
        loss = -delta.where(delta<0,0).rolling(14).mean()
        df["rsi"] = 100-(100/(1+gain/loss))
        df["macd"] = df["c"].ewm(span=12).mean()-df["c"].ewm(span=26).mean()
        df["macd_sig"] = df["macd"].ewm(span=9).mean()
        df["vol_avg"] = df["v"].rolling(20).mean()
        df["atr"] = (df["h"]-df["l"]).rolling(14).mean()
        st = supertrend_simple(df)
        last = df.iloc[-1]; prev = df.iloc[-2]
        ltp = float(last["c"]); atr = float(last["atr"]) if pd.notna(last["atr"]) else ltp*0.007
        buy=0; sell=0; bc=[]; sc=[]
        if last["c"]>last["o"] and prev["c"]<prev["o"]: buy+=1; bc.append("ENGULF")
        if last["c"]<last["o"] and prev["c"]>prev["o"]: sell+=1; sc.append("ENGULF")
        if prev["ema9"]<prev["ema15"] and last["ema9"]>last["ema15"]: buy+=1; bc.append("9x15UP")
        if prev["ema9"]>prev["ema15"] and last["ema9"]<last["ema15"]: sell+=1; sc.append("9x15DN")
        if df["c"].iloc[-3:].is_monotonic_increasing: buy+=1; bc.append("3CBU")
        if df["c"].iloc[-3:].is_monotonic_decreasing: sell+=1; sc.append("3CBD")
        if last["ema9"]>last["vwap"]: buy+=1; bc.append("E9>V")
        if last["ema9"]<last["vwap"]: sell+=1; sc.append("E9<V")
        if st[-1]==1: buy+=1; bc.append("ST_G")
        else: sell+=1; sc.append("ST_R")
        if 40<=last["rsi"]<=70: buy+=1; bc.append(f"RSI{int(last['rsi'])}")
        if 20<=last["rsi"]<=60: sell+=1; sc.append(f"RSI{int(last['rsi'])}")
        if last["macd"]>last["macd_sig"]: buy+=1; bc.append("MACD+")
        if last["macd"]<last["macd_sig"]: sell+=1; sc.append("MACD-")
        if last["v"]>last["vol_avg"]*0.6: buy+=0.5; sell+=0.5; bc.append("VOL"); sc.append("VOL")
        cat = cat_map.get(sym,"SMALL"); thresh = 5 if cat=="LARGE" else 3.5
        if buy>=thresh:
            sl = round(min(df["l"].tail(5).min(), ltp-atr*1.2),1)
            return {"sym":sym,"side":"BUY","score":buy,"cat":cat,"ltp":ltp,"sl":sl,"t1":round(ltp+atr*1.5,1),"t2":round(ltp+atr*3,1),"trail":round(ltp-atr*1.2,1),"conds":bc,"atr":atr}
        if sell>=thresh:
            sl = round(max(df["h"].tail(5).max(), ltp+atr*1.2),1)
            return {"sym":sym,"side":"SELL","score":sell,"cat":cat,"ltp":ltp,"sl":sl,"t1":round(ltp-atr*1.5,1),"t2":round(ltp-atr*3,1),"trail":round(ltp+atr*1.2,1),"conds":sc,"atr":atr}
    except: return None

# LOGIN
obj = SmartConnect(api_key=os.getenv("ANGEL_API_KEY","").strip())
obj.generateSession(os.getenv("ANGEL_CLIENT_ID","").strip(), os.getenv("ANGEL_PASSWORD","").strip(), pyotp.TOTP(os.getenv("ANGEL_TOTP_SECRET","").strip()).now())

today = datetime.now()
from_d = (today - timedelta(days=5)).strftime("%Y-%m-%d 09:15")
to_d = today.strftime("%Y-%m-%d 15:30")

state = load_state(); pnl_hist = load_pnl()
closed=[]; new_active=[]

# TRAILING LOGIC
for trade in state.get("active",[]):
    sym = trade.get("symbol"); token = TOKEN_MAP.get(sym)
    if not token: new_active.append(trade); continue
    try:
        data = obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":from_d,"todate":to_d})
        df = pd.DataFrame(data["data"], columns=["ts","o","h","l","c","v"])
        ltp = float(df.iloc[-1]["c"])
        entry = float(trade.get("price",ltp)); sl = float(trade.get("sl",entry)); t1 = float(trade.get("t1",entry)); t2 = float(trade.get("t2",entry)); atr = float(trade.get("atr", ltp*0.01))
        side = trade.get("side")
        highest = float(trade.get("highest", entry)); lowest = float(trade.get("lowest", entry))
        trail_sl = float(trade.get("trail_sl", sl))

        if side=="BUY":
            if ltp>highest: highest=ltp
            # T1 hit -> SL to cost
            if ltp>=t1 and trail_sl<entry: trail_sl=entry
            # Trail
            if ltp>=t1:
                new_trail = round(ltp - atr*1.2,1)
                if new_trail>trail_sl: trail_sl=new_trail
            # Check hit
            if ltp<=trail_sl:
                pnl = trail_sl - entry
                closed.append({"symbol":sym,"side":side,"status":"TRAIL_SL","pnl":round(pnl,2),"entry":entry,"exit":trail_sl})
                pnl_hist.append({"date":today.strftime("%Y-%m-%d"),"symbol":sym,"pnl":round(pnl,2),"status":"TRAIL_SL"})
                continue
        else:
            if ltp<lowest or lowest==0: lowest=ltp
            if ltp<=t1 and trail_sl>entry: trail_sl=entry
            if ltp<=t1:
                new_trail = round(ltp + atr*1.2,1)
                if new_trail<trail_sl: trail_sl=new_trail
            if ltp>=trail_sl:
                pnl = entry - trail_sl
                closed.append({"symbol":sym,"side":side,"status":"TRAIL_SL","pnl":round(pnl,2),"entry":entry,"exit":trail_sl})
                pnl_hist.append({"date":today.strftime("%Y-%m-%d"),"symbol":sym,"pnl":round(pnl,2),"status":"TRAIL_SL"})
                continue

        trade["ltp"]=ltp; trade["trail_sl"]=trail_sl; trade["highest"]=highest; trade["lowest"]=lowest
        new_active.append(trade)
    except Exception as e:
        new_active.append(trade)

# SCAN NEW
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=40) as ex:
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
        combined_active.append({"symbol":x["sym"],"side":x["side"],"cat":x["cat"],"price":x["ltp"],"sl":x["sl"],"t1":x["t1"],"t2":x["t2"],"trail_sl":x["sl"],"highest":x["ltp"],"lowest":x["ltp"],"atr":x["atr"],"time":today.strftime("%H:%M"),"score":x["score"]})
combined_active = combined_active[:5]
pending=[{"symbol":x["sym"],"side":x["side"],"cat":x["cat"],"price":x["ltp"],"sl":x["sl"],"t1":x["t1"],"t2":x["t2"]} for x in final_6[2:]]

save_state(combined_active, pending); save_pnl(pnl_hist)

today_pnl = sum([p["pnl"] for p in pnl_hist if p["date"]==today.strftime("%Y-%m-%d")])
total_pnl = sum([p["pnl"] for p in pnl_hist])
win = len([p for p in pnl_hist if p["pnl"]>0]); loss = len([p for p in pnl_hist if p["pnl"]<0])

msg = f"🎯 1000 STOCK | 5Min | {today.strftime('%d %b %H:%M')}\n"
msg+=f"Scan {len(all_syms)} | Found {len(results)} | L:{len([x for x in results if x['cat']=='LARGE'])} M:{len([x for x in results if x['cat']=='MID'])} S:{len([x for x in results if x['cat']=='SMALL'])}\n"
msg+="--------------------------------\n"
if closed:
    msg+="📊 CLOSED TODAY:\n"
    for c in closed: msg+=f"{c['side']} {c['symbol']} {c['status']} PnL:{c['pnl']} ({c['entry']}->{c['exit']})\n"
    msg+="--------------------------------\n"

for x in final_6:
    cond = ",".join(x["conds"][:3])
    emoji = "🚀" if x["side"]=="BUY" else "🔻"
    msg+=f"{emoji} {x['side']} {x['sym']}({x['cat']}) {x['score']}/8\nE:{x['ltp']:.1f} SL:{x['sl']:.1f} T1:{x['t1']} T2:{x['t2']}\nTrail:{x['trail']} | {cond}\n\n"

if combined_active:
    msg+="--------------------------------\n🔄 ACTIVE (Trailing):\n"
    for a in combined_active:
        ltp = a.get('ltp',''); trail = a.get('trail_sl','')
        msg+=f"{a['side']} {a['symbol']} E:{a['price']} LTP:{ltp} Trail:{trail}\n"
    msg+="--------------------------------\n"

msg+=f"📈 SUMMARY | Today:{today_pnl:.1f} Total:{total_pnl:.1f} W:{win} L:{loss}\n"
if today_pnl>0: msg+="✅ Profit Day"
elif today_pnl<0: msg+="❌ Loss Day"
else: msg+="➖ No PnL Yet"

send_tg(os.getenv("TELEGRAM_BOT_TOKEN","").strip(), os.getenv("TELEGRAM_CHAT_ID","").strip(), msg)
print(msg)
