import requests, json, os, pyotp, concurrent.futures
from SmartApi import SmartConnect
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

STATE_FILE = "active_trades.json"
PNL_FILE = "pnl_history.json"
MAX_ACTIVE = 2
DAILY_TARGET = 8

def load_state():
    try:
        with open(STATE_FILE,"r") as f: return json.load(f)
    except: return {"active":[],"pending":[],"today_count":0,"today_date":""}
def save_state(a,p,count,date):
    with open(STATE_FILE,"w") as f: json.dump({"active":a,"pending":p,"today_count":count,"today_date":date}, f)
def load_pnl():
    try:
        with open(PNL_FILE,"r") as f: return json.load(f)
    except: return []
def save_pnl(d):
    with open(PNL_FILE,"w") as f: json.dump(d[-1000:], f)
def send_tg(tok,cid,msg):
    try: requests.post(f"https://api.telegram.org/bot{tok}/sendMessage", data={"chat_id":cid,"text":msg}, timeout=20)
    except: pass

def get_token_map():
    d = requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json", timeout=20).json()
    mp={}
    for i in d:
        if i.get("exch_seg")=="NSE" and i.get("symbol"):
            sym=i["symbol"].replace("-EQ","").strip()
            if len(sym)>=2 and sym not in mp: mp[sym]=i["token"]
    return mp
TOKEN_MAP = get_token_map()

def get_nifty_trend(obj):
    try:
        token="99926000"
        today=datetime.now()
        from_d=(today-timedelta(days=1)).strftime("%Y-%m-%d 09:15")
        to_d=today.strftime("%Y-%m-%d 15:30")
        data=obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":from_d,"todate":to_d})
        if data and "data" in data and len(data["data"])>20:
            c=[x[4] for x in data["data"]]
            ema20=pd.Series(c).ewm(20).mean().iloc[-1]
            return "UP" if c[-1]>ema20 else "DOWN"
    except: return "UP"
    return "UP"

# TRUE CATEGORY - BUG FIX
TRUE_SMALL_MID = set(["PRAJIND","DAMCAPITAL","RSYSTEMS","SMCGLOBAL","SYNCOMF","SDBL","ZENSAR","VBL","NBCC","KPITTECH","RAILTEL","IRCON","MAZAGON","TITAGARH","JWL","SUZLON","ZOMATO","YESBANK","IEX","PAYTM","IDEA","NHPC","SJVN","SAIL","COCHINSHIP","HUDCO","BEML","BHEL","PFC","RECLTD","IREDA","RVNL","IRFC","BSE","MCX","DIXON","KAYNES","POLYCAB","COFORGE","PERSISTENT","GRSE","BEL","HAL"])

PRIORITY = ["PRAJIND","COCHINSHIP","JWL","TITAGARH","GRSE","HUDCO","NBCC","ZENSAR","VBL","DAMCAPITAL","RSYSTEMS","SMCGLOBAL","SYNCOMF","SDBL","RVNL","IRFC","BEML","BHEL","PFC","RECLTD","IREDA","SUZLON","ZOMATO","YESBANK","IEX","PAYTM","IDEA","BSE","MCX","DIXON","KAYNES","POLYCAB","COFORGE","PERSISTENT","NHPC","SJVN","NMDC","SAIL","KPITTECH","RAILTEL","IRCON","MAZAGON","BHARTIARTL","SBIN","RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","ITC","LT","KOTAKBANK","BAJFINANCE","AXISBANK","MARUTI","TITAN","SUNPHARMA","ULTRACEMCO","NTPC","POWERGRID","ONGC","ADANIENT","JSWSTEEL","TATASTEEL","BEL","HAL","TATAPOWER","WIPRO","TECHM","HCLTECH","CIPLA","DIVISLAB","M&M","BAJAJ-AUTO","SBILIFE"]

all_syms=[]
for s in PRIORITY:
    if s in TOKEN_MAP and s not in all_syms: all_syms.append(s)
for s in sorted(TOKEN_MAP.keys()):
    if s not in all_syms and len(all_syms)<1000:
        if 3<=len(s)<=15: all_syms.append(s)
    if len(all_syms)>=1000: break
