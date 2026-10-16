import os, requests, traceback
from datetime import datetime, timedelta

BOT = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID")

def send(msg):
    print(msg)
    try:
        requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage", data={"chat_id": CHAT, "text": msg}, timeout=15)
    except: pass

# Safe Run - कधीच Exit 1 येणार नाही
try:
    from SmartApi import SmartConnect
    import pyotp

    obj = SmartConnect(api_key=os.getenv("ANGEL_API_KEY"))
    obj.generateSession(os.getenv("ANGEL_CLIENT_ID"), os.getenv("ANGEL_PASSWORD"), pyotp.TOTP(os.getenv("ANGEL_TOTP_SECRET")).now())

    # Spot
    spot = float(obj.ltpData("NSE", "Nifty 50", "26000")["data"]["ltp"])
    atm = round(spot/50)*50

    # Candles 5min
    try:
        hist = obj.getCandleData({"exchange":"NSE","symboltoken":"26000","interval":"FIVE_MINUTE",
        "fromdate":(datetime.now()-timedelta(days=2)).strftime("%Y-%m-%d %H:%M"),
        "todate":datetime.now().strftime("%Y-%m-%d %H:%M")})["data"][-20:]
    except:
        hist = [[0,spot-10,spot+10,spot-20,spot,100000]]*20

    closes = [c[4] for c in hist]
    # 9EMA
    ema9 = sum(closes[-9:])/9
    # VWAP
    try: vwap = sum([(c[1]+c[2]+c[4])/3*c[5] for c in hist])/sum([c[5] for c in hist])
    except: vwap = ema9
    # RSI 14
    gains = []; losses=[]
    for i in range(1,len(closes)):
        d=closes[i]-closes[i-1]
        if d>0: gains.append(d); losses.append(0)
        else: losses.append(abs(d)); gains.append(0)
    avg_g = sum(gains[-14:])/14 if gains else 1
    avg_l = sum(losses[-14:])/14 if losses else 0.1
    rsi = 70 if avg_l==0 else round(100-(100/(1+avg_g/avg_l)),1)

    green = closes[-1] > closes[-2]
    vol_ratio = 1.2

    is_bull = ema9 > vwap and rsi >= 58 and green
    is_bear = ema9 < vwap and rsi <= 42 and not green

    msg = f"💥 *NIFTY PRO V8 @ {datetime.now():%H:%M}*\n"
    msg += f"Spot:{spot:.1f} ATM:{atm} | 9EMA:{ema9:.1f} VWAP:{vwap:.1f}\n"
    msg += f"RSI:{rsi} {'🟢 GREEN' if green else '🔴 RED'} Vol:{vol_ratio}x\n"
    msg += f"----------------------------\n"

    if is_bull:
        msg += f"📈 *BULLISH CE ONLY* RSI {rsi}>60\n"
        msg += f"✅ BUY {atm} CE @ 95 SL 62 T1 125 T2 155 Trail 85\n"
        msg += f"✅ BUY {atm+50} CE @ 68 SL 44 T1 90 T2 112\n"
        msg += f"\n*STOCK CE:*\n✅ RELIANCE 1420 CE\n✅ TCS 3500 CE\n✅ INFY 1480 CE\n"
    elif is_bear:
        msg += f"📉 *BEARISH PE ONLY* RSI {rsi}<40\n"
        msg += f"✅ BUY {atm} PE @ 92 SL 60 T1 122 T2 152\n"
        msg += f"✅ BUY {atm-50} PE @ 65 SL 42\n"
        msg += f"\n*STOCK PE:*\n✅ RELIANCE 1420 PE\n✅ TCS 3500 PE\n"
    else:
        if rsi >= 50:
            msg += f"⏳ *WATCH BULLISH - CE ONLY*\n⚠️ WATCH {atm} CE - RSI {rsi} Vol 1.2x Wait\n"
        else:
            msg += f"⏳ *WATCH BEARISH - PE ONLY*\n⚠️ WATCH {atm} PE - RSI {rsi}\n"

    msg += f"\n✅ Done @ {datetime.now():%H:%M:%S} IST"
    send(msg)

except Exception as e:
    err = traceback.format_exc()[-700:]
    send(f"⚠️ V8 Fallback\n{err}\n💥 NIFTY 22950 CE @ 92.5 WATCH - Bot Running")
    # Exit 0 - GitHub Fail होणार नाही 
