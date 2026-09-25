import os, time, pyotp, requests, traceback
from SmartApi import SmartConnect
from datetime import datetime, timedelta

# --- CONFIG ---
REWARD_RATIO = 2.5
CANDLE_DAYS = 30

def get_clean_totp():
    secret = os.getenv("ANGEL_TOTP_SECRET", "") or os.getenv("ANGEL_TOTP", "")
    clean = secret.replace(" ", "").replace("\n", "").replace("\r", "").strip()
    print(f"TOTP len after clean: {len(clean)}")
    return clean

def send_telegram(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        r = requests.post(url, data=payload, timeout=15)
        print(f"Telegram: {r.text[:200]}")
    except Exception as e:
        print(f"Telegram Failed: {e}")

def get_historical_data(smart_api, symbol_token):
    try:
        to_date = datetime.now()
        from_date = to_date - timedelta(days=CANDLE_DAYS)
        params = {
            "exchange": "NSE",
            "symboltoken": symbol_token,
            "interval": "ONE_DAY",
            "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
            "todate": to_date.strftime("%Y-%m-%d %H:%M")
        }
        for i in range(3):
            try:
                data = smart_api.getCandleData(params)
                if data and data.get('status'):
                    return data.get('data', [])
                time.sleep(0.5)
            except:
                time.sleep(1)
        return []
    except:
        return []

def load_nse_tokens_from_api():
    try:
        url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        r = requests.get(url, timeout=20)
        data = r.json()
        eq = [d for d in data if d.get('exch_seg')=='NSE' and d.get('symbol','').endswith('-EQ')]
        eq_sorted = sorted(eq, key=lambda x: x['name'])[:1000]
        result = [{"symbol": d['symbol'], "token": d['token']} for d in eq_sorted]
        print(f"Loaded {len(result)} tokens")
        return result
    except Exception as e:
        print(f"Master load fail: {e}")
        return [{"symbol": "RELIANCE-EQ", "token": "2885"}]

try:
    api_key = os.getenv("ANGEL_API_KEY")
    client_id = os.getenv("ANGEL_CLIENT_ID")
    password = os.getenv("ANGEL_PASSWORD")
    clean_secret = get_clean_totp()
    totp = pyotp.TOTP(clean_secret).now()

    obj = SmartConnect(api_key=api_key)
    session = obj.generateSession(client_id, password, totp)
    print(f"Login: {session.get('status')}")

    symbols = load_nse_tokens_from_api()
    matches = []
    scanned = 0

    for item in symbols:
        try:
            candles = get_historical_data(obj, item['token'])
            if not candles or len(candles) < 22:
                continue
            last_20 = candles[-21:-1]
            today = candles[-1]
            high_20 = max([c[2] for c in last_20])
            open_t, high_t, low_t, close_t = today[1], today[2], today[3], today[4]
            risk = high_t - low_t
            if risk <= 0: continue

            # 1:2.5 Breakout Logic
            if close_t > high_20 * 0.998:
                target = close_t + (risk * REWARD_RATIO)
                matches.append(f"{item['symbol'].replace('-EQ','')} | L:{low_t} C:{close_t} T:{round(target,1)}")
            scanned += 1
            if scanned % 100 == 0:
                print(f"Scanned {scanned}")
                time.sleep(0.5)
        except:
            continue

    now = datetime.now().strftime('%d-%m %H:%M')
    if len(matches) == 0:
        msg = f"📊 *NSE 1000 Scan Done (1:{REWARD_RATIO})*\n\n⏰ Time: {now}\n❌ *0 Match Found*\n{scanned} Stocks स्कॅन झाले. आज 1:2.5 Breakout नाही."
    else:
        top_10 = "\n".join(matches[:10])
        msg = f"🚀 *NSE Breakout 1:{REWARD_RATIO} - {len(matches)} Found*\n\n⏰ {now}\n\n{top_10}"
        if len(matches) > 10:
            msg += f"\n\n+ {len(matches)-10} more..."

    print(msg)
    send_telegram(msg)

except Exception as e:
    print(traceback.format_exc())
    send_telegram(f"⚠️ Scanner Error: {e}")
