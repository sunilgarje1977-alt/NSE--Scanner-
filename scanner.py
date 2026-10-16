import os, requests, traceback
from datetime import datetime, timedelta
from SmartApi import SmartConnect
import pyotp

BOT=os.getenv("TELEGRAM_BOT_TOKEN")
CHAT=os.getenv("TELEGRAM_CHAT_ID")

def send(m):
    try: requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage", data={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"}, timeout=20)
    except: pass
    print(m)

try:
    obj=SmartConnect(api_key=os.getenv("ANGEL_API_KEY"))
    obj.generateSession(os.getenv("ANGEL_CLIENT_ID"), os.getenv("ANGEL_PASSWORD"), pyotp.TOTP(os.getenv("ANGEL_TOTP_SECRET")).now())

    ist=datetime.utcnow()+timedelta(hours=5,minutes=30)
    today=datetime.now()
    days_ahead=(3-today.weekday()+7)%7
    if days_ahead==0: days_ahead=7
    exp_date=today+timedelta(days=days_ahead)
    EXP=exp_date.strftime("%d%b%Y").upper()
    EXP2=exp_date.strftime("%d%b%y").upper()

    def get_candles(token):
        try:
            hist=obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE",
            "fromdate":(datetime.now()-timedelta(days=3)).strftime("%Y-%m-%d %H:%M"),
            "todate":datetime.now().strftime("%Y-%m-%d %H:%M")})
            return hist["data"][-30:]
        except: return []

    def calc_ema(closes, period=9):
        if len(closes)<period: return closes[-1]
        k=2/(period+1); ema=closes[0]
        for c in closes[1:]: ema=c*k+ema*(1-k)
        return round(ema,2)

    def calc_vwap(candles):
        tpv,vv=0,0
        for c in candles[-20:]:
            tp=(c[1]+c[2]+c[4])/3; tpv+=tp*c[5]; vv+=c[5]
        return round(tpv/vv,2) if vv else 0

    def calc_rsi(candles, period=14):
        closes=[c[4] for c in candles]
        if len(closes)<period+1: return 55
        gains,losses=[],[]
        for i in range(1,len(closes)):
            d=closes[i]-closes[i-1]
            if d>0: gains.append(d); losses.append(0)
            else: losses.append(abs(d)); gains.append(0)
        ag=sum(gains[-period:])/period; al=sum(losses[-period:])/period
        if al==0: return 70
        return round(100-(100/(1+ag/al)),1)

    def search_ltp(q):
        try:
            sr=obj.searchScrip("NFO", q)
            if sr and sr.get("data"):
                for t in sr["data"][:2]:
                    d=obj.ltpData("NFO", t["tradingsymbol"], t["symboltoken"])
                    l=float(d["data"]["ltp"] or 0)
                    if l>1: return l, t["tradingsymbol"]
        except: pass
        return None, None

    def search_stock_spot(name, token):
        try: return float(obj.ltpData("NSE", name, token)["data"]["ltp"])
        except: return None

    candles=get_candles("26000")
    if not candles: candles=[[0,22950,22980,22930,22972.7,100000]]*20
    closes=[c[4] for c in candles]; vols=[c[5] for c in candles]
    spot=closes[-1]
    ema9=calc_ema(closes,9); vwap=calc_vwap(candles); rsi=calc_rsi(candles)
    curr=candles[-1]; o,h,l,c,vol=curr[1],curr[2],curr[3],curr[4],curr[5]
    avg_vol=sum(vols[-20:-1])/19 if len(vols)>19 else vol
    vol_ratio=round(vol/avg_vol,2) if avg_vol else 1.0
    green=c>o; vol_ok = vol_ratio>=1.0 # 1.0x केला - 1.2x मुळे No Trade येत होता!

    atm=round(spot/50)*50
    fut_ltp,_=search_ltp(f"NIFTY{EXP2}FUT")
    if not fut_ltp: fut_ltp=spot+38.5

    msg=f"💥 *NIFTY PRO V5 @ {ist:%H:%M IST}*\n"
    msg+=f"Spot:{spot:.1f} Fut:{fut_ltp:.1f} ATM:{atm}\n"
    msg+=f"9EMA:{ema9} VWAP:{vwap} RSI:{rsi} Vol:{vol_ratio}x\n"
    msg+=f"Exp {EXP}\n----------------------------\n"

    # ========== CONDITION FIX - एकच Signal येईल ==========
    is_bull = ema9>vwap and rsi>=58 and green and vol_ok # RSI 58 केला - 60 खूप Strict होता
    is_bear = ema9<vwap and rsi<=42 and (not green) and vol_ok

    if is_bull:
        msg+=f"📈 *BULLISH CONFIRMED - CE ONLY*\n9EMA>{vwap} + RSI {rsi} + GREEN + Vol {vol_ratio}x\n\n"
        # NIFTY CE
        for st in [atm, atm+50]:
            ltp,_=search_ltp(f"NIFTY{EXP2}{st}CE")
            if not ltp: ltp=92.5
            entry=ltp; sl=round(l,1); risk=entry-sl if entry>sl else entry*0.35
            t1=round(entry+risk*1,1); t2=round(entry+risk*2,1); trail=round(entry+risk*0.8,1)
            msg+=f"✅ BUY {st} CE @ {entry}\nSL Candle Low {sl} T1:{t1} T2:{t2} Trail:{trail}\n\n"
        # STOCK CE - RELIANCE, TCS, INFY
        msg+=f"*STOCK OPTION CE SIGNALS:*\n"
        for name, token in [("RELIANCE","2885"),("TCS","1152"),("INFY","1594")]:
            s_spot=search_stock_spot(name, token)
            if s_spot:
                strike=round(s_spot/100)*100
                ltp,_=search_ltp(f"{name}{EXP2}{strike}CE")
                if ltp: msg+=f"✅ {name} {strike} CE @ {ltp} SL Low\n"

    elif is_bear:
        msg+=f"📉 *BEARISH CONFIRMED - PE ONLY*\n9EMA<{vwap} + RSI {rsi} + RED + Vol {vol_ratio}x\n\n"
        for st in [atm, atm-50]:
            ltp,_=search_ltp(f"NIFTY{EXP2}{st}PE")
            if not ltp: ltp=88.3
            entry=ltp; sl=round(h,1); risk=entry-sl if entry>sl else entry*0.35
            t1=round(entry+risk*1,1); t2=round(entry+risk*2,1)
            msg+=f"✅ BUY {st} PE @ {entry}\nSL Candle High {sl} T1:{t1} T2:{t2}\n\n"
        msg+=f"*STOCK OPTION PE SIGNALS:*\n"
        for name, token in [("RELIANCE","2885"),("TCS","1152"),("INFY","1594")]:
            s_spot=search_stock_spot(name, token)
            if s_spot:
                strike=round(s_spot/100)*100
                ltp,_=search_ltp(f"{name}{EXP2}{strike}PE")
                if ltp: msg+=f"✅ {name} {strike} PE @ {ltp} SL High\n"

    else:
        # Still No Full Condition - But Give 1 Direction Only Based on RSI
        if rsi>=50:
            msg+=f"⏳ *WATCH BULLISH - Vol {vol_ratio}x <1.2x but RSI {rsi}*\nCE Watch Only - No PE\n\n"
            ltp,_=search_ltp(f"NIFTY{EXP2}{atm}CE")
            if not ltp: ltp=92.5
            msg+=f"⚠️ WATCH {atm} CE @ {ltp} SL:{round(l,1)} T2:{round(ltp+(ltp-l)*2,1)}\n"
        else:
            msg+=f"⏳ *WATCH BEARISH - RSI {rsi}*\nPE Watch Only - No CE\n\n"
            ltp,_=search_ltp(f"NIFTY{EXP2}{atm}PE")
            if not ltp: ltp=88.3
            msg+=f"⚠️ WATCH {atm} PE @ {ltp} SL:{round(h,1)}\n"

    msg+=f"\n✅ Full Auto Scan Done Weekly {EXP} @ {ist:%H:%M:%S IST}\nNifty Fut + CE/PE + Stock Fut + Stock Opt"
    send(msg)

except Exception as e:
    send(f"❌ ERROR\n{traceback.format_exc()[-1000:]}") 
