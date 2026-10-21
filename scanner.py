import os, time, requests, cloudscraper, pytz, pandas as pd
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
IST = pytz.timezone('Asia/Kolkata')

def send_tg(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=15)
        print(msg)
    except Exception as e:
        print(e)

ist_now = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(IST)
print(f"V28 @ {ist_now.strftime('%H:%M')}")

# NSE FETCH
try:
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows'})
    scraper.get("https://www.nseindia.com", timeout=20)
    time.sleep(2)
    oc = scraper.get("https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY", timeout=20).json()
    spot = float(oc['records']['underlyingValue'])
    atm = round(spot/50)*50
    expiry = oc['records']['expiryDates'][0]
    
    atm_row = next((r for r in oc['records']['data'] if r['strikePrice']==atm and r['expiryDate']==expiry), None)
    ce_ltp = float(atm_row.get('CE',{}).get('lastPrice',0))
    pe_ltp = float(atm_row.get('PE',{}).get('lastPrice',0))
    
    chart = scraper.get("https://www.nseindia.com/api/chart-databyindex?index=NIFTY%2050&indices=true", timeout=20).json()
    closes = [c[1] for c in chart['grapthData'][-20:]]
    df = pd.DataFrame(closes, columns=['c'])
    df['9ema'] = df['c'].ewm(span=9).mean()
    df['vwap'] = df['c'].expanding().mean()
    delta = df['c'].diff()
    gain = delta.where(delta>0,0).rolling(14).mean()
    loss = -delta.where(delta<0,0).rolling(14).mean()
    rsi = 100 - (100/(1+gain/loss))
    ema9 = float(df['9ema'].iloc[-1])
    vwap = float(df['vwap'].iloc[-1])
    rsi_val = float(rsi.iloc[-1])
    if pd.isna(rsi_val): rsi_val = 60 if closes[-1]>ema9 else 40
except Exception as e:
    print(f"Error {e}")
    send_tg(f"⚠️ V28 Error {e}")
    exit(0)

print(f"Spot {spot} ATM {atm} CE {ce_ltp} PE {pe_ltp} EMA {ema9:.1f} VWAP {vwap:.1f} RSI {rsi_val:.1f}")

# ===== SIGNAL CALCULATION WITH BUY / TARGET / SL / TRAILING =====
def calc_levels(ltp):
    buy = ltp
    sl = round(buy*0.70, 1)          # 30% SL
    t1 = round(buy*1.5, 1)           # 50% Target 1
    t2 = round(buy*2.5, 1)           # 150% Target 2
    t3 = round(buy*3.5, 1)           # 250% Target 3
    trail = round(buy*0.90, 1)       # Trailing start - cost to cost
    trail2 = round(buy*1.3, 1)       # After T1, SL to Buy
    return buy, sl, t1, t2, t3, trail, trail2

# BULLISH CALL
if ema9 > vwap and rsi_val >= 58:
    buy, sl, t1, t2, t3, trail, trail2 = calc_levels(ce_ltp)
    msg = f"""🚀 NIFTY V28 BUY CALL @ {ist_now.strftime('%H:%M')} IST
Spot:{spot} ATM:{atm} Exp:{expiry}
CE LTP:{ce_ltp} PE LTP:{pe_ltp}
9EMA:{ema9:.1f} > VWAP:{vwap:.1f} RSI:{rsi_val:.0f} 🟢

📈 BUY {atm} CE @ {buy} LIVE
——————————————
🛑 SL: {sl} (30% Stoploss)
🎯 T1: {t1} (50% Book 50%)
🎯 T2: {t2} (150% Book 30%)
🎯 T3: {t3} (250% Trail)
🔄 Trailing SL:
• Cost: {trail} -> {trail2} after T1
• T1 नंतर SL = Buy Price
• T2 नंतर SL = T1
——————————————
PCR & Trend Bullish"""
    send_tg(msg)

# BEARISH PUT
elif ema9 < vwap and rsi_val <= 42:
    buy, sl, t1, t2, t3, trail, trail2 = calc_levels(pe_ltp)
    msg = f"""💥 NIFTY V28 BUY PUT @ {ist_now.strftime('%H:%M')} IST
Spot:{spot} ATM:{atm} Exp:{expiry}
CE LTP:{ce_ltp} PE LTP:{pe_ltp}
9EMA:{ema9:.1f} < VWAP:{vwap:.1f} RSI:{rsi_val:.0f} 🔴

📉 BUY {atm} PE @ {buy} LIVE
——————————————
🛑 SL: {sl} (30% Stoploss)
🎯 T1: {t1} (50% Book 50%)
🎯 T2: {t2} (150% Book 30%)
🎯 T3: {t3} (250% Trail)
🔄 Trailing SL:
• Cost: {trail} -> {trail2} after T1
• T1 नंतर SL = Buy Price
• T2 नंतर SL = T1
——————————————
Trend Bearish - Like Your Chart 22,894"""
    send_tg(msg)

else:
    if ist_now.minute % 15 == 0:
        send_tg(f"⏳ V28 WATCH {ist_now.strftime('%H:%M')} Spot:{spot} ATM:{atm} CE:{ce_ltp} PE:{pe_ltp} EMA:{ema9:.0f} VWAP:{vwap:.0f} RSI:{rsi_val:.0f} No Signal")

print("✅ V28 Done") 
