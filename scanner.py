import os, time, requests, cloudscraper, pytz, pandas as pd
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
IST = pytz.timezone('Asia/Kolkata')

def send_tg(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        print(msg)
    except Exception as e:
        print(f"TG Error: {e}")

# IST TIME
ist_now = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(IST)
h, m = ist_now.hour, ist_now.minute
print(f"V25 Check @ {ist_now.strftime('%H:%M:%S')} IST")

if h < 9 or (h == 9 and m < 15) or h > 15 or (h == 15 and m > 30):
    send_tg(f"⌛ Market Closed @ {ist_now.strftime('%H:%M')} IST - V25 Standby")
    exit(0)

# NSE DATA - CLOUDSCRAPER BYPASS
try:
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows'})
    scraper.get("https://www.nseindia.com", timeout=20)
    time.sleep(2)
    oc = scraper.get("https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY", timeout=20).json()
    
    spot = float(oc['records']['underlyingValue'])
    atm = round(spot / 50) * 50
    expiry = oc['records']['expiryDates'][0]
    
    atm_data = None
    for row in oc['records']['data']:
        if row['strikePrice'] == atm and row['expiryDate'] == expiry:
            atm_data = row
            break
    
    if not atm_data:
        raise Exception(f"ATM {atm} Not Found")
    
    ce = atm_data.get('CE', {})
    pe = atm_data.get('PE', {})
    ce_ltp = float(ce.get('lastPrice', 0))
    pe_ltp = float(pe.get('lastPrice', 0))
    
    # CHART EMA/VWAP/RSI
    chart = scraper.get("https://www.nseindia.com/api/chart-databyindex?index=NIFTY%2050&indices=true", timeout=20).json()
    closes = [c[1] for c in chart['grapthData'][-20:]]
    df = pd.DataFrame(closes, columns=['c'])
    df['ema9'] = df['c'].ewm(span=9).mean()
    df['vwap'] = df['c'].expanding().mean()
    delta = df['c'].diff()
    gain = delta.where(delta>0,0).rolling(14).mean()
    loss = -delta.where(delta<0,0).rolling(14).mean()
    rs = gain/loss
    df['rsi'] = 100 - (100/(1+rs))
    
    ema9 = float(df['ema9'].iloc[-1])
    vwap = float(df['vwap'].iloc[-1])
    rsi = float(df['rsi'].iloc[-1])
    if pd.isna(rsi): rsi = 60 if closes[-1]>ema9 else 40

except Exception as e:
    print(f"ERROR: {e}")
    send_tg(f"⚠️ V25 Error @ {ist_now.strftime('%H:%M')} : {e}")
    exit(0)

# SIGNAL LOGIC - CALL PUT BOTH
print(f"Spot:{spot} ATM:{atm} CE:{ce_ltp} PE:{pe_ltp} EMA:{round(ema9,1)} VWAP:{round(vwap,1)} RSI:{round(rsi)}")

if ema9 > vwap and rsi >= 58:
    sl, t1, t2 = round(ce_ltp*0.7,1), round(ce_ltp*1.5,1), round(ce_ltp*2.5,1)
    msg = f"🚀 V25 NSE LIVE @ {ist_now.strftime('%H:%M')} IST\nSpot:{spot} ATM:{atm} Exp:{expiry}\nCE:{ce_ltp} PE:{pe_ltp}\n9EMA:{round(ema9,1)}>VWAP:{round(vwap,1)} RSI:{round(rsi)} 🟢\n------------------------\n📈 BULLISH CALL\n✅ BUY {atm} CE @ {ce_ltp}\nSL:{sl} T1:{t1} T2:{t2}"
    send_tg(msg)

elif ema9 < vwap and rsi <= 42:
    sl, t1, t2 = round(pe_ltp*0.7,1), round(pe_ltp*1.5,1), round(pe_ltp*2.5,1)
    msg = f"💥 V25 NSE LIVE @ {ist_now.strftime('%H:%M')} IST\nSpot:{spot} ATM:{atm} Exp:{expiry}\nCE:{ce_ltp} PE:{pe_ltp}\n9EMA:{round(ema9,1)}<VWAP:{round(vwap,1)} RSI:{round(rsi)} 🔴\n------------------------\n📉 BEARISH PUT\n✅ BUY {atm} PE @ {pe_ltp}\nSL:{sl} T1:{t1} T2:{t2}"
    send_tg(msg)

else:
    if m % 15 == 0:
        msg = f"Scanner OK {ist_now.strftime('%d-%b %H:%M')} V25 NSE Active No Signal\nSpot:{spot} ATM:{atm} CE:{ce_ltp} PE:{pe_ltp} EMA:{round(ema9)} VWAP:{round(vwap)} RSI:{round(rsi)}"
        send_tg(msg)

print("✅ V25 Done")
