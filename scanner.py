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

TRUE_SMALL_MID = set(["PRAJIND","DAMCAPITAL","RSYSTEMS","SMCGLOBAL","SYNCOMF","SDBL","ZENSAR","VBL","NBCC","KPITTECH","RAILTEL","IRCON","MAZAGON","TITAGARH","JWL","SUZLON","ZOMATO","YESBANK","IEX","PAYTM","IDEA","NHPC","SJVN","SAIL","COCHINSHIP","HUDCO","BEML","BHEL","PFC","RECLTD","IREDA","RVNL","IRFC","BSE","MCX","DIXON","KAYNES","POLYCAB","COFORGE","PERSISTENT","GRSE","BEL","HAL"])

PRIORITY = ["PRAJIND","COCHINSHIP","JWL","TITAGARH","GRSE","HUDCO","NBCC","ZENSAR","VBL","DAMCAPITAL","RSYSTEMS","SMCGLOBAL","SYNCOMF","SDBL","RVNL","IRFC","BEML","BHEL","PFC","RECLTD","IREDA","SUZLON","ZOMATO","YESBANK","IEX","PAYTM","IDEA","BSE","MCX","DIXON","KAYNES","POLYCAB","COFORGE","PERSISTENT","NHPC","SJVN","NMDC","SAIL","KPITTECH","RAILTEL","IRCON","MAZAGON","BHARTIARTL","SBIN","RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","ITC","LT","KOTAKBANK","BAJFINANCE","AXISBANK","MARUTI","TITAN","SUNPHARMA"]

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
        last_10_high = max(highs[-10:-1]) if len(highs)>=11 else max(highs[:-1])
        last_10_low = min(lows[-10:-1]) if len(lows)>=11 else min(lows[:-1])
        buy=0; sell=0; bc=[]; sc=[]
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
        if ltp > last_10_high * 1.0005:
            if volx>=0.9: buy+=2.8; bc.append(f"5m-BO {((ltp-last_10_high)/last_10_high*100):.1f}%")
            else: buy+=1.5; bc.append("5m-BO")
        if ltp < last_10_low * 0.9995:
            if volx>=0.9: sell+=2.8; sc.append(f"5m-BD {((last_10_low-ltp)/ltp*100):.1f}%")
            else: sell+=1.5; sc.append("5m-BD")
        if ltp > orb_high * 1.001: buy+=2.0; bc.append(f"ORB-BO {((ltp-orb_high)/orb_high*100):.1f}%")
        if ltp < orb_low * 0.999: sell+=2.0; sc.append(f"ORB-BD {((orb_low-ltp)/orb_low*100):.1f}%")
        if st_dir==1 and ltp>orb_high: buy+=1; bc.append("ST+ORB")
        if st_dir==-1 and ltp<orb_low: sell+=1; sc.append("ST+ORB")

        # ===== v13 BULLISH FIX - Nifty DOWN मध्ये पण Bullish येईल =====
        if is_small_mid:
            nifty_down_bonus = 1.5 if nifty_trend=="DOWN" and day_gain_pct>0 else 0
            if day_gain_pct >= 0.1:
                if day_gain_pct >= 0.5: buy+=2.5; bc.append(f"SM-DAY+ {day_gain_pct:.1f}%")
                else: buy+=1.0; bc.append(f"DAY+ {day_gain_pct:.1f}%")
                if last_5m_chg >= 0.10: buy+=1.2; bc.append(f"S-MOM {last_5m_chg:.1f}%")
                if ltp >= day_high*0.994: buy+=1.0; bc.append("NEAR-HIGH")
                if recovery_pct >= 0.8: buy+=1.0; bc.append(f"RECOV {recovery_pct:.1f}%")
                if nifty_down_bonus>0: buy+=nifty_down_bonus; bc.append(f"VS-NIFTY+{nifty_down_bonus}")
            if day_gain_pct <= -0.2:
                if day_gain_pct <= -0.5: sell+=2.5; sc.append(f"SM-DAY- {day_gain_pct:.1f}%")
                else: sell+=1.0; sc.append(f"DAY- {day_gain_pct:.1f}%")
                if last_5m_chg <= -0.10: sell+=1.2; sc.append(f"S-DN {last_5m_chg:.1f}%")
                if fall_from_high >= 0.8: sell+=1.0; sc.append(f"FALL {fall_from_high:.1f}%")

        if cat=="SMALL":
            if buy>0: buy+=1.0; bc.append("S-BONUS")
            if sell>0: sell+=1.0; sc.append("S-BONUS")
        elif cat=="MID":
            if buy>0: buy+=0.7; bc.append("M-BONUS")
            if sell>0: sell+=0.7; sc.append("M-BONUS")

        buy_thresh = 1.8 if is_small_mid else 3.5
        sell_thresh = 1.4 if is_small_mid else 3.0

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
        nxt={"symbol":nxt["sym"],"side":nxt["side"],"cat":nxt["cat
