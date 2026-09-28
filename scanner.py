import requests, json, os, pyotp, concurrent.futures
from SmartApi import SmartConnect
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

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
    try: requests.post(f"https://api.telegram.org/bot{tok}/sendMessage", data={"chat_id":cid,"text":msg}, timeout=15)
    except: pass

def get_token_map():
    d = requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json", timeout=15).json()
    mp={}
    for i in d:
        if i.get("exch_seg")=="NSE" and i.get("symbol"):
            sym=i["symbol"].replace("-EQ","").strip()
            # फक्त Equity, BE नाही, -BL नाही
            if len(sym)>=2 and "-" not in sym and sym.isalnum() or "&" in sym or "-" in sym:
                if sym not in mp:
                    mp[sym]=i["token"]
    return mp

TOKEN_MAP = get_token_map()
print(f"TOKEN MAP TOTAL: {len(TOKEN_MAP)}")

# ===== 1000 STOCK - TOKEN MAP मधूनच - पक्का 1000 =====
# Top priority list
PRIORITY = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","BHARTIARTL","ITC","LT","KOTAKBANK","BAJFINANCE","AXISBANK","ASIANPAINT","MARUTI","TITAN","SUNPHARMA","ULTRACEMCO","NTPC","POWERGRID","ONGC","ADANIENT","ADANIPORTS","JSWSTEEL","TATASTEEL","HINDALCO","COALINDIA","BEL","HAL","BSE","MCX","TATAPOWER","TATAMOTORS","WIPRO","TECHM","HCLTECH","GRASIM","CIPLA","DIVISLAB","BRITANNIA","M&M","BAJAJ-AUTO","INDUSINDBK","SBILIFE","PFC","RECLTD","IREDA","RVNL","IRFC","IRCTC","BEML","BHEL","GAIL","VEDL","LICI","HINDZINC","JSWENERGY","COFORGE","PERSISTENT","MPHASIS","DIXON","KAYNES","POLYCAB","LTIM","BSOFT","APOLLOHOSP","MAXHEALTH","AUROPHARMA","LUPIN","GODREJPROP","DLF","PIDILITIND","SRF","MUTHOOTFIN","BANKBARODA","PNB","CANBK","AUBANK","FEDERALBNK","JIOFIN","ADANIPOWER","TATAINVEST","AARTIIND","BANKBARODA","PNB","CANBK","IDFCFIRSTB","BANDHANBNK","CUB","RBLBANK","PNBHOUSING","CHOLAFIN","CONCOR","NHPC","SJVN","NMDC","SAIL","VEDL","JINDALSTEL","COFORGE","KPITTECH","KEI","ZOMATO","PAYTM","NYKAA","DELHIVERY","IDEA","YESBANK","SUZLON","IEX","TEJASNET","HFCL","RAILTEL","IRCON","MAZAGON","COCHINSHIP","PRAJIND","JWL","TITAGARH","GRSE","HUDCO","NBCC","ZENSAR","ROUTE","VBL","JUBLFOOD","KALYANKJIL","KAJARIACER","LALPATHLAB","LAURUSLABS","LTF","LTTS","M&MFIN","MANAPPURAM","MARICO","MCX","MOTHERSON","NCC","OBEROIRLTY","OFSS","OIL","SONACOMS","TATACHEM","TATACOMM","TATAELXSI","TRENT","TVSMOTOR","UBL","UPL","VOLTAS","BALK RISIND".replace(" ",""),"HDFCBANK","ANANDRATHI","AHLUCONT"]

# आता TOKEN_MAP मधून 1000 घे - Priority आधी
all_syms=[]
for s in PRIORITY:
    if s in TOKEN_MAP and s not in all_syms:
        all_syms.append(s)
# उरलेले TOKEN_MAP मधून भर - A-Z liquid
for s in sorted(TOKEN_MAP.keys()):
    if s not in all_syms and len(all_syms)<1000:
        if len(s)>=3 and len(s)<=15: # filter
            all_syms.append(s)
    if len(all_syms)>=1000: break

all_syms = all_syms[:1000]
cat_map={}
for i,s in enumerate(all_syms):
    cat_map[s]="LARGE" if i<150 else "MID" if i<500 else "SMALL"

print(f"FINAL SCAN LIST: {len(all_syms)}")

