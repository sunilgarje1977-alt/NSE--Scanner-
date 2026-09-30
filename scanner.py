import os, requests, pyotp, time
from SmartApi import SmartConnect
from datetime import datetime

API_KEY = os.getenv("ANGEL_API_KEY","").strip()
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID","").strip()
PASSWORD = os.getenv("ANGEL_PASSWORD","").strip()
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET","").strip()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN","").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID","").strip()

def send_tg(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        r = requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=15)
        print(f"TG Status: {r.status_code} | {r.text[:300]}")
    except Exception as e:
        print(f"TG Error: {e}")

def calc_rsi(closes, period=14):
    if len(closes) < period+1: return 50
    g=l=0
    for i in range(1, period+1):
        diff = closes[-i] - closes[-i-1]
        if diff>0: g+=diff
        else: l-=diff
    if l==0: return 70
    return 100 - (100/(1+g/l))

print("=== V48 START ===")
print("Login...")
smart = SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PASSWORD, pyotp.TOTP(TOTP_SECRET).now())
print("Login OK")

today = datetime.now()
# Sunday Test
if today.weekday() >= 5:
    send_tg(f"✅ V48 Bot Working!\nDate: {today.strftime('%d-%b %A')}\nMarket Closed Today.\nToken Error Fixed!\nLogin OK!\nMonday पासून BUY/SELL Signal चालू होतील!")
    print("Sunday - Test msg sent")
    exit()

STOCKS = ["UNIONBANK", "PFC", "RECLTD", "NBCC", "SUZLON"]
found = False

for sym in STOCKS:
    try:
        time.sleep(1)
        print(f"\nSearching {sym}...")
        search = smart.searchScrip("NSE", sym)
        if not search.get('data'):
            print(f"{sym} Not Found")
            continue

        # पहिलाच result घे
        token = search['data'][0]['symboltoken']
        tradingsym = search['data'][0]['tradingsymbol']
        print(f"{sym} -> Token: {token} Symbol: {tradingsym}")

        ltp_data = smart.ltpData("NSE", tradingsym, token)
        ltp = float(ltp_data['data']['ltp'])
        print(f"{sym} LTP: {ltp}")

        # 15M Candle
        start = today.replace(hour=9, minute=15, second=0, microsecond=0)
        params = {
            "exchange": "NSE",
            "symboltoken": token,
            "interval": "FIFTEEN_MINUTE",
            "fromdate": start.strftime("%Y-%m-%d %H:%M"),
            "todate": today.strftime("%Y-%m-%d %H:%M")
        }
        candles = smart.getCandleData(params)
        data = candles.get('data', [])
        if len(data) < 10:
            print(f"{sym} No Candle")
            continue

        closes = [float(c[4]) for c in data]
        rsi = calc_rsi(closes)
        prev_high = float(data[-2][2])
        prev_low = float(data[-2][3])
        print(f"{sym} RSI:{rsi:.1f} PH:{prev_high} PL:{prev_low}")

        if ltp > prev_high and rsi > 60:
            sl = prev_low
            tgt = ltp + (ltp - sl)*1.5
            send_tg(f"🔥 BUY {sym}\nLTP:{ltp:.2f} RSI:{rsi:.1f}\nBreakout:{prev_high:.2f}\nSL:{sl:.2f}\nTGT:{tgt:.2f}")
            found = True
        elif ltp < prev_low and rsi < 50:
            sl = prev_high
            tgt = ltp - (sl - ltp)*1.5
            send_tg(f"🔻 SELL {sym}\nLTP:{ltp:.2f} RSI:{rsi:.1f}\nBreakdown:{prev_low:.2f}\nSL:{sl:.2f}\nTGT:{tgt:.2f}")
            found = True

    except Exception as e:
        print(f"{sym} Error: {e}")

if not found:
    send_tg("V48 Live ✅ No Signal Now\nRSI Filter: BUY>60 SELL<50\nScanned: UNIONBANK, PFC, RECLTD, NBCC, SUZLON")

print("=== V48 DONE ===")