all_syms=all_syms[:1000]

cat_map={}
for s in all_syms:
    if s in TRUE_SMALL_MID:
        # Small vs Mid
        if s in ["PRAJIND","DAMCAPITAL","RSYSTEMS","SMCGLOBAL","SYNCOMF","SDBL","ZENSAR","VBL","SUZLON","ZOMATO","YESBANK","IEX","PAYTM","IDEA"]: cat_map[s]="SMALL"
        else: cat_map[s]="MID"
    else:
        idx = all_syms.index(s)
        if idx < 150: cat_map[s]="LARGE"
        elif idx < 500: cat_map[s]="MID"
        else: cat_map[s]="SMALL"

SCAN_LIST = all_syms
WORKERS = 60

def supertrend_dir(c,h,l, period=10, mult=3):
    try:
        hl2=(np.array(h)+np.array(l))/2
        atr=pd.Series(np.array(h)-np.array(l)).rolling(period).mean().values
        atr=np.nan_to_num(atr, nan=0.01)
        up=hl2+mult*atr; dn=hl2-mult*atr
        dirc=1
        for i in range(1,len(c)):
            if c[i]<dn[i-1]: dirc=-1
            elif c[i]>up[i-1]: dirc=1
        return dirc
    except: return 1

def fast_analyze(args):
    sym,obj,from_d,to_d,nifty_trend=args
    token=TOKEN_MAP.get(sym)
    if not token: return None
    try:
        data=obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":from_d,"todate":to_d})
        if not data or "data" not in data or not data["data"] or len(data["data"])<35: return None
        d=data["data"]
        closes=[x[4] for x in d]; opens=[x[1] for x in d]; highs=[x[2] for x in d]; lows=[x[3] for x in d]; vols=[x[5] for x in d]
        c=np.array(closes,float); h=np.array(highs,float); l=np.array(lows,float)
        def ema(arr,span):
            a=2/(span+1); e=np.zeros_like(arr); e[0]=arr[0]
            for i in range(1,len(arr)): e[i]=a*arr[i]+(1-a)*e[i-1]
            return e
        ema9=ema(c,9); ema15=ema(c,15); ema20=ema(c,20)
        vwap=np.cumsum(c*np.array(vols))/np.cumsum(np.array(vols))
        delta=np.diff(c,prepend=c[0]); gain=np.where(delta>0,delta,0); loss=np.where(delta<0,-delta,0)
        avg_gain=pd.Series(gain).rolling(14).mean().values; avg_loss=pd.Series(loss).rolling(14).mean().values
        rsi=100-(100/(1+avg_gain/(avg_loss+1e-9)))
        ema12=ema(c,12); ema26=ema(c,26); macd=ema12-ema26; macd_sig=ema(macd,9)
        vol_avg=pd.Series(vols).rolling(20).mean().values
        atr=pd.Series(h-l).rolling(14).mean().values
        st_dir=supertrend_dir(c,h,l)
        ltp=float(c[-1]); prev_c=float(c[-2]); last_o=float(opens[-1]); prev_o=float(opens[-2])
        atr_last=float(atr[-1]) if atr[-1]==atr[-1] else ltp*0.008
        orb_high=max(highs[:6]) if len(highs)>=6 else max(highs)
        orb_low=min(lows[:6]) if len(lows)>=6 else min(lows)
        body=abs(ltp-last_o); rng=max(highs[-1],last_o)-min(lows[-1],last_o)+1e-9
        wick_pct=1-(body/rng)

        day_low = min(lows); day_high = max(highs); day_open = opens[0]
        recovery_pct = ((ltp - day_low) / (day_low+1e-9)) * 100
        fall_from_high = ((day_high - ltp) / (day_high+1e-9)) * 100
        last_5m_chg = ((closes[-1] - closes[-2]) / (closes[-2]+1e-9)) * 100
        day_gain_pct = ((ltp - day_open) / (day_open+1e-9)) * 100
        vol_avg_20=float(vol_avg[-1]) if vol_avg[-1]==vol_avg[-1] else 1
        volx = vols[-1]/vol_avg_20 if vol_avg_20>0 else 1

        cat=cat_map.get(sym,"SMALL")
        is_small_mid = cat in ["SMALL","MID"]
        if is_small_mid:
            if wick_pct>0.88: return None
        else:
            if wick_pct>0.75: return None

        # 5 MIN BREAKOUT/BREAKDOWN LEVELS
        last_10_high = max(highs[-10:-1]) if len(highs)>=11 else max(highs[:-1])
        last_10_low = min(lows[-10:-1]) if len(lows)>=11 else min(lows[:-1])

        buy=0; sell=0; bc=[]; sc=[]
        # Basic
        if ltp>last_o and prev_c<prev_o and (ltp-last_o)>(prev_o-prev_c)*0.7: buy+=1; bc.append("ENG")
        if ltp<last_o and prev_c>prev_o and (last_o-ltp)>(prev_c-prev_o)*0.7: sell+=1; sc.append("ENG")
        if ema9[-2]<ema15[-2] and ema9[-1]>ema15[-1]: buy+=1; bc.append("9x15")
        if ema9[-2]>ema15[-2] and ema9[-1]<ema15[-1]: sell+=1; sc.append("9x15")
        if c[-3]<c[-2]<c[-1] and c[-1]>ema9[-1]: buy+=1; bc.append("3C")
        if c[-3]>c[-2]>c[-1] and c[-1]<ema9[-1]: sell+=1; sc.append("3C")
        if ema9[-1]>vwap[-1] and ltp>vwap[-1]: buy+=1; bc.append("VW+")
        if ema9[-1]<vwap[-1] and ltp<vwap[-1]: sell+=1; sc.append("VW-")
        if ltp>ema20[-1] and ema20[-1]>ema20[-2]: buy+=1; bc.append("E20U")
        if ltp<ema20[-1] and ema20[-1]<ema20[-2]: sell+=1; sc.append("E20D")
        rsi_val=float(rsi[-1]) if rsi[-1]==rsi[-1] else 50
        if 50<=rsi_val<=70: buy+=1; bc.append(f"RSI-B {int(rsi_val)}")
        if 28<=rsi_val<=50: sell+=1.2; sc.append(f"RSI-S {int(rsi_val)}")
        if macd[-1]>macd_sig[-1]: buy+=1; bc.append("MACD+")
        if macd[-1]<macd_sig[-1]: sell+=1; sc.append("MACD-")
        last_5_high=max(highs[-5:]); last_5_low=min(lows[-5:])
        if vols[-1]>vol_avg_20*1.0 and ltp>=last_5_high*0.998: buy+=1.2; bc.append(f"VOL-BO {volx:.1f}x")
        if vols[-1]>vol_avg_20*1.0 and ltp<=last_5_low*1.002: sell+=1.2; sc.append(f"VOL-BD {volx:.1f}x")

        # ===== 5 MIN CANDLE BREAKOUT / BREAKDOWN =====
        if ltp > last_10_high * 1.0005:
            if volx>=0.9: buy+=2.8; bc.append(f"5m-BO {((ltp-last_10_high)/last_10_high*100):.1f}%")
            else: buy+=1.5; bc.append("5m-BO")
        if ltp < last_10_low * 0.9995:
            if volx>=0.9: sell+=2.8; sc.append(f"5m-BD {((last_10_low-ltp)/ltp*100):.1f}%")
            else: sell+=1.5; sc.append("5m-BD")
        # ORB BREAKOUT
        if ltp > orb_high * 1.001: buy+=2.0; bc.append(f"ORB-BO {((ltp-orb_high)/orb_high*100):.1f}%")
        if ltp < orb_low * 0.999: sell+=2.0; sc.append(f"ORB-BD {((orb_low-ltp)/orb_low*100):.1f}%")
        if st_dir==1 and ltp>orb_high: buy+=1; bc.append("ST+ORB")
        if st_dir==-1 and ltp<orb_low: sell+=1; sc.append("ST+ORB")

        # ===== SMALL+MID ULTRA LOGIC =====
        if is_small_mid:
            if day_gain_pct >= 0.6:
                if day_gain_pct >= 1.0: buy+=2.5; bc.append(f"SM-DAY+ {day_gain_pct:.1f}%")
                if last_5m_chg >= 0.15: buy+=1.2; bc.append(f"S-MOM {last_5m_chg:.1f}%")
                if ltp >= day_high*0.994: buy+=1.0; bc.append("NEAR-HIGH")
                if recovery_pct >= 1.0: buy+=1.0; bc.append(f"RECOV {recovery_pct:.1f}%")
            if day_gain_pct <= -0.6:
                if day_gain_pct <= -1.0: sell+=2.5; sc.append(f"SM-DAY- {day_gain_pct:.1f}%")
                if last_5m_chg <= -0.15: sell+=1.2; sc.append(f"S-DN {last_5m_chg:.1f}%")
                if fall_from_high >= 1.0: sell+=1.0; sc.append(f"FALL {fall_from_high:.1f}%")

        if cat=="SMALL":
            if buy>0: buy+=1.0; bc.append("S-BONUS")
            if sell>0: sell+=1.0; sc.append("S-BONUS")
        elif cat=="MID":
            if buy>0: buy+=0.7; bc.append("M-BONUS")
            if sell>0: sell+=0.7; sc.append("M-BONUS")

        # Threshold - Low for Small/Mid
        buy_thresh = 2.0 if is_small_mid else 3.5
        sell_thresh = 1.6 if is_small_mid else 3.0

        # Bullish ला Day Green पाहिजे, Bearish ला Red
        if buy>=buy_thresh and day_gain_pct < -1.0 and is_small_mid:
            return None
        if sell>=sell_thresh and day_gain_pct > 1.0 and is_small_mid:
            return None

        if buy>=buy_thresh:
            sl=round(min(lows[-6:]),1)
            return {"sym":sym,"side":"BUY","score":buy,"cat":cat,"ltp":ltp,"sl":sl,"t1":round(ltp+atr_last*1.5,1),"t2":round(ltp+atr_last*3,1),"trail":round(ltp-atr_last*1.2,1),"conds":bc,"atr":atr_last,"recov":recovery_pct,"day_chg":day_gain_pct,"last_5m":last_5m_chg,"volx":volx}
        if sell>=sell_thresh:
            sl=round(max(highs[-6:]),1)
            return {"sym":sym,"side":"SELL","score":sell,"cat":cat,"ltp":ltp,"sl":sl,"t1":round(ltp-atr_last*1.5,1),"t2":round(ltp-atr_last*3,1),"trail":round(ltp+atr_last*1.2,1),"conds":sc,"atr":atr_last,"recov":fall_from_high,"day_chg":day_gain_pct,"last_5m":last_5m_chg,"volx":volx}
    except: return None

