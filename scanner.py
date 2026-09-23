import os, pyotp, requests, time, json
from SmartApi import SmartConnect
from datetime import datetime, timedelta

API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PASSWORD = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# NSE 1000 साठी Instrument Master Load करू
def load_master():
    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    data = requests.get(url).json()
    # फक्त NSE EQ
    nse_eq = [s for s in data if s['exch_seg']=='NSE' and s['symbol'].endswith('-EQ')]
    return nse_eq[:1000] # पहिले 1000

def scan():
    print("Angel Login...")
    totp = pyotp.TOTP(TOTP_SECRET).now()
    obj = SmartConnect(api_key=API_KEY)
    obj.generateSession(CLIENT_ID, PASSWORD, totp)

    stocks = load_master()
    print(f"Loaded {len(stocks)} stocks")

    breakout = []
    for s in stocks:
        try:
            symbol = s['symbol']
            token = s['token']
            # मागच्या 2 दिवसाची candle
            historicParam={
                "exchange": "NSE",
                "symboltoken": token,
                "interval": "ONE_DAY",
                "fromdate": (datetime.now()-timedelta(days=5)).strftime("%Y-%m-%d %H:%M"),
                "todate": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            candles = obj.getCandleData(historicParam)
            if candles and candles['data']:
                data = candles['data']
                if len(data)>=2:
                    last_close = data[-1][4]
                    prev_high = data[-2][2]
                    if last_close > prev_high: # Breakout Logic
                        breakout.append(f"{symbol} - {last_close} (Breakout!)")
        except:
            continue
        time.sleep(0.05)
        if len(breakout)>=20: # Telegram ला 20 पाठवू
            break

    if not breakout:
        msg = "NSE 1000 Scanner (Angel): आज Breakout नाही, 1000 Stocks स्कॅन झाले!"
    else:
        msg = "🚀 NSE 1000 Breakout Scanner (Angel):\n\n" + "\n".join(breakout)

    # Telegram
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    print("Sent!")

if __name__ == "__main__":
    scan()
