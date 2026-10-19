import requests
import pytz
from datetime import datetime
import time
import json

# ===== CONFIG =====
BOT_TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"
IST = pytz.timezone('Asia/Kolkata')

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/"
}

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except Exception as e:
        print(f"TG Error {e}")

# ===== IST TIME CHECK =====
utc_now = datetime.utcnow().replace(tzinfo=pytz.utc)
ist_now = utc_now.astimezone(IST)
hour = ist_now.hour
minute = ist_now.minute

print(f"V22 NSE Check @ {ist_now.strftime('%H:%M:%S')} IST")

if hour < 9 or (hour == 9 and minute < 15) or hour > 15 or (hour == 15 and minute > 30):
    msg = f"⌛ Market Closed @ {ist_now.strftime('%H:%M')} IST - V22 NSE Scanner Standby"
    print(msg)
    send_telegram(msg)
    exit()

# ===== DIRECT NSE DATA =====
session = requests.Session()
session.headers.update(HEADERS)

try:
    # 1. First hit main page to get cookies
    session.get("https://www.nseindia.com", timeout=10)
    time.sleep(1)
    
    # 2. Get NIFTY Spot + Option Chain
    url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
    res = session.get(url, timeout=15)
    data = res.json()
    
    spot = data['records']['underlyingValue']
    atm = round(spot / 50) * 50
    expiry = data['records']['expiryDates'][0]  # Nearest Expiry
    
    # Find ATM Option Data
    atm_data = None
    for item in data['records']['data']:
        if item['strikePrice'] == atm and item['expiryDate'] == expiry:
            atm_data = item
            break
    
    if not atm_data:
        raise Exception("ATM Data Not Found")
    
    ce_data = atm_data.get('CE', {})
    pe_data = atm_data.get('PE', {})
    
    ce_ltp = ce_data.get('lastPrice', 0)
    pe_ltp = pe_data.get('lastPrice', 0)
    ce_oi = ce_data.get('openInterest', 0)
    pe_oi = pe_data.get('openInterest', 0)
    
    # PCR for Direction
    pcr = pe_oi / ce_oi if ce_oi > 0 else 1
    change = data['records']['data'][0].get('CE',{}).get('underlyingValue', spot) - spot
    
    # Simple EMA/VWAP Logic using NSE Intraday (approx)
    # NSE gives us true LTP - we use PCR + LTP Change for Signal
    
    bullish = pcr > 1.1 and ce_ltp > 0  # More PUT OI = Bullish
    bearish = pcr < 0.9 and pe_ltp > 0  # More CALL OI = Bearish
    
    # For better: use NSE Chart API for 9EMA
    chart_url = f"https://www.nseindia.com/api/chart-databyindex?index=NIFTY%2050&indices=true"
    chart_res = session.get(chart_url, timeout=10).json()
    
    # Last 10 candles for 9EMA approx
    candles = chart_res['grapthData'][-15:]  # NSE gives [timestamp, value]
    closes = [c[1] for c in candles]
    ema9 = sum(closes[-9:]) / 9
    vwap = sum(closes) / len(closes)
    spot_live = closes[-1]
    
    # Vol & RSI Approx from NSE
    rsi = 60 if spot_live > ema9 else 40
    
except Exception as e:
    send_telegram(f"⚠️ V22 NSE Error: {e}")
    print(f"NSE Error {e}")
    exit()

# ===== V22 SIGNAL - NSE LIVE PREMIUM =====
print(f"NSE Spot:{spot} ATM:{atm} CE:{ce_ltp} PE:{pe_ltp} PCR:{round(pcr,2)} EMA9:{round(ema9)} VWAP:{round(vwap)}")

if ema9 > vwap and rsi >= 58:  # BULLISH
    sl = round(ce_ltp * 0.7, 1)
    t1 = round(ce_ltp * 1.5, 1)
    t2 = round(ce_ltp * 2.5, 1)
    trail = round(ce_ltp * 0.9, 1)
    msg = f"""🚀 NIFTY PRO V22 NSE LIVE @ {ist_now.strftime('%H:%M')} IST
Spot:{spot} ATM:{atm} | CE LTP:{ce_ltp} PE LTP:{pe_ltp}
9EMA:{round(ema9)} x VWAP:{round(vwap)} | PCR:{round(pcr,2)} | RSI:{rsi}

📈 BULLISH CALL - NSE DATA
✅ BUY {atm} CE @ {ce_ltp} 🟢 LIVE {expiry}
SL:{sl} T1:{t1} T2:{t2} Trail:{trail}
OI CE:{ce_oi} PE:{pe_oi}"""
    send_telegram(msg)

elif ema9 < vwap and rsi <= 42:  # BEARISH
    sl = round(pe_ltp * 0.7, 1)
    t1 = round(pe_ltp * 1.5, 1)
    t2 = round(pe_ltp * 2.5, 1)
    trail = round(pe_ltp * 0.9, 1)
    msg = f"""💥 NIFTY PRO V22 NSE LIVE @ {ist_now.strftime('%H:%M')} IST
Spot:{spot} ATM:{atm} | CE LTP:{ce_ltp} PE LTP:{pe_ltp}
9EMA:{round(ema9)} x VWAP:{round(vwap)} | PCR:{round(pcr,2)} | RSI:{rsi}

📉 BEARISH PUT - NSE DATA
✅ BUY {atm} PE @ {pe_ltp} 🔴 LIVE {expiry}
SL:{sl} T1:{t1} T2:{t2} Trail:{trail}
OI CE:{ce_oi} PE:{pe_oi}"""
    send_telegram(msg)

else:
    msg = f"Scanner OK {ist_now.strftime('%d-%b %H:%M')} NSE LIVE Active No Signal\nSpot:{spot} ATM:{atm} CE:{ce_ltp} PE:{pe_ltp} PCR:{round(pcr,2)} 9EMA:{round(ema9)} VWAP:{round(vwap)} - WATCH Near Cross"
    print(msg)
    if minute % 10 == 0:  # 10 Min la ekda
        send_telegram(msg)

print("✅ V22 NSE Done") 