obj=SmartConnect(api_key=os.getenv("ANGEL_API_KEY","").strip())
obj.generateSession(os.getenv("ANGEL_CLIENT_ID","").strip(), os.getenv("ANGEL_PASSWORD","").strip(), pyotp.TOTP(os.getenv("ANGEL_TOTP_SECRET","").strip()).now())
today=datetime.now()
from_d=(today-timedelta(days=1)).strftime("%Y-%m-%d 09:15"); to_d=today.strftime("%Y-%m-%d 15:30")
nifty_trend=get_nifty_trend(obj)
state=load_state(); pnl_hist=load_pnl()
today_str=today.strftime("%Y-%m-%d")
if state.get("today_date")!=today_str:
    state["today_count"]=0; state["today_date"]=today_str; state["active"]=[]; state["pending"]=[]

closed=[]; new_active=[]
for trade in state.get("active",[]):
    sym=trade.get("symbol"); token=TOKEN_MAP.get(sym)
    if not token: new_active.append(trade); continue
    try:
        data=obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":from_d,"todate":to_d})
        if not data or "data" not in data: new_active.append(trade); continue
        ltp=float(data["data"][-1][4]); entry=float(trade.get("price",ltp)); trail_sl=float(trade.get("trail_sl",trade.get("sl",entry))); atr=float(trade.get("atr",ltp*0.01))
        side=trade.get("side"); highest=float(trade.get("highest",entry)); lowest=float(trade.get("lowest",entry)); t1=float(trade.get("t1",entry))
        if side=="BUY":
            if ltp>highest: highest=ltp
            if ltp>=t1 and trail_sl<entry: trail_sl=entry
            if ltp>=t1:
                nt=round(ltp-atr*1.2,1)
                if nt>trail_sl: trail_sl=nt
            if ltp<=trail_sl:
                pnl=trail_sl-entry; closed.append({"symbol":sym,"side":side,"status":"TRAIL_SL","pnl":round(pnl,2),"entry":entry,"exit":trail_sl})
                pnl_hist.append({"date":today_str,"symbol":sym,"pnl":round(pnl,2),"status":"TRAIL_SL","time":today.strftime("%H:%M")}); continue
        else:
            if ltp<lowest or lowest==0: lowest=ltp
            if ltp<=t1 and trail_sl>entry: trail_sl=entry
            if ltp<=t1:
                nt=round(ltp+atr*1.2,1)
                if nt<trail_sl: trail_sl=nt
            if ltp>=trail_sl:
                pnl=entry-trail_sl; closed.append({"symbol":sym,"side":side,"status":"TRAIL_SL","pnl":round(pnl,2),"entry":entry,"exit":trail_sl})
                pnl_hist.append({"date":today_str,"symbol":sym,"pnl":round(pnl,2),"status":"TRAIL_SL","time":today.strftime("%H:%M")}); continue
        trade["ltp"]=ltp; trade["trail_sl"]=trail_sl; trade["highest"]=highest; trade["lowest"]=lowest; new_active.append(trade)
    except: new_active.append(trade)

