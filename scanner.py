import os, json, time, requests, pyotp, pandas as pd
from SmartApi import SmartConnect
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- SECRETS (GitHub Secret मधून येईल) ---
API_KEY = os.getenv("ANGEL_API_KEY","").strip()
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID","").strip()
PASSWORD = os.getenv("ANGEL_PASSWORD","")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET","").strip().replace(" ","").upper()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN","")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID","")

# --- तुझी 1000 LIST - Net नाही, तुझीच ---
data = """RELIANCE TCS HDFCBANK ICICIBANK INFY ITC SBIN BHARTIARTL LT BAJFINANCE MARUTI TITAN SUNPHARMA WIPRO ULTRACEMCO NTPC POWERGRID TATAMOTORS TATASTEEL JSWSTEEL HCLTECH BAJAJFINSV ASIANPAINT ONGC ADANIENT ADANIPORTS COALINDIA GRASIM HINDALCO HINDUNILVR CIPLA DIVISLAB DRREDDY EICHERMOT BPCL BRITANNIA HEROMOTOCO ICICIPRULI SBILIFE HDFCLIFE LTIM TRENT VEDL INDUSINDBK AXISBANK KOTAKBANK BAJAJ-AUTO APOLLOHOSP TATACONSUM NESTLEIND JSWENERGY NHPC SJVN GMRINFRA IDFCFIRSTB FEDERALBNK AUBANK INDIANB BANKINDIA UNIONBANK CANBK MAHABANK PNB BANKBARODA RECLTD PFC IRFC RVNL IRCTC HAL BEL BHEL SAIL TATAPOWER ADANIGREEN ADANIPOWER IDEA YESBANK SUZLON ENGINERSIN JIOFIN ZOMATO NYKAA PAYTM POLICYBZR DELHIVERY NAUKRI INDIAMART LTF MUTHOOTFIN MANAPPURAM CHOLAFIN BAJAJHLDNG SHRIRAMFIN PEL TATACHEM DEEPAKNTR AARTIIND ATUL SRF PIIND UPL COROMANDEL CHAMBLFERT GNFC FACT RCF GSFC TATACOMM INDIGO TORRENTPOWER CESC TORNTPHARM ALKEM AUROPHARMA LUPIN BIOCON GLAND LAURUSLABS IPCALAB ZYDUSLIFE ABB SIEMENS CUMMINSIND THERMAX VOLTAS BLUESTARCO DIXON AMBER SYRMA KAYNES TATATECH TATAELXSI KPITTECH COFORGE PERSISTENT MPHASIS LTTS 360ONE IEX MCX BSE CAMS CDSL KFINTECH ANGELONE MOTILALOFS ICICIGI NIACL GICRE STARHEALTH HDFCAMC UTIAMC NAM-INDIA SBICARD HUDCO IREDA IRB NBCC NCC DLF GODREJPROP OBEROIRLTY PRESTIGE BRIGADE SOBHA PHOENIXLTD LODHA MAHLIFE IBREALEST SUNTECK DMART VMART ABFRL SHOPERSTOP RAYMOND ARVIND VARDHMAN WELSPUNLIV TRIDENT KPRMILL PAGEIND LUXIND DOLLAR BATAINDIA RELAXO CAMPUS METROBRAND TTKPRESTIG CROMPTON HAVELLS POLYCAB KEI FINOLEX RRKABEL VGUARD BAJAJELEC WHIRLPOOL INOXWIND INDHOTEL EIHOTEL LEMONTREE CHALET DEVYANI JUBLFOOD WESTLIFE SAPPHIRE KALYANKJIL SENCO HINDZINC NATIONALUM APLAPOLLO JSL JINDALSTEL NMDC AMBUJACEM ACC SHREECEM RAMCOCEM JKCEMENT M&M TVSMOTOR ASHOKLEY ESCORTS SONACOMS MOTHERSON BHARATFORG MINDACORP ENDURANCE GABRIEL MRF CEAT BALKRISIND GRSE COCHINSHIP MAZDOCK BDL MIDHANI PARAS MTARTECH DATAPATTNS AVANTEL ASTRAMICRO DCXINDIA
AARTIDRUGS AAVAS ABSLAMC AFFLE AIAENG AJANTPHARM AKZOINDIA ALEMBICLTD ALKYLAMINE ALOKINDS ANANDRATHI ANANTRAJ APARINDS APLLTD APTUS ASAHIINDIA ASHOKA ASTERDM ASTRAL ATGL AVANTIFEED AWL BALAMINES BANDHANBNK BAYERCROP BBTC BLUEDART BSOFT CANFINHOME CAPLIPOINT CARBORUN CASTROLIND CCL CEATLTD CENTRALBK CERA CGCL CRAFTSMAN CREDITACC CRISIL CSBBANK CUB CYIENT DABUR DALBHARAT DCAL DCBBANK DCMSHRIRAM EASEMYTRIP ELGIEQUIP EMAMILTD EQUITASBNK ERIS ESABINDIA EXIDEIND FINEORG FINCABLES FSL GALAXYSURF GARFIBRES GESHIP GILLETTE GLAXO GLENMARK GMDCLTD GMRINFRA GODREJCP GODREJPROP GRANULES GRAPHITE GRINDWELL GRINFRA GUJALKALI GUJGASLTD HAPPSTMNDS HONASA IIFL INTELLECT IOC ISEC JBCHEPHARM JINDALSAW JIOFIN JUBLINGREA JUSTDIAL JYOTHYLAB KAJARIA KARURVYSYA KEC KIRLOSENG KRBL KSB KTKBANK LALPATHLAB LATENTVIEW LTIM LTTS MAHABANK MANYAVAR MAPMYINDIA MARICO MASTEK MAXHEALTH MCX MEDANTA METROPOLIS MGL MRF NAUKRI NAVINFLUOR NCC NESTLEIND NETWEB NH NIACL OFSS PATANJALI PERSISTENT PETRONET PFIZER PIDILITIND PNCINFRA POLYMED PRAJIND PRINCEPIPE PVRINOX QUESS RADICO RAILTEL RALLIS RAMCOCEM RATNAMANI RAYMOND RBLBANK RELAXO SAPPHIRE SBICARD SCHAEFFLER SEQUENT SHANKARA SHREECEM SIEMENS SJVN SKFINDIA SOLARINDS STAR STLTECH SUDARS"""

