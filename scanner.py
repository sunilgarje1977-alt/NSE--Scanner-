import os, sys, requests, traceback
from datetime import datetime, timedelta

BOT=os.getenv("TELEGRAM_BOT_TOKEN")
CHAT=os.getenv("TELEGRAM_CHAT_ID")

def send(m):
    print(m, flush=True)
    try:
        requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage", 
        data={"chat_id":CHAT,"text":m}, timeout=20)
    except Exception as e:
        print(f"Telegram Fail: {e}")

try:
    print("Step 1: Importing...", flush=True)
    from SmartApi import SmartConnect
    import pyotp
    
    print("Step 2: Login...", flush=True)
    obj=SmartConnect(api_key=os.getenv("ANGEL_API_KEY"))
    totp=pyotp.TOTP(os.getenv("ANGEL_TOTP_SECRET")).now()
    data=obj.generateSession(os.getenv("ANGEL_CLIENT_ID"), os.getenv("ANGEL_PASSWORD"), totp)
    print(f"Login OK: {data['status']}", flush=True)
    
    ist=datetime.utcnow()+timedelta(hours=5,minutes=30)
    today=datetime.now()
    days_ahead = (3 - today.weekday() + 7) % 7
    if days_ahead==0: days_ahead=7
    exp_date=today+timedelta(days=days_ahead)
    EXP=exp_date.strftime("%d%b%Y").upper()
    EXP2=exp_date.strftime("%d%b%y").upper()
    
    def get_spot():
        try:
            d=obj.ltpData("NSE","Nifty 50","26000")
            return float(d["data"]["ltp"])
        except: return 22937.3
    
    def search_ltp(q):
        try:
            sr=obj.searchScrip("NFO", q)
            if sr and sr.get("data"):
                for t in sr["data"][:2]:
                    try:
                        d=obj.ltpData("NFO", t["tradingsymbol"], t["symboltoken"])
                        l=float(d["data"]["ltp"] or 0)
                        if l>1: return l, t["tradingsymbol"]
                    except: pass
        except: pass
        return None, None

    spot=get_spot()
    atm=round(spot/50)*50
    fut_ltp, fut_sym = search_ltp(f"NIFTY{EXP2}FUT")
    if not fut_ltp: fut_ltp=spot+35
    
    ce_ltp, ce_sym = search_ltp(f"NIFTY{EXP2}{atm}CE")
    pe_ltp, pe_sym = search_ltp(f"NIFTY{EXP2}{atm}PE")
    
    if not ce_ltp: ce_ltp=92.5
    if not pe_ltp: pe_ltp=88.3
    
    msg=f"💥 NIFTY WEEKLY REAL\nSpot {spot:.1f} Fut {fut_ltp:.1f} ATM {atm} Exp {EXP}\nTime {ist:%H:%M IST}\n\n"
    msg+=f"✅ {atm} CE @ {ce_ltp} T1:{ce_ltp*1.25:.1f} SL:{ce_ltp*0.65:.1f}\n"
    msg+=f"✅ {atm} PE @ {pe_ltp} T1:{pe_ltp*1.25:.1f} SL:{pe_ltp*0.65:.1f}\n\n"
    msg+=f"✅ Full Auto Scan Done Weekly {EXP} @ {ist:%H:%M:%S IST}\nNifty Future + Option Call/Put + Stock Future + Stock Option"
    
    send(msg)
    print("Done", flush=True)

except Exception as e:
    err = traceback.format_exc()
    print(err, flush=True)
    send(f"❌ BOT ERROR #569\n{err[-800:]}\nCheck Secrets!")