results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futs=[ex.submit(fast_analyze,(s,obj,from_d,to_d,nifty_trend)) for s in SCAN_LIST]
    for f in concurrent.futures.as_completed(futs):
        r=f.result()
        if r: results.append(r)

def get_top(cat,side,exclude=[]):
    filt=[x for x in results if x["cat"]==cat and x["side"]==side and x["sym"] not in exclude]
    if not filt: return None
    return sorted(filt, key=lambda x: x["score"], reverse=True)[0]

existing_syms=[a["symbol"] for a in new_active]+[c["symbol"] for c in closed]
final_trades=[]
for combo in [("SMALL","BUY"),("MID","BUY"),("SMALL","SELL"),("MID","SELL"),("SMALL","BUY"),("MID","BUY"),("SMALL","BUY"),("MID","SELL")]:
    if len(final_trades)>=DAILY_TARGET: break
    t=get_top(combo[0],combo[1],existing_syms+[x["sym"] for x in final_trades])
    if t: final_trades.append(t)

if len(final_trades)<4:
    for combo in [("LARGE","BUY"),("LARGE","SELL")]:
        t=get_top(combo[0],combo[1],existing_syms+[x["sym"] for x in final_trades])
        if t: final_trades.append(t)

today_count=state.get("today_count",0)+len(closed)
combined_active=new_active[:]
pending=state.get("pending",[])
while len(combined_active)<MAX_ACTIVE and (pending or final_trades):
    if pending: nxt=pending.pop(0)
    else:
        nxt=final_trades.pop(0)
        nxt={"symbol":nxt["sym"],"side":nxt["side"],"cat":nxt["cat"],"price":nxt["ltp"],"sl":nxt["sl"],"t1":nxt["t1"],"t2":nxt["t2"],"trail_sl":nxt["sl"],"highest":nxt["ltp"],"lowest":nxt["ltp"],"atr":nxt["atr"],"time":today.strftime("%H:%M"),"score":nxt["score"]}
    if not any(a["symbol"]==nxt["symbol"] for a in combined_active):
        if today_count<DAILY_TARGET:
            combined_active.append(nxt); today_count+=1
        else: pending.append(nxt)