def fast_analyze(args):
    sym, obj, from_d, to_d = args
    token = TOKEN_MAP.get(sym)
    if not token: return None
    try:
        data = obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":from_d,"todate":to_d})
        if not data or "data" not in data or not data["data"]: return None
        d = data["data"]
        if len(d) < 30: return None
        closes = [x[4] for x in d]; opens = [x[1] for x in d]; highs = [x[2] for x in d]; lows = [x[3] for x in d]; vols = [x[5] for x in d]
        c = np.array(closes, dtype=float)
        def ema(arr, span):
            alpha = 2/(span+1); ema = np.zeros_like(arr); ema[0]=arr[0]
            for i in range(1,len(arr)): ema[i]=alpha*arr[i]+(1-alpha)*ema[i-1]
            return ema
        ema9 = ema(c,9); ema15 = ema(c,15); ema20 = ema(c,20)
        vwap = np.cumsum(c*np.array(vols))/np.cumsum(np.array(vols))
        delta = np.diff(c, prepend=c[0]); gain = np.where(delta>0, delta, 0); loss = np.where(delta<0, -delta, 0)
        avg_gain = pd.Series(gain).rolling(14).mean().values; avg_loss = pd.Series(loss).rolling(14).mean().values
        rs = avg_gain/(avg_loss+1e-9); rsi = 100 - (100/(1+rs))
        ema12 = ema(c,12); ema26 = ema(c,26); macd = ema12-ema26; macd_sig = ema(macd,9)
        vol_avg = pd.Series(vols).rolling(20).mean().values
        atr = pd.Series(np.array(highs)-np.array(lows)).rolling(14).mean().values
        ltp = float(c[-1]); prev_c = float(c[-2]); last_o = float(opens[-1]); prev_o = float(opens[-2])
        atr_last = float(atr[-1]) if atr[-1]==atr[-1] else ltp*0.007
        buy=0; sell=0; bc=[]; sc=[]
        if ltp>last_o and prev_c<prev_o: buy+=1; bc.append("ENGULF")
        if ltp<last_o and prev_c>prev_o: sell+=1; sc.append("ENGULF")
        if ema9[-2]<ema15[-2] and ema9[-1]>ema15[-1]: buy+=1; bc.append("9x15UP")
        if ema9[-2]>ema15[-2] and ema9[-1]<ema15[-1]: sell+=1; sc.append("9x15DN")
        if c[-3]<c[-2]<c[-1]: buy+=1; bc.append("3CBU")
        if c[-3]>c[-2]>c[-1]: sell+=1; sc.append("3CBD")
        if ema9[-1]>vwap[-1]: buy+=1; bc.append("E9>V")
        if ema9[-1]<vwap[-1]: sell+=1; sc.append("E9<V")
        if ltp>ema20[-1]: buy+=1; bc.append("ST_G")
        else: sell+=1; sc.append("ST_R")
        if 40<=rsi[-1]<=70: buy+=1; bc.append(f"RSI{int(rsi[-1])}")
        if 20<=rsi[-1]<=60: sell+=1; sc.append(f"RSI{int(rsi[-1])}")
        if macd[-1]>macd_sig[-1]: buy+=1; bc.append("MACD+")
        if macd[-1]<macd_sig[-1]: sell+=1; sc.append("MACD-")
        if vols[-1]>vol_avg[-1]*0.6: buy+=0.5; sell+=0.5; bc.append("VOL"); sc.append("VOL")
        cat = cat_map.get(sym,"SMALL"); thresh = 5 if cat=="LARGE" else 3.5
        if buy>=thresh:
            sl = round(min(lows[-5:]),1); return {"sym":sym,"side":"BUY","score":buy,"cat":cat,"ltp":ltp,"sl":sl,"t1":round(ltp+atr_last*1.5,1),"t2":round(ltp+atr_last*3,1),"trail":round(ltp-atr_last*1.2,1),"conds":bc,"atr":atr_last}
        if sell>=thresh:
            sl = round(max(highs[-5:]),1); return {"sym":sym,"side":"SELL","score":sell,"cat":cat,"ltp":ltp,"sl":sl,"t1":round(ltp-atr_last*1.5,1),"t2":round(ltp-atr_last*3,1),"trail":round(ltp+atr_last*1.2,1),"conds":sc,"atr":atr_last}
    except: return None

obj = SmartConnect(api_key=os.getenv("ANGEL_API_KEY","").strip())
obj.generateSession(os.getenv("ANGEL_CLIENT_ID","").strip(), os.getenv("ANGEL_PASSWORD","").strip(), pyotp.TOTP(os.getenv("ANGEL_TOTP_SECRET","").strip()).now())
today = datetime.now()
from_d = (today - timedelta(days=1)).strftime("%Y-%m-%d 09:15")
to_d = today.strftime("%Y-%m-%d 15:30")