SYMBOLS = list(dict.fromkeys([s for s in data.split() if s.strip()]))
print(f"TOTAL 1000 LIST LOADED: {len(SYMBOLS)}")

def send_tg(msg):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":msg,"parse_mode":"Markdown"}, timeout=10)
    except: pass

# Login
obj = SmartConnect(api_key=API_KEY)
obj.generateSession(CLIENT_ID, PASSWORD, pyotp.TOTP(TOTP_SECRET).now())
print("Angel Login OK")

# Token Map
try:
    master = pd.read_json("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json")
    nse = master[(master['exch_seg']=='NSE') & (master['symbol'].str.endswith('-EQ'))]
    TMap = {str(r['symbol']).replace('-EQ',''): str(r['token']) for _, r in nse.iterrows() if str(r['symbol']).replace('-EQ','') in SYMBOLS}
except: TMap = {}

# --- TRADE MANAGEMENT ---
STATE_FILE = "trade_state.json"
def load_state():
    if os.path.exists(STATE_FILE):
        try: return json.load(open(STATE_FILE))
        except: pass
    return {"date": str(datetime.now().date()), "active": [], "closed": [], "pnl": 0.0, "count": 0}

def save_state(st):
    json.dump(st, open(STATE_FILE,"w"))

state = load_state()
if state["date"]!= str(datetime.now().date()):
    state = {"date": str(datetime.now().date()), "active": [], "closed": [], "pnl": 0.0, "count": 0}

