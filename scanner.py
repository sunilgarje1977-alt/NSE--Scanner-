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
    return exp.strftime("%d%b%Y").upper()

try:
    from SmartApi import SmartConnect
    import pandas as pd, pyotp
    obj=SmartConnect(api_key=os.getenv("ANGEL_API_KEY"))
    totp=pyotp.TOTP(os.getenv("ANGEL_TOTP_SECRET")).now()
    obj.generateSession(os.getenv("ANGEL_CLIENT_ID"),os.getenv("ANGEL_PASSWORD"),totp)

    ist=datetime.utcnow()+timedelta(hours=5,minutes=30)
    if ist.hour < 9 or (ist.hour==9 and ist.minute < 15):
        print(f"Market Not Open {ist.strftime('%H:%M')} IST - Skip")
        exit(0)
    if ist.hour >= 15 and ist.minute > 30:
        send(f"Market Closing {ist.strftime('%H:%M')} IST - No Fresh Trade, Morning Signal Follow करा")
        exit(0)

    EXP=get_expiry()
    today_str=ist.strftime("%Y-%m-%d")
    now_str=ist.strftime("%Y-%m-%d %H:%M")

    def get_ltp(txt):
        try:
            sr=obj.searchScrip("NFO", txt)
            if sr.get("data"):
                tsym=sr["data"][0]["tradingsymbol"]
                token=sr["data"][0]["symboltoken"]
                ltp=obj.ltpData("NFO", tsym, token)
                if ltp.get("data"): return float(ltp["data"]["ltp"]), tsym
        except: pass
        return None, None

    sr=obj.searchScrip("NSE","Nifty 50")
    spot_token=sr["data"][0]["symboltoken"]
    hp={"exchange":"NSE","symboltoken":spot_token,"interval":"FIVE_MINUTE","fromdate":today_str+" 09:15","todate":now_str}
    cd=obj.getCandleData(hp)
    if not cd.get("data") or len(cd["data"])<20:
        send(f"Real PA Data Fail @ {ist.strftime('%H:%M')}")
        exit(0)

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
    last=df.iloc[-1]

    spot=float(last["close"])
    vwap=float(last["vwap"])
    ema9=float(last["9ema"])
    ema20=float(last["20ema"])
    rsi=float(last["rsi"])
    atr=float(last["atr"])

    bull=spot > vwap*1.001 and ema9 > ema20 and 58 <= rsi <= 78 and last["close"] > last["open"] and last["volume"] > df["volume"].rolling(20).mean().iloc[-1]*1.2
    bear=spot < vwap*0.999 and ema9 < ema20 and 20 <= rsi <= 46 and last["close"] < last["open"] and last["volume"] > df["volume"].rolling(20).mean().iloc[-1]*1.2

    atm=round(spot/50)*50

    if bull:
        ce_atm=atm
        ce_otm=atm+100
        opt_ltp, opt_sym = get_ltp(f"NIFTY {EXP} {ce_otm} CE")
        fut_ltp, fut_sym = get_ltp(f"NIFTY {EXP} FUTURE")
        msg=f"💥 *CE Strike (Real PA):*\n• ATM: {ce_atm} CE\n• Best OTM: {ce_otm} CE (Premium 50-90)\n"
        if opt_ltp: msg+=f"• Entry: {ce_otm} CE @ {opt_ltp:.1f} | T1 {round(opt_ltp*1.25,1)} | T2 {round(opt_ltp*1.6,1)} | SL {round(opt_ltp*0.7,1)}\n"
        msg+=f"• Cash BUY | Nifty CE Call Buy\n"
        if fut_ltp: msg+=f"• Future: {fut_sym} @ {fut_ltp:.1f} | T1 {round(fut_ltp+atr*1.5,1)} | SL {round(min(ema20,vwap),1)}\n"
        msg+=f"• Spot {spot:.1f} > VWAP {vwap:.1f} | RSI {rsi:.1f} | 9EMA {ema9:.1f}\n• Trail: 9EMA Below EXIT | {EXP}"
        send(msg)
    elif bear:
        pe_atm=atm
        pe_otm=atm-200
        opt_ltp, opt_sym = get_ltp(f"NIFTY {EXP} {pe_otm} PE")
        fut_ltp, fut_sym = get_ltp(f"NIFTY {EXP} FUTURE")
        msg=f"💥 *PE Strike (Real PA):*\n• ATM: {pe_atm} PE\n• Best OTM: {pe_otm} PE (Premium 50-90)\n"
        if opt_ltp: msg+=f"• Entry: {pe_otm} PE @ {opt_ltp:.1f} | T1 {round(opt_ltp*1.4,1)} | T2 {round(opt_ltp*2.0,1)} | SL {round(opt_ltp*0.65,1)}\n"
        msg+=f"• Cash SELL | Nifty PE Put Buy\n"
        if fut_ltp: msg+=f"• Future SHORT: {fut_sym} @ {fut_ltp:.1f} | T1 {round(fut_ltp-atr*1.5,1)} | SL {round(max(ema20,vwap),1)}\n"
        msg+=f"• Spot {spot:.1f} < VWAP {vwap:.1f} | RSI {rsi:.1f} | 9EMA {ema9:.1f}\n• Trail: 9EMA Above EXIT | {EXP}"
        send(msg)
    else:
        send(f"Scanner OK {ist.strftime('%d-%b %H:%M')} Real PA Active No Signal @ {spot:.1f} VWAP {vwap:.1f} RSI {rsi:.1f}")

    exit(0)
except Exception as e:
    send(f"Error:\n{traceback.format_exc()[-700:]}")
    exit(0)
