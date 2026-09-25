import os, pyotp, requests
from SmartApi import SmartConnect
from datetime import datetime, timedelta

REWARD_RATIO = 2.5

def send_telegram(msg):
    try:
        t=os.getenv("TELEGRAM_BOT_TOKEN"); c=os.getenv("TELEGRAM_CHAT_ID")
        requests.post(f"https://api.telegram.org/bot{t}/sendMessage", data={"chat_id":c,"text":msg,"parse_mode":"Markdown"}, timeout=10)
    except: pass

def get_clean_totp():
    return os.getenv("ANGEL_TOTP_SECRET","").replace(" ","").strip()

try:
    obj = SmartConnect(api_key=os.getenv("ANGEL_API_KEY"))
    obj.generateSession(os.getenv("ANGEL_CLIENT_ID"), os.getenv("ANGEL_PASSWORD"), pyotp.TOTP(get_clean_totp()).now())
    print("Login Done - WHIRLPOOL Pattern Scan")

    # Load 500 tokens
    master = requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json", timeout=20).json()
    eq = [d for d in master if d['exch_seg']=='NSE' and d['symbol'].endswith('-EQ')][:400]

    to_date = datetime.now()
    from_date = to_date - timedelta(days=2)

    matches = []
    for d in eq:
        try:
            p = {"exchange":"NSE","symboltoken":d['token'],"interval":"FIVE_MINUTE","fromdate":from_date.strftime("%Y-%m-%d %H:%M"),"todate":to_date.strftime("%Y-%m-%d %H:%M")}
            data = obj.getCandleData(p).get('data',[])
            if len(data) < 30: continue

            # Last 20 candles = Today's consolidation
            last20 = data[-25:-5]
            last5 = data[-5:]

            high20 = max(c[2] for c in last20)
            low20 = min(c[3] for c in last20)
            vol_avg = sum(c[5] for c in last20) / len(last20)

            curr = data[-1]
            curr_close, curr_high, curr_low, curr_vol = curr[4], curr[2], curr[3], curr[5]

            # WHIRLPOOL Logic
            consolidation = (high20 - low20) / low20 < 0.03 # 3% च्या आत flat होता
            breakout = curr_close > high20
            volume_spike = curr_vol > vol_avg * 1.8
            green_candle = curr[4] > curr[1]

            if consolidation and breakout and volume_spike and green_candle:
                risk = curr_high - curr_low
                if risk <=0: continue
                target = curr_close + risk*REWARD_RATIO
                gain = ((curr_close - data[-20][4]) / data[-20][4])*100
                matches.append(f"*{d['symbol'].replace('-EQ','')}* | ₹{curr_close} (+{round(gain,1)}%) | SL:{round(curr_low,1)} T:{round(target,1)} Vol:{round(curr_vol/vol_avg,1)}x")
        except:
            continue

    now = datetime.now().strftime('%d-%m %H:%M')
    if not matches:
        msg = f"📊 *WHIRLPOOL Type Scan (1:{REWARD_RATIO})*\n⏰ {now}\n❌ आज असा Breakout नाही\nConsolidation + Volume + Breakout चेक केले."
    else:
        msg = f"🚀 *WHIRLPOOL Pattern Found - {len(matches)} Stocks (1:{REWARD_RATIO})*\n⏰ {now}\n\n" + "\n\n".join(matches[:10])

    print(msg)
    send_telegram(msg)

except Exception as e:
    import traceback
    print(traceback.format_exc())
    send_telegram(f"Error: {e}")
