import os, time, math, datetime, requests, traceback
import pandas as pd
from SmartApi import SmartConnect
import pyotp

# --- CONFIG V4 ---
VOL_X = 3.0
RSI_BUY_MIN, RSI_BUY_MAX = 40, 70
RSI_SELL_MIN, RSI_SELL_MAX = 30, 60
TARGET_R = 1.0 # 1:1 - WinRate साठी

def send_tg(msg):
    try:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat = os.getenv("TELEGRAM_CHAT_ID")
        if not token or not chat: return
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, data={"chat_id": chat, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except: pass

# --- LOGIN ---
try:
    obj = SmartConnect(api_key=os.getenv("ANGEL_API_KEY"))
    totp = pyotp.TOTP(os.getenv("ANGEL_TOTP_SECRET")).now()
    obj.generateSession(os.getenv("ANGEL_CLIENT_ID"), os.getenv("ANGEL_PASSWORD"), totp)
    send_tg(f"FAST BOT V4 STARTED - 1000 Stocks - 2 Active - 6 Daily - 1 Min - 1:1:5 Trail + 3xVol + RSI {RSI_BUY_MIN}-{RSI_BUY_MAX}")
    print("LOGIN OK")
except Exception as e:
    print(f"Login fail {e}")
    exit()

# --- INDICATORS ---
def get_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_data(token, interval="ONE_MINUTE"):
    try:
        historicParam = {
            "exchange": "NSE",
            "symboltoken": token,
            "interval": interval,
            "fromdate": (datetime.datetime.now() - datetime.timedelta(days=5)).strftime("%Y-%m-%d %H:%M"),
            "todate": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        data = obj.getCandleData(historicParam)
        df = pd.DataFrame(data['data'], columns=['time','open','high','low','close','volume'])
        return df
    except: return None

# --- LOAD 1000 STOCKS ---
# तुझ्या आधीच्या फाईल मधून Token List घेतोय
try:
    # Angel Instrument List
    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    df_inst = pd.read_json(url)
    nse = df_inst[(df_inst['exch_seg']=='NSE') & (df_inst['symbol'].str.endswith('-EQ'))].head(1000)
    tokens = nse[['symbol','token']].values.tolist()
except:
    tokens = []

active_trades = {}
daily_count = 0

# --- MAIN LOOP ---
while True:
    try:
        now = datetime.datetime.now()
        if now.weekday() >= 5: time.sleep(60); continue
        if not (datetime.time(9,15) <= now.time() <= datetime.time(15,15)): time.sleep(60); continue

        for symbol, token in tokens:
            if daily_count >= 6: break
            if len(active_trades) >= 2: break

            df = get_data(token)
            if df is None or len(df) < 50: continue

            df['ema9'] = df['close'].ewm(span=9).mean()
            df['ema15'] = df['close'].ewm(span=15).mean()
            df['rsi'] = get_rsi(df['close'])
            df['vwap'] = (df['close'] * df['volume']).cumsum() / df['volume'].cumsum()
            df['vol_avg'] = df['volume'].rolling(20).mean()

            last = df.iloc[-1]
            prev = df.iloc[-2]

            vol_ratio = last['volume'] / last['vol_avg'] if last['vol_avg']>0 else 0
            rsi = last['rsi']

            buy_cond = (last['close'] > last['open'] and
                        vol_ratio >= VOL_X and
                        RSI_BUY_MIN < rsi < RSI_BUY_MAX and
                        last['close'] > last['vwap'] and
                        last['ema9'] > last['ema15'])

            sell_cond = (last['close'] < last['open'] and
                         vol_ratio >= VOL_X and
                         RSI_SELL_MIN < rsi < RSI_SELL_MAX and
                         last['close'] < last['vwap'] and
                         last['ema9'] < last['ema15'])

            if buy_cond and symbol not in active_trades:
                sl = prev['low']
                entry = last['close']
                diff = entry - sl
                if diff <=0: continue
                t1 = entry + diff * TARGET_R
                t2 = entry + diff * 1.5
                t5 = entry + diff * 2.5
                msg = f"🟢 BUY {symbol.replace('-EQ','')} @ {entry:.2f}\nSL: {sl:.2f}\nT1: {t1:.2f} T2: {t2:.2f} T5: {t5:.2f}\nVol: {vol_ratio:.1f}x RSI: {rsi:.1f} Trail ON"
                send_tg(msg)
                active_trades[symbol] = {"type":"BUY","entry":entry,"sl":sl}
                daily_count+=1

            if sell_cond and symbol not in active_trades:
                sl = prev['high']
                entry = last['close']
                diff = sl - entry
                if diff <=0: continue
                t1 = entry - diff * TARGET_R
                t2 = entry - diff * 1.5
                t5 = entry - diff * 2.5
                msg = f"🔴 SELL {symbol.replace('-EQ','')} @ {entry:.2f}\nSL: {sl:.2f}\nT1: {t1
