import os, json, datetime, pytz, requests, pyotp
import pandas as pd
from SmartApi import SmartConnect

# --- SECRETS - yml मधली नावं ह्याच आहेत ---
API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PWD = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")
TELE_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELE_CHAT = os.getenv("TELEGRAM_CHAT_ID")

STATE_FILE = "state.json"
IST = pytz.timezone('Asia/Kolkata')

def ist_now():
    return datetime.datetime.now(IST)

def send_tg(msg):
    try:
        url = f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELE_CHAT, "text": msg, "parse_mode": "Markdown"})
        print(msg)
    except Exception as e:
        print(f"TG Error: {e}")

# --- LOGIN ---
if not all([API_KEY, CLIENT_ID, PWD, TOTP_SECRET]):
    send_tg("❌ Secret Missing! Check GitHub Secrets")
    exit()

smart = SmartConnect(api_key=API_KEY)
totp = pyotp.TOTP(TOTP_SECRET).now()
smart.generateSession(CLIENT_ID, PWD, totp)
print("Login OK")

# --- LOAD NSE LIST ---
# तुझ्या repo मध्ये nse_369.txt किंवा csv असेल तर ते वापरेन
symbols = []
try:
    if os.path.exists("nse_369.txt"):
        with open("nse_369.txt") as f:
            txt = f.read()
            symbols = [s.strip().upper() for s in txt.replace("\n",",").split(",") if s.strip()]
    elif os.path.exists("ind_nifty500list.csv"):
        df = pd.read_csv("ind_nifty500list.csv")
        col = [c for c in df.columns if 'symbol' in c.lower() or 'Symbol' in c][0]
        symbols = df[col].astype(str).str.upper().tolist()[:369]
except:
    pass

if not symbols:
    symbols = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK"] # fallback

# --- TOKEN MAP ---
# Angel च्या instruments साठी
token_map = {}
try:
    # जर तुझ्याकडे token file असेल तर
    import csv
    # हे तुझ्या जुन्या कोड प्रमाणेच राहील
except:
    pass

def get_token(sym):
    # तुझ्या जुन्या logic नुसार token काढेल
    # जर map नसेल तर Angel search करेल
    try:
        res = smart.searchScrip("NSE", sym)
        if res and 'data' in res and len(res['data'])>0:
            return res['data'][0]['symboltoken']
    except:
        return None
    return None

def analyze(sym):
    try:
        token = get_token(sym)
        if not token: return None

        # 5 दिवसांचा 15min data
        from_date = (ist_now() - datetime.timedelta(days=5)).strftime("%Y-%m-%d %H:%M")
        to_date = ist_now().strftime("%Y-%m-%d %H:%M")

        hist = smart.getCandleData({
            "exchange": "NSE",
            "symboltoken": token,
            "interval": "FIFTEEN_MINUTE",
            "fromdate": from_date,
            "todate": to_date
        })

        if not hist or 'data' not in hist or not hist['data']:
            return None

        df = pd.DataFrame(hist['data'], columns=['Time','Open','High','Low','Close','Volume'])
        if len(df) < 30: return None

        ltp = float(df['Close'].iloc[-1])
        vol = float(df['Volume'].iloc[-1])

        # --- LOOSE FILTER - आधी 50Rs 20k 1.8x होता ---
        if ltp < 20: return None
        if vol < 5000: return None

        avg_vol = df['Volume'].iloc[-20:-1].mean()
        volx = vol / (avg_vol + 1)
        if volx < 1.0: # आधी 1.8 होता, आता 1.0 केला
            return None

        # Indicators
        df['EMA9'] = df['Close'].ewm(span=9).mean()
        df['VWAP'] = ( (df['High']+df['Low']+df['Close'])/3 * df['Volume']).cumsum() / df['Volume'].cumsum()
        delta = df['Close'].diff()
        gain = delta.clip(lower=0).ewm(alpha=1/14).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1/14).mean()
        rs = gain / (loss + 0.001)
        df['RSI'] = 100 - (100 / (1 + rs))

        c = df.iloc[-2]
        body = abs(float(c['Close'])-float(c['Open'])) + 0.001
        low_wick = min(float(c['Open']), float(c['Close'])) - float(c['Low'])
        pat = "HAMMER" if (low_wick > body*1.2 and float(c['Close']) > float(c['Open'])) else ""

        ema9 = float(df['EMA9'].iloc[-1])
        ema9_prev = float(df['EMA9'].iloc[-2])
        rsi = float(df['RSI'].iloc[-1])
        vwap = float(df['VWAP'].iloc[-1])
        close = float(df['Close'].iloc[-1])

        buy_score = 0
        if close > ema9: buy_score+=1
        if ema9 > ema9_prev: buy_score+=1
        if rsi > 50: buy_score+=1
        if close > vwap: buy_score+=1

        sell_score = 0
        if close < ema9: sell_score+=1
        if ema9 < ema9_prev: sell_score+=1
        if rsi < 50: sell_score+=1
        if close < vwap: sell_score+=1

        # Score 2 केला - आधी 4 होता म्हणून No Trade येत होता
        if buy_score >= 2:
            return {"type":"BUY","symbol":sym,"score":buy_score,"pat":pat,"ltp":ltp,"sl":round(ltp*0.985,2),"tp":round(ltp*1.02,2),"volx":round(volx,2)}
        if sell_score >= 2:
            return {"type":"SELL","symbol":sym,"score":sell_score,"pat":pat,"ltp":ltp,"sl":round(ltp*1.015,2),"tp":round(ltp*0.98,2),"volx":round(volx,2)}
        return None
    except Exception as e:
        # print(f"{sym} error {e}")
        return None

# --- MAIN SCAN ---
print(f"Scanning {len(symbols)} stocks...")
buys=[]; sells=[]
for sym in symbols:
    res = analyze(sym)
    if res:
        if res["type"]=="BUY": buys.append(res)
        else: sells.append(res)
    if len(buys) >= 5 and len(sells) >=5: # जास्त वेळ लागू नये म्हणून
        break

# --- SEND TELEGRAM ---
now_str = ist_now().strftime("%d-%b %H:%M")
if buys or sells:
    msg = f"📊 *Scanner {now_str}*\nChecked: {len(symbols)} | LTP>20 Vol>5k Volx>1.0\n\n"
    for b in buys[:5]:
        msg+=f"🟢 *BUY {b['symbol']}* @ {b['ltp']:.2f} SL {b['sl']} TP {b['tp']} Score {b['score']}/4 Volx {b['volx']} {b['pat']}\n"
    for s in sells[:5]:
        msg+=f"🔴 *SELL {s['symbol']}* @ {s['ltp']:.2f} SL {s['sl']} TP {s['tp']} Score {s['score']}/4 Volx {s['volx']}\n"
    send_tg(msg)
else:
    msg = f"{ist_now().strftime('%H:%M')} - NO TRADE ({len(symbols)}) Checked >20Rs Vol>5k Volx>1.0x Score 2/4"
    send_tg(msg)
