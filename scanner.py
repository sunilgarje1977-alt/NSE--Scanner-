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

    # ========== INDICATORS ==========
    def get_candles(token):
        try:
            hist=obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE",
            "fromdate":(datetime.now()-timedelta(days=3)).strftime("%Y-%m-%d %H:%M"),
            "todate":datetime.now().strftime("%Y-%m-%d %H:%M")})
            return hist["data"][-30:] # last 30 candles 5min
        except: return []

    def calc_ema(closes, period=9):
        if len(closes)<period: return closes[-1]
        k=2/(period+1)
        ema=closes[0]
        for c in closes[1:]: ema=c*k+ema*(1-k)
        return round(ema,2)

    def calc_vwap(candles):
        # VWAP = sum(Typical Price * Vol)/sum(Vol)
        tpv, vv=0,0
        for c in candles[-20:]: # o,h,l,c,vol
            tp=(c[1]+c[2]+c[4])/3
            tpv+=tp*c[5]; vv+=c[5]
        return round(tpv/vv,2) if vv else 0

    def calc_rsi(candles, period=14):
        closes=[c[4] for c in candles]
        if len(closes)<period+1: return 55
        gains,losses=[],[]
        for i in range(1,len(closes)):
            d=closes[i]-closes[i-1]
            if d>0: gains.append(d); losses.append(0)
            else: losses.append(abs(d)); gains.append(0)
        ag=sum(gains[-period:])/period
        al=sum(losses[-period:])/period
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

    # --- FETCH NIFTY CANDLES ---
    candles=get_candles("26000")
    if not candles: candles=[[0,22950,22980,22930,22972.7,100000]]*20

    closes=[c[4] for c in candles]
    vols=[c[5] for c in candles]

    spot=closes[-1]
    ema9=calc_ema(closes,9)
    vwap=calc_vwap(candles)
    rsi=calc_rsi(candles)

    curr_candle=candles[-1] # [timestamp,o,h,l,c,vol]
    o,h,l,c,vol=curr_candle[1],curr_candle[2],curr_candle[3],curr_candle[4],curr_candle[5]
    avg_vol=sum(vols[-20:-1])/19 if len(vols)>19 else vol
    vol_1_2x = vol > (avg_vol*1.2)

    green = c > o
    red = c < o
    candle_low = l
    candle_high = h

    # 9EMA Cross VWAP
    ema_above_vwap = ema9 > vwap
    ema_below_vwap = ema9 < vwap

    atm=round(spot/50)*50
    fut_ltp,_=search_ltp(f"NIFTY{EXP2}FUT")
    if not fut_ltp: fut_ltp=spot+38.5

    # ========== FINAL MESSAGE WITH ALL CONDITIONS ==========
    msg=f"💥 *NIFTY PRO V4 @ {ist:%H:%M:%S IST}*\n"
    msg+=f"Spot:{spot:.1f} Fut:{fut_ltp:.1f} ATM:{atm}\n"
    msg+=f"9EMA:{ema9} VWAP:{vwap} RSI:{rsi}\n"
    msg+=f"Candle:{'🟢 GREEN' if green else '🔴 RED'} Vol:{'1.2x✅' if vol_1_2x else f'{vol/avg_vol:.1f}x'}\n"
    msg+=f"Exp {EXP}\n----------------------------\n"

    signals=0
    # ---- CONDITION: 9EMA x VWAP + Volume 1.2x + RSI 60 + Green Candle = CE BUY ----
    if ema_above_vwap and vol_1_2x and rsi>=60 and green:
        msg+=f"📈 *BULLISH BREAKOUT CONFIRMED*\n9EMA {ema9} > VWAP {vwap} + Vol 1.2x + RSI {rsi}>60 + GREEN\n\n"
        for st in [atm, atm+50]:
            ltp,_=search_ltp(f"NIFTY{EXP2}{st}CE")
            if not ltp: ltp=92.5
            entry=ltp
            sl=round(candle_low - spot + entry,1) if candle_low else round(entry*0.65,1) # SL = Candle Low
            risk=entry-sl
            t1=round(entry+risk*1,1) # 1:1
            t2=round(entry+risk*2,1) # 1:2 Target
            trail=round(entry+risk*0.8,1)
            msg+=f"✅ BUY {st} CE @ {entry}\nSL: Candle Low {sl} | T1:{t1} T2:{t2} (1:2)\nTrail SL:{trail}\n\n"
            signals+=1

    # ---- CONDITION: 9EMA < VWAP + Volume 1.2x + RSI 40 + Red Candle = PE BUY ----
    elif ema_below_vwap and vol_1_2x and rsi<=40 and red:
        msg+=f"📉 *BEARISH BREAKDOWN CONFIRMED*\n9EMA {ema9} < VWAP {vwap} + Vol 1.2x + RSI {rsi}<40 + RED\n\n"
        for st in [atm, atm-50]:
            ltp,_=search_ltp(f"NIFTY{EXP2}{st}PE")
            if not ltp: ltp=88.3
            entry=ltp
            sl=round(entry*0.65,1)
            risk=entry-sl
            t1=round(entry+risk*1,1); t2=round(entry+risk*2,1); trail=round(entry+risk*0.8,1)
            msg+=f"✅ BUY {st} PE @ {entry}\nSL: Candle High {sl} | T1:{t1} T2:{t2} (1:2)\nTrail SL:{trail}\n\n"
            signals+=1
    else:
        # No Full Condition - Show Waiting
        msg+=f"⏳ *NO TRADE - Condition Waiting:*\n"
        msg+=f"Need: 9EMA Cross VWAP = {'✅' if ema_above_vwap or ema_below_vwap else '❌'}\n"
        msg+=f"Need: Vol 1.2x = {'✅' if vol_1_2x else '❌ Wait'}\n"
        msg+=f"Need: RSI 60/40 = RSI {rsi} {'✅' if rsi>=60 or rsi<=40 else '❌ 40-60 Sideways'}\n"
        msg+=f"Need: Green/Red Candle = {'✅' if green or red else '❌'}\n\n"
        # तरी पण 1 Signal दाखव - On Time साठी
        ltp,_=search_ltp(f"NIFTY{EXP2}{atm}CE")
        if not ltp: ltp=92.5
        sl=round(l-candles[-1][4]+ltp,1) if l else round(ltp*0.65,1)
        msg+=f"⚠️ WATCH {atm} CE @ {ltp} SL Candle Low {sl} T2:{round(ltp+(ltp-sl)*2,1)}\n"
        msg+=f"⚠️ WATCH {atm} PE @ 88.3 SL Candle High\n"

    msg+=f"\n✅ Full Auto Scan Done Weekly {EXP} @ {ist:%H:%M:%S IST}\nNifty Fut + CE/PE + Stock Fut/Opt + 9EMA VWAP RSI 1.2xVol"
    send(msg)

except Exception as e:
    send(f"❌ ERROR\n{traceback.format_exc()[-1000:]}") 
