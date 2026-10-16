import os, sys, requests, time
from datetime import datetime, timedelta

BOT = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID")

def send(m):
    print(m)
    try:
        requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage",
        data={"chat_id": CHAT, "text": m, "parse_mode": "Markdown"}, timeout=20)
    except:
        pass

def get_scanner_data(obj):
    # Spot
    spot = float(obj.ltpData("NSE", "Nifty 50", "26000")["data"]["ltp"])
    atm = round(spot / 50) * 50
    # Candle 1Min + 5Min
    hist = obj.getCandleData({
        "exchange": "NSE",
        "symboltoken": "26000",
        "interval": "ONE_MINUTE",
        "fromdate": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M"),
        "todate": datetime.now().strftime("%Y-%m-%d %H:%M")
    })["data"]
    h = hist
    last = h[-2]
    closes = [c[4] for c in h]
    vols = [c[5] for c in h]

    def ema(data, p=9):
        k = 2/(p+1); e = data[0]
        for x in data[1:]: e = x*k + e*(1-k)
        return e

    ema9 = ema(closes[-20:], 9)
    vwap = sum([(c[1]+c[2]+c[4])/3 * c[5] for c in h[-20:]]) / sum([c[5] for c in h[-20:]])

    gains=[]; losses=[]
    for i in range(1,len(closes)):
        d=closes[i]-closes[i-1]
        gains.append(d if d>0 else 0)
        losses.append(abs(d) if d<0 else 0)
    ag=sum(gains[-14:])/14 if len(gains)>=14 else 1
    al=sum(losses[-14:])/14 if len(losses)>=14 else 0.5
    rsi=100-(100/(1+ag/(al if al!=0 else 0.1)))

    open_c, high_c, low_c, close_c = last[1], last[2], last[3], last[4]
    is_green = close_c > open_c

    # LIVE Option Price
    def get_live(strike, typ):
        try:
            s = obj.searchScrip("NFO", f"NIFTY {strike}")
            if s and s.get("data"):
                for t in s["data"][:40]:
                    sym=t["tradingsymbol"]
                    if str(strike) in sym and typ in sym and "NIFTY" in sym:
                        try:
                            ltp=float(obj.ltpData("NFO", sym, t["symboltoken"])["data"]["ltp"])
                            if ltp>2: return ltp, sym
                        except: continue
        except: pass
        return None, None

    return spot, atm, ema9, vwap, rsi, last, is_green, get_live

try:
    from SmartApi import SmartConnect
    import pyotp
    obj = SmartConnect(api_key=os.getenv("ANGEL_API_KEY"))
    obj.generateSession(os.getenv("ANGEL_CLIENT_ID"), os.getenv("ANGEL_PASSWORD"), pyotp.TOTP(os.getenv("ANGEL_TOTP_SECRET")).now())

    # 1 MIN LOOP - 14 Times = 14 Min Real-Time Data
    for i in range(14):
        try:
            now = datetime.now()
            # Market Time Check 9:15 to 3:35
            if now.hour < 9 or (now.hour==9 and now.minute<15) or now.hour>15 or (now.hour==15 and now.minute>35):
                send(f"⏳ Market Closed @ {now:%H:%M} - V20 1Min Scanner Standby")
                break

            spot, atm, ema9, vwap, rsi, last, is_green, get_live_fn = get_scanner_data(obj)
            low_c = last[3]; high_c = last[2]; close_c = last[4]

            msg = f"⚡ *NIFTY 1MIN LIVE #{i+1} @ {now:%H:%M:%S} IST*\n"
            msg += f"Spot:{spot:.1f} ATM:{atm} | C:{close_c:.1f}\n"
            msg += f"9EMA:{ema9:.1f} x VWAP:{vwap:.1f} | RSI:{rsi:.0f} {'🟢' if is_green else '🔴'}\n"
            msg += "----------------------------\n"

            if ema9 > vwap and rsi >= 58 and is_green:
                msg += f"📈 *BULLISH CALL*\n"
                for st in [atm, atm+50]:
                    p,sym = get_live_fn(st,"CE")
                    entry = p if p else 0
                    if entry:
                        msg += f"✅ BUY {st} CE @ {entry} 🟢 LIVE {sym}\nSL:{round(entry*0.7,1)} T1:{round(entry*1.5,1)} T2:{round(entry*2.5,1)}\n\n"
                    else:
                        msg += f"✅ BUY {st} CE @ Market (LTP Fetching...)\n\n"
            elif ema9 < vwap and rsi <= 42 and not is_green:
                msg += f"📉 *BEARISH PUT*\n"
                for st in [atm, atm-50]:
                    p,sym = get_live_fn(st,"PE")
                    entry = p if p else 0
                    if entry:
                        msg += f"✅ BUY {st} PE @ {entry} 🟢 LIVE {sym}\nSL:{round(entry*0.7,1)} T1:{round(entry*1.5,1)}\n\n"
            else:
                msg += f"⏳ WATCH - Near 9EMA Cross\n"

            msg += f"V20 1MIN Done #{i+1}/14"
            send(msg)

        except Exception as inner_e:
            send(f"⚠️ Loop {i+1} Error: {str(inner_e)[:100]}")

        # 1 MIN WAIT - Real Time
        if i < 13:
            time.sleep(60)

except Exception as e:
    import traceback; traceback.print_exc()
    send(f"❌ V20 Error @ {datetime.now():%H:%M} : {str(e)[:150]}")

sys.exit(0) 
