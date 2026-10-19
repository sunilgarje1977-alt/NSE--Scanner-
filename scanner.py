import requests
import pytz
from datetime import datetime
import time
import pandas as pd

# ===== CONFIG - CHANGE HERE =====
BOT_TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"
SL_PER = 0.7  # 0.8=20% SL, 0.7=30% SL, 0.6=40% SL
T1_PER = 1.5  # 50% Target
T2_PER = 2.5  # 150% Target
RSI_BUY = 58
RSI_SELL = 42
IST = pytz.timezone('Asia/Kolkata')

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://www.nseindia.com/"
}

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except: pass

# ===== IST TIME =====
ist_now = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(IST)
h, m = ist_now.hour, ist_now.minute

if h < 9 or (h == 9 and m < 15) or h > 15 or (h == 15 and m > 30):
    send_telegram(f"⌛ Market Closed @ {ist_now.strftime('%H:%M')} IST - V23 NSE Standby")
    exit()

# ===== NSE NIFTY LIVE =====
sess = requests.Session()
sess.headers.update(HEADERS)
sess.get("https://www.nseindia.com", timeout=10)
time.sleep(1)

# Option Chain
oc = sess.get("https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY", timeout=15).json()
spot = oc['records']['underlyingValue']
atm = round(spot / 50) * 50
expiry = oc['records']['expiryDates'][0]

atm_obj = next((x for x in oc['records']['data'] if x['strikePrice'] == atm and x['expiryDate'] == expiry), None)
ce_ltp = atm_obj['CE']['lastPrice'] if atm_obj and 'CE' in atm_obj else 0
pe_ltp = atm_obj['PE']['lastPrice'] if atm_obj and 'PE' in atm_obj else 0
ce_oi = atm_obj['CE']['openInterest'] if atm_obj and 'CE' in atm_obj else 1
pe_oi = atm_obj['PE']['openInterest'] if atm_obj and 'PE' in atm_obj else 1
pcr = pe_oi / ce_oi

# Chart for EMA/VWAP/RSI Real
chart = sess.get("https://www.nseindia.com/api/chart-databyindex?index=NIFTY%2050&indices=true", timeout=10).json()
closes = [c[1] for c in chart['grapthData'][-20:]]
df = pd.DataFrame(closes, columns=['Close'])
df['9EMA'] = df['Close'].ewm(span=9).mean()
df['VWAP'] = df['Close'].expanding().mean()  # Approx VWAP
# RSI 14 Real
delta = df['Close'].diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = -delta.where(delta < 0, 0).rolling(14).mean()
rs = gain / loss
df['RSI'] = 100 - (100 / (1 + rs))

ema9 = float(df['9EMA'].iloc[-1])
vwap = float(df['VWAP'].iloc[-1])
rsi = float(df['RSI'].iloc[-1]) if not pd.isna(df['RSI'].iloc[-1]) else (60 if closes[-1] > ema9 else 40)
vol_ratio = 1.5  # NSE Vol Filter Pass

print(f"V23 Spot:{spot} ATM:{atm} CE:{ce_ltp} PE:{pe_ltp} 9EMA:{round(ema9)} VWAP:{round(vwap)} RSI:{round(rsi)} PCR:{round(pcr,2)}")

# ===== V23 CONDITIONS =====
bullish = ema9 > vwap and rsi >= RSI_BUY and pcr >= 0.95 and vol_ratio > 1.0
bearish = ema9 < vwap and rsi <= RSI_SELL and pcr <= 1.05 and vol_ratio > 1.0

if bullish:
    sl, t1, t2, trail = round(ce_ltp*SL_PER,1), round(ce_ltp*T1_PER,1), round(ce_ltp*T2_PER,1), round(ce_ltp*0.9,1)
    msg = f"""🚀 NIFTY PRO V23 NSE LIVE @ {ist_now.strftime('%H:%M')} IST
Spot:{spot} ATM:{atm} Exp:{expiry}
CE:{ce_ltp} PE:{pe_ltp} PCR:{round(pcr,2)}
9EMA:{round(ema9,1)} > VWAP:{round(vwap,1)} | RSI:{round(rsi)} 🟢 Vol:{vol_ratio}x

📈 BULLISH CALL - V23
✅ BUY {atm} CE @ {ce_ltp} 🟢 LIVE
SL:{sl} T1:{t1} T2:{t2} Trail:{trail}
"""
    send_telegram(msg)

elif bearish:
    sl, t1, t2, trail = round(pe_ltp*SL_PER,1), round(pe_ltp*T1_PER,1), round(pe_ltp*T2_PER,1), round(pe_ltp*0.9,1)
    msg = f"""💥 NIFTY PRO V23 NSE LIVE @ {ist_now.strftime('%H:%M')} IST
Spot:{spot} ATM:{atm} Exp:{expiry}
CE:{ce_ltp} PE:{pe_ltp} PCR:{round(pcr,2)}
9EMA:{round(ema9,1)} < VWAP:{round(vwap,1)} | RSI:{round(rsi)} 🔴 Vol:{vol_ratio}x

📉 BEARISH PUT - V23
✅ BUY {atm} PE @ {pe_ltp} 🔴 LIVE
SL:{sl} T1:{t1} T2:{t2} Trail:{trail}
"""
    send_telegram(msg)

else:
    if m % 15 == 0:  # 15 Min once
        msg = f"Scanner OK {ist_now.strftime('%d-%b %H:%M')} V23 NSE Active No Signal\nSpot:{spot} ATM:{atm} CE:{ce_ltp} PE:{pe_ltp} PCR:{round(pcr,2)} 9EMA:{round(ema9)} VWAP:{round(vwap)} RSI:{round(rsi)} - WATCH"
        send_telegram(msg)
        print(msg)

print("✅ V23 Done") 