# --- SCAN LOGIC - ALL YOUR CONDITIONS ---
def analyze(sym):
    token = TMap.get(sym)
    if not token: return None
    try:
        p = {"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":(datetime.now()-timedelta(days=5)).strftime("%Y-%m-%d 09:15"),"todate":datetime.now().strftime("%Y-%m-%d %H:%M")}
        res = obj.getCandleData(p)
        d = res.get('data')
        if not d or len(d) < 30: return None
        df = pd.DataFrame(d, columns=['date','open','high','low','close','volume'])

        df['ema9'] = df['close'].ewm(span=9).mean()
        df['ema15'] = df['close'].ewm(span=15).mean()
        df['vol_avg'] = df['volume'].rolling(20).mean()
        df['vwap'] = (df['close']*df['volume']).cumsum() / df['volume'].cumsum()
        delta = df['close'].diff()
        gain = delta.where(delta>0,0).rolling(14).mean()
        loss = -delta.where(delta<0,0).rolling(14).mean()
        df['rsi'] = 100 - (100/(1+gain/loss))
        df['high20'] = df['high'].rolling(20).max()
        df['low20'] = df['low'].rolling(20).min()

        last = df.iloc[-1]
        prev = df.iloc[-2]

        # BUY - तुझ्या सर्व Condition
        buy_cond = (
            last['close'] > df['high20'].iloc[-2] and # Chart Breakout
            last['close'] > last['open'] and # 5min Green Candle
            last['volume'] > last['vol_avg']*1.2 and # Candle with Volume
            last['ema9'] > last['ema15'] and prev['ema9'] <= prev['ema15'] and # 9EMA cross 15EMA Up
            last['close'] > last['vwap'] and # VWAP वर Close
            last['rsi'] >= 60 # RSI 60
        )
        if buy_cond:
            entry = last['close'] # Close वर Buy
            sl = last['low'] # SL Candle Low
            risk = entry - sl
            if risk <=0: return None
            return {"sym":sym,"side":"BUY","entry":entry,"sl":sl,"t1":entry+risk*1,"t2":entry+risk*2,"t5":entry+risk*5,"time":str(datetime.now())}

        # SELL - तुझ्या सर्व Condition
        sell_cond = (
            last['close'] < df['low20'].iloc[-2] and # Breakdown
            last['close'] < last['open'] and abs(last['close']-last['open']) > (last['high']-last['low'])*0.6 and # Big Red Candle
            last['volume'] > last['vol_avg']*1.2 and
            last['ema9'] < last['ema15'] and prev['ema9'] >= prev['ema15'] and # 9EMA cross Down
            last['close'] < last['vwap'] and # VWAP खाली Close
            last['rsi'] <= 40 # RSI 40
        )
        if sell_cond:
            entry = last['close'] # Red Candle Close वर Sell
            sl = last['high'] # SL Candle High
            risk = sl - entry
            if risk <=0: return None
            return {"sym":sym,"side":"SELL","entry":entry,"sl":sl,"t1":entry-risk*1,"t2":entry-risk*2,"t5":entry-risk*5,"time":str(datetime.now())}
    except: return None
    return None

print(f"🚀 LIVE BOT STARTED - 1000 Stocks - 1 Min Loop")
send_tg(f"🚀 *LIVE BOT STARTED* {datetime.now().strftime('%d-%m %H:%M')}\n1000 Stocks | 2 Active | 6 Daily | 1 Min Signal")

