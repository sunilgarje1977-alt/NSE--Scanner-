import os, datetime, pytz, requests, pyotp, time
import pandas as pd
import numpy as np
from SmartApi import SmartConnect
from concurrent.futures import ThreadPoolExecutor, as_completed

API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PWD = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")
TELE_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELE_CHAT = os.getenv("TELEGRAM_CHAT_ID")

IST = pytz.timezone('Asia/Kolkata')

def ist_now():
    return datetime.datetime.now(IST)

def send_tg(m):
    try:
        url = f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELE_CHAT, "text": m, "parse_mode": "Markdown"}, timeout=15)
    except Exception as e:
        print(e)

smart = SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PWD, pyotp.TOTP(TOTP_SECRET).now())
print("Login OK", ist_now())

SYMBOLS = ["PGEL","BHEL","SAIL","SUZLON","IRFC","RVNL","IREDA","NHPC","SJVN","HUDCO","IRCON","NBCC","NCC","BEL","BDL","HAL","MAZDOCK","COCHINSHIP","GRSE","OIL","NMDC","TATACHEM","ASHOKLEY","VOLTAS","KEI","APARINDS","FEDERALBNK","BANKINDIA","IDBI","AUROPHARMA","LUPIN","GLENMARK","BIOCON","AARTIIND","BSOFT","CUMMINSIND","ESCORTS","INDHOTEL","BHARATFORG","UNOMINDA","TORNTPOWER","SONACOMS","POLYCAB","COFORGE","BSE","MUTHOOTFIN","PAYTM","VMM","WAAREENER","360ONE","AAVAS","ACE","AFFLE","AMBER","ANGELONE","BEML","BLS","KPITTECH","TATAELXSI","LTTS","CONCOR","PRESTIGE","PHOENIXLTD","SBICARD","IRB","JINDALSTEL","JSL","JSWENERGY","JUBLFOOD","KALYANKJIL","KAYNES","KEC","KFINTECH","M&MFIN","MASTEK","MCX","MEDANTA","NATCOPHARM","NAUKRI","OLECTRA","PEL","PNBHOUSING","RECLTD","SIEMENS","SUNTV","SYNGENE","TRENT","TRIDENT","ZYDUSLIFE","ZOMATO","DELHIVERY","MAPMYINDIA","PNCINFRA","GRINFRA","MTARTECH","CYIENT","TANLA","ROUTE","HAPPSTMNDS","LICI","LODHA","LTF","AUBANK","ADANIGREEN","BANKBARODA","BANDHANBNK","CANBK","CDSL","CGPOWER","CHOLAFIN","DABUR","DLF","DMART","GAIL","GODREJCP","HAVELLS","IDFCFIRSTB","INDIGO","IOC","IRCTC","LALPATHLAB","LAURUSLABS","LTIM","MOTHERSON","MPHASIS","PERSISTENT","PNB","RBLBANK","SRF","TATAPOWER","TITAN","VEDL","DIXON","SAFARI","CAMPUS","INDIAMART","INTELLECT","NETWEB","SYRMA","DATAPATTNS","PARAS","TATATECH","ELECON","HFCL","IEX","JWL","TEXRAIL","RAILTEL","RITES","CESC","MGL","WAAREERTL","VARUNBEV","VBL","DEVYANI","CHALET","VMART","ABFRL","RAYMOND","SOBHA","BRIGADE","ANANTRAJ","KARURVYSYA","CUB","UJJIVAN","FORTIS","KIMS","SULA"]

def calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1/period).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def analyze(sym):
    try:
        time.sleep(0.25)
        r = smart.searchScrip("NSE", sym)
        if not r or not r.get('data'):
            return None
        token = r['data'][0]['symboltoken']
        today = ist_now().strftime("%Y-%m-%d")
        from_date = f"{today} 09:00"
        to_date = f"{today} 15:30"
        hist = smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":from_date,"todate":to_date})
        if not hist or not hist.get('data') or len(hist['data']) < 25:
            from_date = (ist_now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d 09:00")
            hist = smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":from_date,"todate":to_date})
            if not hist or not hist.get('data') or len(hist['data']) < 25:
                return None

        df = pd.DataFrame(hist['data'], columns=['Time','Open','High','Low','Close','Volume'])
        for c in ['Open','High','Low','Close','Volume']:
            df[c] = df[c].astype(float)

        df['EMA9'] = df['Close'].ewm(span=9).mean()
        df['EMA15'] = df['Close'].ewm(span=15).mean()
        df['VWAP'] = ((df['High']+df['Low']+df['Close'])/3 * df['Volume']).cumsum() / df['Volume'].cumsum()
        df['AvgVol'] = df['Volume'].rolling(20).mean()
        df['RSI'] = calc_rsi(df['Close'], 14)

        curr = df.iloc[-1]
        prev = df.iloc[-2]

        ltp = float(curr['Close'])
        ema9 = float(curr['EMA9'])
        ema15 = float(curr['EMA15'])
        vwap = float(curr['VWAP'])
        vol = float(curr['Volume'])
        avgvol = float(curr['AvgVol'])
        rsi = float(curr['RSI'])
        p_ema9 = float(prev['EMA9'])
        p_ema15 = float(prev['EMA15'])

        if ltp < 50:
            return None
        if vol < avgvol:
            return None

        buy_cross = p_ema9 <= p_ema15 and ema9 > ema15
        buy_vwap = ema9 > vwap and ema15 > vwap and ltp > vwap
        buy_rsi = 55 <= rsi <= 68

        sell_cross = p_ema9 >= p_ema15 and ema9 < ema15
        sell_vwap = ema9 < vwap and ema15 < vwap and ltp < vwap
        sell_rsi = 32 <= rsi <= 45

        if buy_cross and buy_vwap and buy_rsi:
            return f"BUY:{sym}:{ltp:.1f}:{rsi:.0f}:{vol:.0f}"

        if sell_cross and sell_vwap and sell_rsi:
            return f"SELL:{sym}:{ltp:.1f}:{rsi:.0f}:{vol:.0f}"

        return None

    except Exception as e:
        print(f"{sym} err {e}")
        return None

buys = []
sells = []

with ThreadPoolExecutor(max_workers=5) as ex:
    futures = {ex.submit(analyze, s): s for s in set(SYMBOLS)}
    for f in as_completed(futures):
        res = f.result()
        if res:
            if res.startswith("BUY"):
                buys.append(res)
            else:
                sells.append(res)

now_str = ist_now().strftime("%d-%b %H:%M")
msg = f"📊 *BSE 1000 SmallCap 9/15 + VWAP + RSI {now_str}*\n{len(set(SYMBOLS))} checked\n\n"

if buys:
    txt = ""
    for b in buys[:15]:
        parts = b.split(":")
        txt += f"🟢 BUY {parts[1]} @ {parts[2]} RSI {parts[3]}\n"
    msg += f"*BUY:*\n{txt}\n"

if sells:
    txt = ""
    for b in sells[:15]:
        parts = b.split(":")
        txt += f"🔴 SELL {parts[1]} @ {parts[2]} RSI {parts[3]}\n"
    msg += f"*SELL:*\n{txt}\n"

if not buys and not sells:
    msg += "⏸️ No 9/15 Cross Now - Sideways"

send_tg(msg)
print(msg) 
