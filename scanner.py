import os, json, datetime, pytz, requests, pyotp
import pandas as pd
from SmartApi import SmartConnect

# Secrets from GitHub
API_KEY = os.getenv("API_KEY")
CLIENT_ID = os.getenv("CLIENT_ID")
PWD = os.getenv("MPIN")
TOTP_SECRET = os.getenv("TOTP_SECRET")
TELE_TOKEN = os.getenv("TELE_TOKEN")
TELE_CHAT = os.getenv("TELE_CHAT")

STATE_FILE = "state.json"
IST = pytz.timezone('Asia/Kolkata')
def ist_now(): return datetime.datetime.now(IST)

def send_tg(msg):
    try:
        url = f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELE_CHAT, "text": msg})
    except: pass

# Login
smart = SmartConnect(api_key=API_KEY)
totp = pyotp.TOTP(TOTP_SECRET).now()
smart.generateSession(CLIENT_ID, PWD, totp)

# Token Map Load
# तुझ्या repo मध्ये instruments.csv / token_map.json असेल तर ते load करेल
token_map = {}
try:
    # जर तुझ्याकडे token file असेल तर
    df_map = pd.read_csv("ind_nifty500list.csv")
    # example: symbol, token
    for _, r in df_map.iterrows():
        token_map[r['Symbol']] = str(r['Token'])
except:
    pass

def get_nse_list():
    # 369 ची list तुझीच वापरणार, फक्त return
    try:
        with open("nse_369.txt") as f:
            syms = [x.strip() for x in f.read().split(",")]
            return syms
    except:
        return list(token_map.keys())[:369]

def analyze(sym):
    try:
        token = token_map.get(sym)
        if not token: return None
        
        fdate = (ist_now()-datetime.timedelta(days=5)).strftime("%Y-%m-%d %H:%M")
        tdate = ist_now().strftime("%Y-%m-%d %H:%M")
        hist = smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIFTEEN_MINUTE","fromdate":fdate,"todate":tdate})
        if not hist or 'data' not in hist: return None
        df = pd.DataFrame(hist['data'], columns=['Time','Open','High','Low','Close','Volume'])
        if len(df) < 30: return None

        ltp = float(df['Close'].iloc[-1])
        vol = float(df['Volume'].iloc[-1])

        # --- LOOSE FILTER ---
        if ltp < 20: return None
        if vol < 5000: return None

        avg_vol = df['Volume'].iloc[-20:-1].mean()
        volx = vol / (avg_vol+1)
        if volx < 1.0:  # आधी 1.8 होता, आता 1.0 केला
            return None

        # Indicators
        df['EMA9'] = df['Close'].ewm(9).mean()
        df['VWAP'] = ((df['High']+df['Low']+df['Close'])/3 * df['Volume']).cumsum() / df['Volume'].cumsum()
        delta = df['Close'].diff()
        gain = delta.clip(lower=0).ewm(alpha=1/14).mean()
        loss = abs(delta.clip(upper=0)).ewm(alpha=1/14).mean()
        df['RSI'] = 100 - (100 / (1 + gain/loss))

        c = df.iloc[-2]
        body = abs(c['Close']-c['Open'])+1
        low_p = min(c['Open'],c['Close'])-c['Low']
        pat = "HAMMER" if (low_p>body*1.2 and c['Close']>c['Open']) else ""

        ema9 = df['EMA9'].iloc[-1]
        ema9_prev = df['EMA9'].iloc[-2]
        rsi = df['RSI'].iloc[-1]
        vwap = df['VWAP'].iloc[-1]
        close = df['Close'].iloc[-1]

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

        # Score 2 वर आणला - आधी 4 होता
        if buy_score >= 2:
            return {"type":"BUY","symbol":sym,"score":buy_score,"pat":pat,"ltp":ltp,"sl":ltp*0.985,"tp":ltp*1.02,"volx":round(volx,2)}
        if sell_score >= 2:
            return {"type":"SELL","symbol":sym,"score":sell_score,"pat":pat,"ltp":ltp,"sl":ltp*1.015,"tp":ltp*0.98,"volx":round(volx,2)}
        return None
    except:
        return None

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                st=json.load(f)
                if st['date']==ist_now().strftime("%Y-%m-%d"): return st
        except: pass
    return {"date":ist_now().strftime("%Y-%m-%d"),"active":[],"closed":[]}

state = load_state()
universe = get_nse_list()
print(f"Checked {len(universe)} stocks")

buys=[]; sells=[]
for sym in universe:
    if any(tr["symbol"]==sym for tr in state["active"]): continue
    res = analyze(sym)
    if res:
        if res["type"]=="BUY": buys.append(res)
        else: sells.append(res)

if buys or sells:
    msg = f"Scanner {ist_now().strftime('%d-%b %H:%M')}\n"
    for b in buys[:5]:
        msg+=f"🟢 BUY {b['symbol']} @ {b['ltp']:.2f} SL {b['sl']:.2f} TP {b['tp']:.2f} Volx {b['volx']} {b['pat']}\n"
    for s in sells[:5]:
        msg+=f"🔴 SELL {s['symbol']} @ {s['ltp']:.2f} SL {s['sl']:.2f} TP {s['tp']:.2f} Volx {s['volx']}\n"
    send_tg(msg)
    print(msg)
else:
    # आता No Trade आला तरी Volx 1.0 दाखवेल
    msg = f"{ist_now().strftime('%H:%M')} - NO TRADE ({len(universe)}) Checked >20Rs Vol>5k Volx>1.0x"
    send_tg(msg)
    print(msg) 
