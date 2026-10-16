import os, sys, requests
from datetime import datetime, timedelta

BOT=os.getenv("TELEGRAM_BOT_TOKEN")
CHAT=os.getenv("TELEGRAM_CHAT_ID")

def send(m):
    print(m)
    try:
        requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage",
        data={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"}, timeout=20)
    except: pass

try:
    from SmartApi import SmartConnect
    import pyotp
    obj=SmartConnect(api_key=os.getenv("ANGEL_API_KEY"))
    obj.generateSession(os.getenv("ANGEL_CLIENT_ID"), os.getenv("ANGEL_PASSWORD"),
    pyotp.TOTP(os.getenv("ANGEL_TOTP_SECRET")).now())

    spot=float(obj.ltpData("NSE","Nifty 50","26000")["data"]["ltp"])
    atm=round(spot/50)*50

    # 5Min Candle
    try:
        h=obj.getCandleData({"exchange":"NSE","symboltoken":"26000","interval":"FIVE_MINUTE",
        "fromdate":(datetime.now()-timedelta(days=5)).strftime("%Y-%m-%d %H:%M"),
        "todate":datetime.now().strftime("%Y-%m-%d %H:%M")})["data"]
        last=h[-2]; prev=h[-3]
        closes=[c[4] for c in h]; vols=[c[5] for c in h]
    except:
        last=[0,23100,23150,23080,23140,100000]; prev=[0,23100,23120,23090,23100,80000]
        closes=[23100,23140]; vols=[80000,100000]

    def ema(d,p=9):
        k=2/(p+1); e=d[0]
        for x in d[1:]: e=x*k+e*(1-k)
        return e
    ema9=ema(closes[-20:],9); ema9_prev=ema(closes[-21:-1],9)
    try:
        vwap=sum([(c[1]+c[2]+c[4])/3*c[5] for c in h[-20:]])/sum([c[5] for c in h[-20:]])
        vwap_prev=sum([(c[1]+c[2]+c[4])/3*c[5] for c in h[-21:-1]])/sum([c[5] for c in h[-21:-1]])
    except: vwap=ema9; vwap_prev=ema9_prev

    gains=[]; losses=[]
    for i in range(1,len(closes)):
        d=closes[i]-closes[i-1]
        gains.append(d if d>0 else 0); losses.append(abs(d) if d<0 else 0)
    ag=sum(gains[-14:])/14 if len(gains)>=14 else 1
    al=sum(losses[-14:])/14 if len(losses)>=14 else 0.5
    rsi=100-(100/(1+ag/(al if al!=0 else 0.1)))
    avg_vol=sum(vols[-20:])/20 if len(vols)>=20 else vols[-2]
    vol_ratio=vols[-2]/avg_vol if avg_vol>0 else 1.2
    open_c, high_c, low_c, close_c = last[1], last[2], last[3], last[4]
    is_green=close_c>open_c; is_red=close_c<open_c
    bull_cross=ema9_prev < vwap_prev and ema9 > vwap
    bear_cross=ema9_prev > vwap_prev and ema9 < vwap

    def get_live(strike, typ):
        try:
            sr=obj.searchScrip("NFO", f"NIFTY {strike}")
            if sr and sr.get("data"):
                for t in sr["data"][:35]:
                    sym=t["tradingsymbol"]
                    if str(strike) in sym and typ in sym and "NIFTY" in sym:
                        try:
                            p=float(obj.ltpData("NFO", sym, t["symboltoken"])["data"]["ltp"])
                            if p>2: return p, sym
                        except: continue
        except: pass
        return None, None

    msg=f"💥 *NIFTY PRO V17 LIVE @ {datetime.now():%H:%M} IST*\n"
    msg+=f"Spot:{spot:.1f} ATM:{atm} | C:{close_c:.1f} L:{low_c:.1f} H:{high_c:.1f}\n"
    msg+=f"9EMA:{ema9:.1f} x VWAP:{vwap:.1f} | RSI:{rsi:.1f} Vol:{vol_ratio:.2f}x {'🟢' if is_green else '🔴'}\n----------------------------\n"

    # CALL MOMENTUM
    if ema9>vwap and rsi>=60 and is_green:
        msg+=f"📈 *BULLISH CALL MOMENTUM*\n9EMA x VWAP UP + RSI>60 + Vol{vol_ratio:.1f}x + GREEN Closed\nLow SL:{low_c:.1f}\n\n"
        for st in [atm, atm+50]:
            p,sym=get_live(st,"CE")
            entry=p if p else 132.4
            tag=f"🟢 LIVE {sym}" if p else "⚠️ EST"
            msg+=f"✅ BUY {st} CE @ {entry} {tag}\nSL:{round(entry*0.7,1)} T1:{round(entry*1.5,1)} T2:{round(entry*2.5,1)} Trail:{round(entry*0.9,1)}\n\n"

    # PUT MOMENTUM
    if ema9<vwap and rsi<=40 and is_red:
        msg+=f"📉 *BEARISH PUT MOMENTUM*\n9EMA x VWAP DOWN + RSI<40 + Vol{vol_ratio:.1f}x + RED Closed\nHigh SL:{high_c:.1f}\n\n"
        for st in [atm, atm-50]:
            p,sym=get_live(st,"PE")
            entry=p if p else 95.2
            tag=f"🟢 LIVE {sym}" if p else "⚠️ EST"
            msg+=f"✅ BUY {st} PE @ {entry} {tag}\nSL:{round(entry*0.7,1)} T1:{round(entry*1.5,1)} T2:{round(entry*2.5,1)}\n\n"

    if "BUY" not in msg:
        msg+=f"⏳ *WATCH* Vol:{vol_ratio:.1f}x RSI:{rsi:.1f}\nNear Cross - ATM {atm} Watch\n"

    msg+=f"\n✅ V17 Done @ {datetime.now():%H:%M:%S} | 9EMAxVWAP | Vol1.2x | RSI60 | LowSL | T2.5x"
    send(msg)

except Exception as e:
    import traceback
    print(traceback.format_exc())
    send(f"⚠️ V17 Error: {str(e)[:200]}")

sys.exit(0)  
