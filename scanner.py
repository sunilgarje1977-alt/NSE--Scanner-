import os, pyotp, requests, traceback
from SmartApi import SmartConnect
from datetime import datetime, timedelta

REWARD_RATIO = 2.5

def get_clean_totp():
    s = os.getenv("ANGEL_TOTP_SECRET","").replace(" ","").strip()
    return s

def send_telegram(msg):
    try:
        t = os.getenv("TELEGRAM_BOT_TOKEN")
        c = os.getenv("TELEGRAM_CHAT_ID")
        requests.post(f"https://api.telegram.org/bot{t}/sendMessage", data={"chat_id":c, "text":msg, "parse_mode":"Markdown"}, timeout=10)
    except: pass

try:
    print(f"Starting Fast Scan 1:{REWARD_RATIO}")
    obj = SmartConnect(api_key=os.getenv("ANGEL_API_KEY"))
    totp = pyotp.TOTP(get_clean_totp()).now()
    obj.generateSession(os.getenv("ANGEL_CLIENT_ID"), os.getenv("ANGEL_PASSWORD"), totp)

    # Nifty 500 Direct URL - Fast
    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    data = requests.get(url, timeout=20).json()
    eq = [d for d in data if d['exch_seg']=='NSE' and d['symbol'].endswith('-EQ')][:500]

    matches=[]
    to_date = datetime.now()
    from_date = to_date - timedelta(days=25)

    for d in eq:
        try:
            params={"exchange":"NSE","symboltoken":d['token'],"interval":"ONE_DAY","fromdate":from_date.strftime("%Y-%m-%d %H:%M"),"todate":to_date.strftime("%Y-%m-%d %H:%M")}
            candles = obj.getCandleData(params).get('data',[])
            if len(candles) < 21: continue
            last20 = candles[-21:-1]
            today = candles[-1]
            high20 = max(c[2] for c in last20)
            close_t = today[4]
            low_t = today[3]
            risk = today[2]-today[3]
            if close_t > high20*0.998 and risk>0:
                target = close_t + risk*REWARD_RATIO
                matches.append(f"{d['symbol'].replace('-EQ','')} C:{close_t} T:{round(target,1)}")
        except: continue

    now = datetime.now().strftime('%d-%m %H:%M')
    if not matches:
        msg = f"📊 *NSE 500 Scan (1:{REWARD_RATIO})*\n⏰ {now}\n❌ 0 Match Found - आज Breakout नाही"
    else:
        msg = f"🚀 *Breakout 1:{REWARD_RATIO} - {len(matches)} Found*\n⏰ {now}\n\n" + "\n".join(matches[:15])

    print(msg)
    send_telegram(msg)

except Exception as e:
    print(traceback.format_exc())
    send_telegram(f"Error: {e}")