for x in final_trades:
    if len(pending)<6:
        pending.append({"symbol":x["sym"],"side":x["side"],"cat":x["cat"],"price":x["ltp"],"sl":x["sl"],"t1":x["t1"],"t2":x["t2"],"trail_sl":x["sl"],"highest":x["ltp"],"lowest":x["ltp"],"atr":x["atr"],"time":today.strftime("%H:%M"),"score":x["score"]})

combined_active=combined_active[:MAX_ACTIVE]
save_state(combined_active,pending,today_count,today_str); save_pnl(pnl_hist)

today_pnl=sum([p["pnl"] for p in pnl_hist if p["date"]==today_str]); total_pnl=sum([p["pnl"] for p in pnl_hist])
win=len([p for p in pnl_hist if p["pnl"]>0]); loss=len([p for p in pnl_hist if p["pnl"]<0]); total_trades=len(pnl_hist)
win_today=len([p for p in pnl_hist if p["date"]==today_str and p["pnl"]>0]); loss_today=len([p for p in pnl_hist if p["date"]==today_str and p["pnl"]<0])

buy_res=[r for r in results if r["side"]=="BUY"]
sell_res=[r for r in results if r["side"]=="SELL"]

msg=f"⚡ v11 FULL | SMALL+MID + 5m BO/BD | Nifty:{nifty_trend} | {today.strftime('%H:%M:%S')}\n"
msg+=f"Scan 1000/1000 | Found {len(results)} (B:{len(buy_res)} S:{len(sell_res)}) | Daily {today_count}/{DAILY_TARGET}\n"
msg+=f"L:{len([x for x in results if x['cat']=='LARGE'])} M:{len([x for x in results if x['cat']=='MID'])} S:{len([x for x in results if x['cat']=='SMALL'])} <- REAL!\n"
msg+="--------------------------------\n"

