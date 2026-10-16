import os, requests, traceback, time
from datetime import datetime, timedelta
BOT=os.getenv("TELEGRAM_BOT_TOKEN")
CHAT=os.getenv("TELEGRAM_CHAT_ID")
def send(m):
    print(m)
    try: requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage", data={"chat_id":CHAT,"text":m}, timeout=20)
    except: pass
try:
    from SmartApi import SmartConnect
    import pyotp
    obj=SmartConnect(api_key=os.getenv("ANGEL_API_KEY"))
    obj.generateSession(os.getenv("ANGEL_CLIENT_ID"), os.getenv("ANGEL_PASSWORD"), pyotp.TOTP(os.getenv("ANGEL_TOTP_SECRET")).now())
    ist=datetime.utcnow()+timedelta(hours=5,minutes=30)
    today=datetime.now()
    days_ahead=(1-today.weekday()+7)%7
    weekly_date=today if days_ahead==0 else today+timedelta(days=days_ahead)
    EXP=weekly_date.strftime("%d%b%Y").upper()
    EXP2=EXP.replace("2026","26")
    send(f"Manual Test @ {ist:%H:%M:%S IST} | Weekly Exp {EXP} | Real Time Check...")

    def get_spot(token,symbol):
        try:
            d=obj.ltpData("NSE",symbol,token)
            return float(d["data"]["ltp"])
        except: return None

    def get_nfo_ltp(q):
        lst=[q, q.replace(" ",""), q.replace("2026","26"), q.replace(" ","").replace("2026","26")]
        if "FUT" in q:
            lst+=[f"NIFTY{EXP}FUT", f"NIFTY{EXP2}FUT", f"NIFTY{EXP}FUT".replace(" ","")]
        if "CE" in q or "PE" in q:
            try:
                p=q.split()
                st=[x for x in p if x.isdigit()][0]
                ty="CE" if "CE" in q else "PE"
                lst+=[f"NIFTY{EXP}{st}{ty}", f"NIFTY{EXP2}{st}{ty}"]
            except: pass
        for tq in lst:
            try:
                sr=obj.searchScrip("NFO", tq)
                if sr.get("data"):
                    for t in sr["data"][:3]:
                        try:
                            d=obj.ltpData("NFO", t["tradingsymbol"], t["symboltoken"])
                            l=float(d["data"]["ltp"] or 0)
                            if l>0: return l, t["tradingsymbol"]
                        except: pass
                        try:
                            o=obj.ohlcData("NFO", t["tradingsymbol"], t["symboltoken"])
                            l=float(o["data"].get("close") or o["data"].get("ltp") or 0)
                            if l>0: return l, t["tradingsymbol"]
                        except: pass
            except: pass
        return None, None

    def calc(e): return round(e*1.25,1), round(e*1.5,1), round(e*2.0,1), round(e*0.65,1), round(e*0.85,1)

    spot=get_spot("26000","Nifty 50")
    if spot:
        atm=round(spot/50)*50
        fut,_=get_nfo_ltp(f"NIFTY {EXP} FUT")
        fut=fut or spot
        head=f"NIFTY WEEKLY REAL Spot {spot:.1f} Fut {fut:.1f} ATM {atm} Exp {EXP} {ist:%H:%M IST}\n\n"
        body=""; ok=False
        for df,ty in [(0,"CE"),(0,"PE"),(50,"CE"),(-50,"PE")]:
            st=atm+df
            ltp,sym=get_nfo_ltp(f"NIFTY {EXP} {st} {ty}")
            if ltp and 5<=ltp<=200:
                t1,t2,t3,sl,tr=calc(ltp)
                body+=f"✅ {st} {ty} @ {ltp} E:{ltp} T1:{t1} T2:{t2} SL:{sl} Trail:{tr}\n{sym}\n\n"
                ok=True
            if ok and len(body)>300: break
        send(head+body if ok else f"NIFTY Weekly Spot {spot:.1f} Fut {fut:.1f} ATM {atm} Exp {EXP} Premium Range Baher - 9:15 nanter Real Signal @ {ist:%H:%M IST}")

    send(f"Full Auto Scan Done Weekly {EXP} @ {ist:%H:%M:%S IST}")
except Exception as e:
    send(f"ERROR {traceback.format_exc()[-800:]}")
