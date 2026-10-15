 import os, requests, traceback
from datetime import datetime, timedelta
BOT=os.getenv("TELEGRAM_BOT_TOKEN")
CHAT=os.getenv("TELEGRAM_CHAT_ID")

def send(m):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage", data={"chat_id":CHAT,"text":m}, timeout=15)
        print(m)
    except Exception as e:
        print(f"TG Fail {e}")

try:
    from SmartApi import SmartConnect
    import pyotp
    obj=SmartConnect(api_key=os.getenv("ANGEL_API_KEY"))
    obj.generateSession(os.getenv("ANGEL_CLIENT_ID"), os.getenv("ANGEL_PASSWORD"), pyotp.TOTP(os.getenv("ANGEL_TOTP_SECRET")).now())
    ist=datetime.utcnow()+timedelta(hours=5,minutes=30)
    EXP=(datetime.now()+timedelta(days=(3-datetime.now().weekday()+7)%7 or 7)).strftime("%d%b%Y").upper()
    send(f"🧪 Manual Test @ {ist:%H:%M IST} - Checking Real PA...")

    def get_ltp(exch, symbol):
        try:
            sr=obj.searchScrip(exch, symbol)
            if sr.get("data"):
                d=obj.ltpData(exch, sr["data"][0]["tradingsymbol"], sr["data"][0]["symboltoken"])
                if d.get("data"): return float(d["data"]["ltp"]), sr["data"][0]["tradingsymbol"]
        except: pass
        return None, None

    def get_opt_ltp(full_sym):
        try:
            sr=obj.searchScrip("NFO", full_sym)
            if sr.get("data"):
                t=sr["data"][0]
                d=obj.ltpData("NFO", t["tradingsymbol"], t["symboltoken"])
                if d.get("data"): return float(d["data"]["ltp"]), t["tradingsymbol"]
        except: pass
        return None, None

    def levels(entry):
        t1=round(entry*1.25,1); t2=round(entry*1.5,1); t3=round(entry*2.0,1)
        sl=round(entry*0.65,1); trail=round(entry*0.85,1)
        return t1,t2,t3,sl,trail

    # ===== 1. NIFTY FUTURE + OPTION CALL PUT =====
    spot,sym=get_ltp("NSE","Nifty 50")
    if spot:
        atm=round(spot/50)*50
        fut_ltp,_=get_opt_ltp(f"NIFTY {EXP} FUT")
        msg=f"💥 NIFTY FUTURE REAL @ {fut_ltp or spot:.1f} Spot {spot:.1f} ATM {atm}\nExp {EXP}\n\n"
        # Option Call Put Premium 50-90
        for diff,typ in [(100,"CE"),(-200,"PE")]:
            strike=atm+diff
            ltp,osym=get_opt_ltp(f"NIFTY {EXP} {strike} {typ}")
            if ltp and 20 <= ltp <= 150:
                t1,t2,t3,sl,trail=levels(ltp)
                msg+=f"OPTION {strike} {typ} @ {ltp:.1f}\nEntry {ltp} | T1 {t1} T2 {t2} T3 {t3}\nSL {sl} Trail->{trail}\n{osym}\n\n"
        send(msg)

    # ===== 2. NSE FUTURE STOCK + OPTION CALL PUT =====
    STOCKS=["RELIANCE","BHEL","TCS","INFY","SBIN"]
    for STOCK in STOCKS:
        spot,sym=get_ltp("NSE",STOCK)
        if not spot: continue
        atm=round(spot/5)*5 if STOCK=="BHEL" else round(spot/10)*10
        fut_ltp,_=get_opt_ltp(f"{STOCK} {EXP} FUT")
        msg=f"💥 {STOCK} FUTURE REAL @ {fut_ltp or spot:.1f} Spot {spot:.1f} ATM {atm}\n"
        found=False
        for strike in [atm-20, atm, atm+20] if STOCK!="BHEL" else [atm-10, atm, atm+10]:
            for typ in ["CE","PE"]:
                ltp,osym=get_opt_ltp(f"{STOCK} {EXP} {strike} {typ}")
                if ltp and 20 <= ltp <= 150:
                    t1,t2,t3,sl,trail=levels(ltp)
                    msg+=f"OPT {strike} {typ} @ {ltp:.1f} E:{ltp} T1:{t1} SL:{sl} Trail:{trail}\n{osym}\n"
                    found=True
                    break
            if found: break
        if found: send(msg)

    send(f"✅ Full Auto Scan Done @ {ist:%H:%M IST} - Nifty Future + Option + Stock Future + Stock Option")

except Exception as e:
    err=traceback.format_exc()[-800:]
    print(err)
    send(f"❌ ERROR {err}") 