if buy_res:
    small_buy=[x for x in buy_res if x["cat"] in ["SMALL","MID"]]
    if small_buy:
        top_buy=sorted(small_buy, key=lambda x: x["day_chg"], reverse=True)[:6]
        msg+=f"🔥 BULLISH SMALL+MID 5m-BO ({len(small_buy)}):\n"
        for b in top_buy:
            msg+=f"{b['sym']}({b['cat']}) P:{b['ltp']} Chg:{b['day_chg']:.1f}% 5m:{b['last_5m']:.1f}% | {','.join(b['conds'][:2])}\n"
        msg+="--------------------------------\n"

if sell_res:
    small_sell=[x for x in sell_res if x["cat"] in ["SMALL","MID"]]
    if small_sell:
        top_sell=sorted(small_sell, key=lambda x: x["day_chg"])[:4]
        msg+=f"🔻 BEARISH SMALL+MID 5m-BD ({len(small_sell)}):\n"
        for b in top_sell:
            msg+=f"{b['sym']}({b['cat']}) P:{b['ltp']} Chg:{b['day_chg']:.1f}% | {','.join(b['conds'][:2])}\n"
        msg+="--------------------------------\n"

burst=[r for r in results if "5m-BO" in str(r["conds"]) or "5m-BD" in str(r["conds"]) or "ORB-BO" in str(r["conds"])]
if burst:
    msg+=f"⚡ 5 MIN BREAKOUT/BREAKDOWN:\n"
    for m in sorted(burst, key=lambda x: x["last_5m"], reverse=True)[:5]:
        msg+=f"{m['side']} {m['sym']}({m['cat']}) {m['ltp']} {','.join(m['conds'][:2])}\n"
    msg+="--------------------------------\n"

if closed:
    msg+=f"📊 CLOSED ({len(closed)}):\n"
    for c in closed: msg+=f"{c['side']} {c['symbol']} PnL:{c['pnl']}\n"
    msg+="--------------------------------\n"
msg+=f"🔄 ACTIVE ({len(combined_active)}/{MAX_ACTIVE}):\n"
for a in combined_active:
    msg+=f"{a['side']} {a['symbol']}({a.get('cat','')}) E:{a['price']} LTP:{a.get('ltp','')} Trail:{a.get('trail_sl','')} S:{a.get('score','')}\n"
msg+="--------------------------------\n"
msg+=f"📈 TODAY: {today_pnl:.2f} | TOTAL: {total_pnl:.2f} | W:{win_today} L:{loss_today}\n"
msg+=f"v11: 5m-BO/BD | ORB-BO/BD | S/M Thresh 2.0/1.6 | Day Green=BUY\n"

send_tg(os.getenv("TELEGRAM_BOT_TOKEN","").strip(), os.getenv("TELEGRAM_CHAT_ID","").strip(), msg)
print(msg)
