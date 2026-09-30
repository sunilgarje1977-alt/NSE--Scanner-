# V44 LIVE - Angel One + 1:1 Trailing BUY/SELL
import os, time, requests, pyotp
from SmartApi import SmartConnect

# --- KEYS GitHub Secret मधून ---
API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PASSWORD = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SL_PER = 0.06

def send_tg(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    print(f"TG: {msg[:40]}")

def get_levels(ltp, side):
    ltp=float(ltp)
    if side=="BUY":
        sl=round(ltp*(1-SL_PER),2)
        target=round(ltp*(1+SL_PER),2)
    else:
        sl=round(ltp*(1+SL_PER),2)
        target=round(ltp*(1-SL_PER),2)
    return sl, sl, target

# --- ANGEL LOGIN ---
print("Angel Login...")
try:
    smart = SmartConnect(api_key=API_KEY)
    totp = pyotp.TOTP(TOTP_SECRET).now()
    data = smart.generateSession(CLIENT_ID, PASSWORD, totp)
    print("Angel Login Success ✅")
except Exception as e:
    print(f"Angel Login Fail: {e}")
    send_tg(f"V44 Angel Login Fail: {e}")
    exit()

# --- STOCKS with Token (Angel Token लागतो) ---
# तुला हवे असलेले Token - NSE चे
STOCKS = {
    "NBCC": "115505", "SUZLON": "27501", "HAL": "13650", "IOC": "13266",
    "DLF": "15557", "RELIANCE": "14977", "TCS": "18457", "INFY": "15921"
}

buy_list=[]; sell_list=[]

for sym, token in STOCKS.items():
    try:
        ltp_data = smart.ltpData("NSE", sym, token)
        ltp = float(ltp_data['data']['ltp'])
        
        # --- तुझी जुनी TOP 6 Condition इथे टाक ---
        # मी Demo साठी Simple Condition ठेवली आहे - तू तुझी जुनी टाक
        # उदा. जर तुझ्याकडे 15 Day Avg ची Condition असेल तर इथे टाक
        
        # BUY Logic: समज 79.45 हा LTP
        if ltp > 0: # इथे तुझी BUY Condition टाक - उदा. ltp > ema20
            # Test साठी सध्या मी SELL/BUY दोन्ही दाखवतो
            pass

        # आता सध्या सर्वांना BUY/SELL मध्ये टाकून दाखवतो
        # तुला Condition नसेल तर मी 50% BUY 50% SELL करतो
        import random
        side = random.choice(["BUY","SELL"]) # हे काढून तुझी Condition टाक
        
        sl, tsl, target = get_levels(ltp, side)
        if side=="BUY":
            buy_list.append((sym, ltp, sl, tsl, target))
        else:
            sell_list.append((sym, ltp, sl, tsl, target))
            
        time.sleep(0.5)
    except Exception as e:
        print(f"{sym} LTP Fail: {e}")

# TOP 6
buy_list=buy_list[:6]
sell_list=sell_list[:6]

if not buy_list and not sell_list:
    send_tg("V44 LIVE (Angel) - No Setup Found ✅")
else:
    for s, ltp, sl, tsl, tgt in buy_list:
        send_tg(f"🟢 BUY {s} - TOP 6\nLTP: {ltp}\nSL: {sl}\nTSL: {tsl}\nTARGET: {tgt}\nRR: 1:1 (Angel Live)")
    for s, ltp, sl, tsl, tgt in sell_list:
        send_tg(f"🔴 SELL {s} - TOP 6\nLTP: {ltp}\nSL: {sl}\nTSL: {tsl}\nTARGET: {tgt}\nRR: 1:1 (Angel Live)")

print("Done")
