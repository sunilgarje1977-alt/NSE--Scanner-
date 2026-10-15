import os, sys, subprocess
for p in ["logzero","websocket-client"]:
    try: __import__("logzero" if p=="logzero" else "websocket")
    except: subprocess.check_call([sys.executable,"-m","pip","install",p])
import requests, traceback
from datetime import datetime, timedelta
BOT=os.getenv("TELEGRAM_BOT_TOKEN")
CHAT=os.getenv("TELEGRAM_CHAT_ID")
def send(m):
    try: requests.post("https://api.telegram.org/bot"+BOT+"/sendMessage",data={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=15)
    except: pass
    print(m)

def get_expiry():
    today=datetime.now()
    days_ahead=3-today.weekday()
    if days_ahead<=0: days_ahead+=7
    exp=today+timedelta(days=days_ahead)
    return exp.strftime("%d%b%Y").upper(), exp.strftime("%b").upper()

try:
    from SmartApi import SmartConnect
    import pandas as pd, pyotp
    obj=SmartConnect(api_key=os.getenv("ANGEL_API_KEY"))
    totp=pyotp.TOTP(os.getenv("ANGEL_TOTP_SECRET")).now()
    obj.generateSession(os.getenv("ANGEL_CLIENT_ID"),os.getenv("ANGEL_PASSWORD"),totp)

    EXP_STR, EXP_MON = get_expiry()
    ist=datetime.utcnow()+timedelta(hours=5,minutes=30)
    today=ist.strftime("%Y-%m-%d")
    now=ist.strftime("%Y-%m-%d %H:%M")

    if ist.hour>=15 and ist.minute>15:
        send(f"Market Close {ist.strftime('%H:%M')} IST")
        exit(0)

    def get_nfo_ltp(search_text):
        try:
            sr=obj.searchScrip("NFO", search_text)
            if sr.get("data"):
                tsym=sr["data"][0]["tradingsymbol"]
                token=sr["data"][0]["symboltoken"]
                ltp=obj.ltpData("NFO", tsym, token)
                if ltp.get("data"):
                    return float(ltp["data"]["ltp"]), tsym
        except: pass
        return None, None

    def scan_nifty(name, spot_token, root):
        hp={"exchange":"NSE","symboltoken":spot_token,"interval":"FIVE_MINUTE","fromdate":today+" 09:15","todate":now}
        cd=obj.getCandleData(hp)
        if not cd.get("data") or len(cd["data"])<20: return
        df=pd.DataFrame(cd["data"],columns=["time","open","high","low","close","volume"])
        for c in ["close","open","high","low","volume"]: df[c]=pd.to_numeric(df[c])
        df["typ"]=(df["high"]+df["low"]+df["close"])/3
        df["vwap"]=(df["typ"]*df["volume"]).cumsum()/df["volume"].cumsum()
        df["9ema"]=df["close"].ewm(span=9).mean()
        df["20ema"]=df["close"].ewm(span=20).mean()
        d=df["close"].diff()
        g=d.where(d>0,0).rolling(14).mean()
        l=-d.where(d<0,0).rolling(14).mean()
        df["rsi"]=100-(100/(1+g/l))
        df["atr"]=(df["high"]-df["low"]).rolling(14).mean()
        c=df.iloc[-1]
        vol_blast=c["volume"]>df["volume"].rolling(20).mean().iloc[-1]*1.2

        bull=c["close"]>c["vwap"]*1.001 and c["9ema"]>c["20ema"] and 58<=c["rsi"]<=78 and c["close"]>c["open"]
        bear=c["close"]<c["vwap"]*0.999 and c["9ema"]<c["20ema"] and 20<=c["rsi"]<=46 and c["close"]<c["open"]

        step=100 if c["close"]>40000 else 50
        atm=round(c["close"]/step)*step

        if bull and vol_blast:
            ce_strike=atm+step
            opt_ltp, opt_sym = get_nfo_ltp(f"{root} {EXP_STR} {ce_strike} CE")
            fut_ltp, fut_sym = get_nfo_ltp(f"{root} {EXP_STR} FUTURE")
            if not fut_ltp:
                fut_ltp, fut_sym = get_nfo_ltp(f"{root} {EXP_MON} FUTURE")

            msg=f"💥🟢 *{name} LONG BLAST @ {c['close']:.1f}* | RSI {c['rsi']:.1f}\n"
            msg+=f"Spot {c['close']:.1f} > VWAP {c['vwap']:.1f} | Like RELIANCE 1180 CE Chart\n\n"
            if opt_ltp:
                msg+=f"📈 *NIFTY OPTION:*\n{opt_sym}\n"
                msg+=f"ENTRY {ce_strike} CE @ {opt_ltp:.1f}\n"
                msg+=f"🎯 T1 {round(opt_ltp*1.25,1)} (25%) | T2 {round(opt_ltp*1.6,1)} (60%)\n"
                msg+=f"🛑 SL {round(opt_ltp*0.7,1)} (30%)\n\n"
            if fut_ltp:
                msg+=f"🚀 *NIFTY FUTURE:*\n{fut_sym}\n"
                msg+=f"ENTRY FUT @ {fut_ltp:.1f}\n"
                msg+=f"🎯 T1 {round(fut_ltp+c['atr']*1.5,1)} | T2 {round(fut_ltp+c['atr']*3,1)}\n"
                msg+=f"🛑 SL {round(min(c['20ema'],c['vwap']),1)}\n\n"
            msg+=f"🔄 Trail: 9EMA {c['9ema']:.1f} खाली आला की EXIT\nExpiry {EXP_STR}"
            send(msg)

        if bear and vol_blast:
            pe_strike=atm-step
            opt_ltp, opt_sym = get_nfo_ltp(f"{root} {EXP_STR} {pe_strike} PE")
            fut_ltp, fut_sym = get_nfo_ltp(f"{root} {EXP_STR} FUTURE")
            if not fut_ltp:
                fut_ltp, fut_sym = get_nfo_ltp(f"{root} {EXP_MON} FUTURE")

            msg=f"💥🔴 *{name} SHORT BLAST @ {c['close']:.1f}* | RSI {c['rsi']:.1f}\n"
            msg+=f"Spot {c['close']:.1f} < VWAP {c['vwap']:.1f} | Like BHEL 430 PE +200%\n\n"
            if opt_ltp:
                msg+=f"📉 *NIFTY OPTION:*\n{opt_sym}\n"
                msg+=f"ENTRY {pe_strike} PE @ {opt_ltp:.1f}\n"
                msg+=f"🎯 T1 {round(opt_ltp*1.4,1)} (40%) | T2 {round(opt_ltp*2.0,1)} (100%)\n"
                msg+=f"🛑 SL {round(opt_ltp*0.65,1)}\n\n"
            if fut_ltp:
                msg+=f"🚀 *NIFTY FUTURE SHORT:*\n{fut_sym}\n"
                msg+=f"ENTRY FUT SHORT @ {fut_ltp:.1f}\n"
                msg+=f"🎯 T1 {round(fut_ltp-c['atr']*1.5,1)} | T2 {round(fut_ltp-c['atr']*3,1)}\n"
                msg+=f"🛑 SL {round(max(c['20ema'],c['vwap']),1)}\n\n"
            msg+=f"🔄 Trail: 9EMA {c['9ema']:.1f} वर गेला की EXIT\nExpiry {EXP_STR}"
            send(msg)

    # NIFTY + BANKNIFTY
    for idx_name, root in [("Nifty 50","NIFTY"), ("Nifty Bank","BANKNIFTY")]:
        sr=obj.searchScrip("NSE", idx_name)
        if sr.get("data"):
            scan_nifty(idx_name, sr["data"][0]["symboltoken"], root)

    send(f"✅ Nifty Option+Future Scan Done @ {ist.strftime('%H:%M')} IST")
    exit(0)
except Exception as e:
    send(f"Error Nifty OF:\n{traceback.format_exc()[-700:]}")
    exit(0)