state = load_state(); pnl_hist = load_pnl()
closed=[]; new_active=[]
for trade in state.get("active",[]):
    sym = trade.get("symbol"); token = TOKEN_MAP.get(sym)
    if not token: new_active.append(trade); continue
    try:
        data = obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":from_d,"todate":to_d})
        if not data or "data" not in data: new_active.append(trade); continue
        ltp = float(data["data"][-1][4]); entry = float(trade.get("price",ltp)); trail_sl = float(trade.get("trail_sl", trade.get("sl",entry))); atr = float(trade.get("atr", ltp*0.01))
        side = trade.get("side"); highest = float(trade.get("highest", entry)); lowest = float(trade.get("lowest", entry)); t1 = float(trade.get("t1",entry))
        if side=="BUY":
            if ltp>highest: highest=ltp
            if ltp>=t1 and trail_sl<entry: trail_sl=entry
            if ltp>=t1:
                nt = round(ltp - atr*1.2,1)
                if nt>trail_sl: trail_sl=nt
            if ltp<=trail_sl:
                pnl = trail_sl - entry
                closed.append({"symbol":sym,"side":side,"status":"TRAIL_SL","pnl":round(pnl,2),"entry":entry,"exit":trail_sl})
                pnl_hist.append({"date":today.strftime("%Y-%m-%d"),"symbol":sym,"pnl":round(pnl,2),"status":"TRAIL_SL"})
                continue
        else:
            if ltp<lowest or lowest==0: lowest=ltp
            if ltp<=t1 and trail_sl>entry: trail_sl=entry
            if ltp<=t1:
                nt = round(ltp + atr*1.2,1)
                if nt<trail_sl: trail_sl=nt
            if ltp>=trail_sl:
                pnl = entry - trail_sl
                closed.append({"symbol":sym,"side":side,"status":"TRAIL_SL","pnl":round(pnl,2),"entry":entry,"exit":trail_sl})
                pnl_hist.append({"date":today.strftime("%Y-%m-%d"),"symbol":sym,"pnl":round(pnl,2),"status":"TRAIL_SL"})
                continue
        trade["ltp"]=ltp; trade["trail_sl"]=trail_sl; trade["highest"]=highest; trade["lowest"]=lowest
        new_active.append(trade)
    except: new_active.append(trade)

results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=80) as ex:
    futs=[ex.submit(fast_analyze,(s,obj,from_d,to_d)) for s in all_syms]
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
total_trades = len(pnl_hist)

msg = f"⚡ FAST 1000 | 5Min | {today.strftime('%H:%M:%S')}\n"
msg+=f"Scan {len(all_syms)} | Found {len(results)} | L:{len([x for x in results if x['cat']=='LARGE'])} M:{len([x for x in results if x['cat']=='MID'])} S:{len([x for x in results if x['cat']=='SMALL'])}\n"
msg+="--------------------------------\n"
if closed:
    msg+="📊 CLOSED TODAY:\n"
    for c in closed: msg+=f"{c['side']} {c['symbol']} {c['status']} PnL:{c['pnl']} ({c['entry']}->{c['exit']})\n"
    msg+="--------------------------------\n"
for x in final_6:
    cond = ",".join(x["conds"][:3]); emoji = "🚀" if x["side"]=="BUY" else "🔻"
    msg+=f"{emoji} {x['side']} {x['sym']}({x['cat']}) {x['score']}/8\nE:{x['ltp']:.1f} SL:{x['sl']:.1f} T1:{x['t1']} T2:{x['t2']}\nTrail:{x['trail']} | {cond}\n\n"
if combined_active:
    msg+="--------------------------------\n🔄 ACTIVE (Trailing):\n"
    for a in combined_active:
        msg+=f"{a['side']} {a['symbol']} E:{a['price']} LTP:{a.get('ltp','')} Trail:{a.get('trail_sl','')}\n"
    msg+="--------------------------------\n"

# ===== PROFIT LOSS SUMMARY - FINAL =====
msg+=f"📈 PROFIT LOSS SUMMARY\n"
msg+=f"Today: {today_pnl:.2f} | Total: {total_pnl:.2f}\n"
msg+=f"W:{win} L:{loss} Total Trades:{total_trades}\n"
if today_pnl>0: msg+=f"✅ Profit Day +{today_pnl:.2f}\n"
elif today_pnl<0: msg+=f"❌ Loss Day {today_pnl:.2f}\n"
else: msg+=f"➖ No PnL Yet - Trades Open\n"
if total_trades>0:
    win_rate = (win/total_trades*100) if total_trades>0 else 0
    msg+=f"WinRate: {win_rate:.1f}%\n"

send_tg(os.getenv("TELEGRAM_BOT_TOKEN","").strip(), os.getenv("TELEGRAM_CHAT_ID","").strip(), msg)
print(msg)
