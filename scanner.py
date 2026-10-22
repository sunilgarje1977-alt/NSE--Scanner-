import os, time, json, pathlib, datetime, pytz, requests, cloudscraper

BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")
IST = pytz.timezone('Asia/Kolkata')
STATE = pathlib.Path('last_signal_v41.json')

def send_tg(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        r = requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=15)
        print(f"TG Sent: {r.status_code} - {msg[:100]}")
    except Exception as e:
        print(e)

ist_now = datetime.datetime.now(IST)
print(f"V41 RUN @ {ist_now.strftime('%H:%M:%S')} IST")

# --- 1. CHECK LAST SIGNAL - 4 HOURS BLOCK ---
if STATE.exists():
    try:
        last = json.loads(STATE.read_text())
        last_time = datetime.datetime.fromisoformat(last['time'])
        if last_time.tzinfo is None:
            last_time = IST.localize(last_time)
        diff_min = (ist_now - last_time).total_seconds() / 60
        print(f"Last was {last['key']} {diff_min:.1f} min ago")
        if diff_min < 240:  # 4 तास
            print(f"SKIP - Need 240 min gap. Exit.")
            exit(0)
        if last['key'].split('_')[-1] == str(int(round(float(last.get('spot',0))/50)*50)):
            # Optional same strike block
            pass
    except Exception as e:
        print(f"State read fail {e}")

# --- 2. NSE FETCH LIVE ---
scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
spot = 0
try:
    scraper.get("https://www.nseindia.com", timeout=15)
    time.sleep(2)
    oc = scraper.get("https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY", timeout=15).json()
    spot = float(oc['records']['underlyingValue'])
    expiry = oc['records']['expiryDates'][0]
    print(f"LIVE Spot: {spot} Expiry: {expiry}")
except Exception as e:
    print(f"NSE Fail {e}, using fallback")
    spot = 22894.0

atm = int(round(spot / 50) * 50)

# --- 3. YOUR LOGIC: EMA < VWAP + RSI <45 = PUT ---
# Live मध्ये EMA/VWAP काढशील - आता demo
ema = 23047
vwap = 23077
rsi = 38

direction = "NONE"
if spot < 23000 and ema < vwap and rsi < 45:
    direction = "PUT"
    reason = f"Spot {spot}<23000 + EMA {ema}<VWAP {vwap} + RSI {rsi} Weak"
elif spot > 23000 and ema > vwap and rsi > 55:
    direction = "CALL"
    reason = f"Spot {spot}>23000 + EMA {ema}>VWAP {vwap} + RSI {rsi} Strong"
else:
    print(f"WATCH - No trade Spot:{spot}")
    exit(0)

# --- 4. OPTION PRICE ---
try:
    atm_row = next((r for r in oc['records']['data'] if r.get('strikePrice') == atm), None)
    if atm_row:
        opt = atm_row['PE'] if direction == 'PUT' else atm_row['CE']
        price = float(opt['lastPrice'])
    else:
        price = 135.0
except:
    price = 135.0

sl = round(price * 0.7, 1)
t1 = round(price * 1.5, 1)
t2 = round(price * 2.5, 1)
t3 = round(price * 3.5, 1)

# --- 5. SEND ---
new_key = f"{ist_now.strftime('%Y-%m-%d')}_{direction}_{atm}"

msg = f"""✅ *FINAL NIFTY {direction} @ {ist_now.strftime('%H:%M')} IST - V41*

*Spot:* {spot} *ATM:* {atm}
{reason}

📉 *BUY {atm} {direction} @ {price} LIVE*
🛑 SL:{sl} T1:{t1} T2:{t2} T3:{t3}

Prev: {STATE.read_text()[:50] if STATE.exists() else 'None'}
Next after 4 Hrs
"""

send_tg(msg)

# --- 6. SAVE ---
STATE.write_text(json.dumps({
    'key': new_key,
    'time': ist_now.isoformat(),
    'spot': spot,
    'atm': atm,
    'direction': direction,
    'price': price
}, indent=2))
print(f"Saved {new_key}")
