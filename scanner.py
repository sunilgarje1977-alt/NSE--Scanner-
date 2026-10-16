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
    send(f"🧪 Manual Test @ {ist:%H:%M:%S IST} | Weekly Exp {EXP} | Real Time Check...")

    def get_spot(token,symbol):
        try:
            d=obj.ltpData("NSE",symbol,token)
            return float(d["data"]["ltp"])
        except: return None

    # === हाच Fix - इथेच करायचा आहे ===
    def get_nfo_ltp(tradingsym_text):
        try:
            sr=obj.searchScrip("NFO", tradingsym_text)
            if sr.get("data"):
                t=sr["data"][0]
                d=obj.ltpData("NFO", t["tradingsymbol"], t["symboltoken"])
                ltp=None
                if d.get("data") and float(d["data"]["ltp"])>0:
                    ltp=float(d["data"]["ltp"])
                if not ltp or ltp==0:
                    try:
                        o=obj.ohlcData("NFO", t["tradingsymbol"], t["symboltoken"])
                        if o.get("data"):
                            ltp=float(o["data"]["ltp"] or o["data"]["close"])
                    except: pass
                if ltp:
                    return ltp, t["tradingsymbol"]
        except: pass
        return None, None

    def calc_levels(e):
        return round(e*1.25,1), round(e*1.5,1), round(e*2.0,1), round(e*0.65,1), round(e*0.85,1)

    nifty_spot=get_spot("26000","Nifty 50")
    if nifty_spot:
        atm=round(nifty_spot/50)*50
        fut_ltp,fut_sym=get_nfo_ltp(f"NIFTY {EXP} FUT")
        fut_ltp=fut_ltp or nifty_spot
        header=f"💥 NIFTY WEEKLY REAL TIME\nSpot {nifty_spot:.1f} Fut {fut_ltp:.1f} ATM {atm}\nExp {EXP} Weekly\nTime {ist:%H:%M IST}\n\n"
        body=""; found=False
        for diff,typ in [(0,"CE"),(0,"PE"),(50,"CE"),(-50,"PE"),(100,"CE"),(-100,"PE")]:
            strike=atm+diff
            ltp,osym=get_nfo_ltp(f"NIFTY {EXP} {strike} {typ}")
            if ltp and 5<=ltp<=200:
                t1,t2,t3,sl,trail=calc_levels(ltp)
                body+=f"✅ {strike} {typ} @ {ltp:.1f}\nEntry {ltp:.1f} | T1 {t1} T2 {t2} T3 {t3}\nSL {sl} Trail {trail}\n{osym}\n\n"
                found=True
            if found and len(body.splitlines())>12: break
        send(header+body if found else f"💥 NIFTY Weekly Spot {nifty_spot:.1f} Fut {fut_ltp:.1f} ATM {atm} Exp {EXP}\nPremium Range बाहेर - 9:15 नंतर Real Signal @ {ist:%H:%M IST}")

    time.sleep(1)
    for STOCK,TOKEN in [("RELIANCE","2885"),("BHEL","3181")]:
        spot=get_spot(TOKEN,STOCK)
        if not spot: continue
        atm_s=round(spot/10)*10 if STOCK!="BHEL" else round(spot/5)*5
        fut_ltp,_=get_nfo_ltp(f"{STOCK} {EXP} FUT")
        fut_ltp=fut_ltp or spot
        msg=f"💥 {STOCK} WEEKLY FUT+OPT REAL\nSpot {spot:.1f} Fut {fut_ltp:.1f} ATM {atm_s}\nExp {EXP}\n\n"
        found=0
        strikes=[atm_s-20,atm_s,atm_s+20] if STOCK!="BHEL" else [atm_s-10,atm_s,atm_s+10]
        for strike in strikes:
            for typ in ["CE","PE"]:
                ltp,osym=get_nfo_ltp(f"{STOCK} {EXP} {strike} {typ}")
                if ltp and 5<=ltp<=200:
                    t1,t2,t3,sl,trail=calc_levels(ltp)
                    msg+=f"✅ {strike} {typ} @ {ltp:.1f} E:{ltp:.1f} T1:{t1} SL:{sl} Trail:{trail}\n{osym}\n"
                    found+=1
                    if found>=2: break
            if found>=2: break
        if found>0: send(msg)

    send(f"✅ Full Auto Scan Done Weekly {EXP} @ {ist:%H:%M:%S IST} - Nifty Future + Option Call/Put + Stock Future + Stock Option")
except Exception as e:
    send(f"❌ ERROR @ {datetime.utcnow()+timedelta(hours=5,minutes=30):%H:%M IST}\n{traceback.format_exc()[-900:]}") 