# LIVE LOOP - 1 मिनिटाला
while True:
    try:
        # Daily Reset
        if state["date"]!= str(datetime.now().date()):
            state = {"date": str(datetime.now().date()), "active": [], "closed": [], "pnl": 0.0, "count": 0}

        # 1. Check Trailing & PnL for Active Trades
        if state["active"]:
            for trade in state["active"][:]:
                try:
                    # LTP घे
                    tok = TMap.get(trade['sym'])
                    if not tok: continue
                    ltp_data = obj.getCandleData({"exchange":"NSE","symboltoken":tok,"interval":"ONE_MINUTE","fromdate":datetime.now().strftime("%Y-%m-%d 09:15"),"todate":datetime.now().strftime("%Y-%m-%d %H:%M")})
                    ltp = ltp_data['data'][-1][4] if ltp_data.get('data') else trade['entry']

                    # Trailing Stoploss
                    if trade['side']=="BUY":
                        if ltp >= trade['t1'] and trade['sl'] < trade['entry']: trade['sl'] = trade['entry'] # T1 ला SL Cost ला
                        if ltp >= trade['t2'] and trade['sl'] < trade['t1']: trade['sl'] = trade['t1'] # T2 ला SL T1 ला
                        if ltp <= trade['sl']: # SL Hit
                            pnl = ltp - trade['entry']
                            state["closed"].append({**trade,"exit":ltp,"pnl":pnl,"reason":"SL"})
                            state["active"].remove(trade)
                            state["pnl"] += pnl
                            send_tg(f"🔴 *SL HIT* {trade['sym']} {trade['side']} Exit {ltp:.1f} PnL {pnl:.1f}")
                    else: # SELL
                        if ltp <= trade['t1'] and trade['sl'] > trade['entry']: trade['sl'] = trade['entry']
                        if ltp <= trade['t2'] and trade['sl'] > trade['t1']: trade['sl'] = trade['t1']
                        if ltp >= trade['sl']:
                            pnl = trade['entry'] - ltp
                            state["closed"].append({**trade,"exit":ltp,"pnl":pnl,"reason":"SL"})
                            state["active"].remove(trade)
                            state["pnl"] += pnl
                            send_tg(f"🔴 *SL HIT* {trade['sym']} {trade['side']} Exit {ltp:.1f} PnL {pnl:.1f}")

                    # Target Hit Check
                    if trade['side']=="BUY" and ltp >= trade['t5']:
                        pnl = ltp - trade['entry']
                        state["closed"].append({**trade,"exit":ltp,"pnl":pnl,"reason":"T5"})
                        state["active"].remove(trade)
                        state["pnl"] += pnl
                        send_tg(f"🟢 *T5 HIT* {trade['sym']} BUY Exit {ltp:.1f} PnL +{pnl:.1f}")
                    if trade['side']=="SELL" and ltp <= trade['t5']:
                        pnl = trade['entry'] - ltp
                        state["closed"].append({**trade,"exit":ltp,"pnl":pnl,"reason":"T5"})
                        state["active"].remove(trade)
                        state["pnl"] += pnl
                        send_tg(f"🟢 *T5 HIT* {trade['sym']} SELL Exit {ltp:.1f} PnL +{pnl:.1f}")

                except: pass

        save_state(state)

        # 2. Daily 6 Trade आणि 2 Active Check
        if len(state["closed"]) >= 6:
            print(f"Daily 6 Limit Done - PnL {state['pnl']:.2f}")
            time.sleep(60)
            continue

        if len(state["active"]) >= 2:
            print(f"2 Active Running - Waiting for close... Active: {[t['sym'] for t in state['active']]}")
            time.sleep(60)
            continue

        # 3. New Scan - 1000 Stocks Fast (50 Threads)
        print(f"Scanning {len(TMap)} stocks... Active {len(state['active'])}/2 Closed {len(state['closed'])}/6 PnL {state['pnl']:.2f}")
        new_signals = []
        with ThreadPoolExecutor(max_workers=50) as ex:
            futs = [ex.submit(analyze, s) for s in SYMBOLS if s in TMap and s not in [t['sym'] for t in state["active"]]]
            for f in as_completed(futs):
                r = f.result()
                if r: new_signals.append(r)

        # 4. Take New Trades - एक Close झाला की दुसरा Active होणार
        for sig in new_signals:
            if len(state["active"]) >= 2 or len(state["closed"]) + len(state["active"]) >= 6: break
            if sig['sym'] in [t['sym'] for t in state["active"]+state["closed"]]: continue

            state["active"].append(sig)
            state["count"] += 1
            msg = f"⚡ *NEW {sig['side']} SIGNAL* {sig['sym']}\nEntry (Close): {sig['entry']:.1f}\nSL (Candle {'Low' if sig['side']=='BUY' else 'High'}): {sig['sl']:.1f}\nT1 {sig['t1']:.1f} | T2 {sig['t2']:.1f} | T5 {sig['t5']:.1f}\n\n*Daily:* {len(state['closed'])}/6 | *Active:* {len(state['active'])}/2 | *PnL:* {state['pnl']:.1f}"
            send_tg(msg)
            print(f"NEW TRADE: {sig}")

        save_state(state)

        # Daily Report हर तासाला
        if datetime.now().minute == 0:
            send_tg(f"📊 *HOURLY REPORT {datetime.now().strftime('%H:%M')}*\nActive: {len(state['active'])}/2 | Closed: {len(state['closed'])}/6 | PnL: {state['pnl']:.2f}\nActive Trades: {', '.join([t['sym'] for t in state['active']]) if state['active'] else 'None'}")

    except Exception as e:
        print(f"Error in loop: {e}")

    time.sleep(60) # 1 मिनिटाला Signal
