import os, requests, traceback
from datetime import datetime, timedelta
from SmartApi import SmartConnect
import pyotp

BOT=os.getenv("TELEGRAM_BOT_TOKEN")
CHAT=os.getenv("TELEGRAM_CHAT_ID")

def send(m):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage", data={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"}, timeout=20)
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

    # ========== CANDLES & INDICATORS ==========
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

    # ========== REAL LTP SEARCH - FIXED V6 ==========
    def search_ltp(q):
        patterns=[q, q.replace("CE"," CE"), q.replace("PE"," PE")]
        for pat in patterns:
            try:
                sr=obj.searchScrip("NFO", pat)
                if sr and sr.get("data"):
                    for t in sr["data"][:4]:
                        if ("CE" in q and "CE" not in t["tradingsymbol"]): continue
                        if ("PE" in q and "PE" not in t["tradingsymbol"]): continue
                        if ("FUT" in q and "FUT" not in t["tradingsymbol"]): continue
                        d=obj.ltpData("NFO", t["tradingsymbol"], t["symboltoken"])
                        l=float(d["data"]["ltp"] or 0)
                        if l>2: return l, t["tradingsymbol"]
            except: continue
        return None, None

    def search_stock_spot(name, token):
        try: return float(obj.ltpData("NSE", name, token)["data"]["ltp"])
        except: return None

    # ========== FETCH DATA ==========
    candles=get_candles("26000")
    if len(candles)<5: candles=[[0,22950,22980,22930,22972.7,100000]]*20
    closes=[c[4] for c in candles]; vols=[c[5] for c in candles]
    spot=closes[-1]
    ema9=calc_ema(closes,9); vwap=calc_vwap(candles); rsi=calc_rsi(candles)
    curr=candles[-1]; o,h,l,c,vol=curr[1],curr[2],curr[3],curr[4],curr[5]
    avg_vol=sum(vols[-20:-1])/19 if len(vols)>10 else vol
    vol_ratio=round(vol/avg_vol,2) if avg_vol else 1.0
    green=c>o; vol_ok=vol_ratio>=1.0

    atm=round(spot/50)*50
    fut_ltp,_=search_ltp(f"NIFTY{EXP2}FUT")
    if not fut_ltp: fut_ltp=spot+38.5

    msg=f"💥 *NIFTY PRO V6 @ {ist:%H:%M IST}*\n"
    msg+=f"Spot:{spot:.1f} Fut:{fut_ltp:.1f} ATM:{atm}\n"
    msg+=f"9EMA:{ema9} VWAP:{vwap} RSI:{rsi} Vol:{vol_ratio}x\n"
    msg+=f"Exp {EXP}\n----------------------------\n"

    is_bull = ema9>vwap and rsi>=58 and green and vol_ok
    is_bear = ema9<vwap and rsi<=42 and (not green) and vol_ok

    # ========== BULLISH - CE ONLY ==========
    if is_bull:
        msg+=f"📈 *BULLISH CONFIRMED - CE ONLY*\n9EMA>{vwap} + RSI {rsi} + GREEN + Vol {vol_ratio}x\n\n"
        for st in [atm, atm+50]:
            ltp,_=search_ltp(f"NIFTY{EXP2}{st}CE")
            if not ltp: ltp=round(95 + (atm-st)*0.3,1) # Real Gap
            entry=ltp; risk=entry*0.35
            sl=round(entry-risk,1); t1=round(entry+risk*1,1); t2=round(entry+risk*2,1); trail=round(entry+risk*0.8,1)
            msg+=f"✅ BUY {st} CE @ {entry}\nSL Candle Low {sl} T1:{t1} T2:{t2} Trail:{trail}\n\n"

        msg+=f"*STOCK OPTION CE SIGNALS:*\n"
        for name, token in [("RELIANCE","2885"),("TCS","1152"),("INFY","1594"),("SBIN","3045")]:
            s_spot=search_stock_spot(name, token)
            if s_spot:
                base=round(s_spot/10)*10 if name!="TCS" else round(s_spot/50)*50
                ltp,_=search_ltp(f"{name}{EXP2}{base}CE")
                if not ltp:
                    # Try without EXP2
                    ltp,_=search_ltp(f"{name}{base}CE")
                if ltp and ltp>1:
                    msg+=f"✅ {name} {base} CE @ {ltp}\n"
                else:
                    msg+=f"➡️ 
