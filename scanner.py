import os, json, time, requests, pyotp, pandas as pd
from SmartApi import SmartConnect
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- SECRETS ---
API_KEY = os.getenv("ANGEL_API_KEY","").strip()
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID","").strip()
PASSWORD = os.getenv("ANGEL_PASSWORD","")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET","").strip().replace(" ","").upper()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN","")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID","")

def send_tg(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":msg,"parse_mode":"Markdown"}, timeout=15)
    except: pass

# --- तुझी 1000 LIST - तू दिलेली ---
data = """
RELIANCE TCS HDFCBANK ICICIBANK INFY ITC SBIN BHARTIARTL LT BAJFINANCE MARUTI TITAN SUNPHARMA WIPRO ULTRACEMCO NTPC POWERGRID TATAMOTORS TATASTEEL JSWSTEEL HCLTECH BAJAJFINSV ASIANPAINT ONGC ADANIENT ADANIPORTS COALINDIA GRASIM HINDALCO HINDUNILVR CIPLA DIVISLAB DRREDDY EICHERMOT BPCL BRITANNIA HEROMOTOCO ICICIPRULI SBILIFE HDFCLIFE LTIM TRENT VEDL INDUSINDBK AXISBANK KOTAKBANK BAJAJ-AUTO APOLLOHOSP TATACONSUM NESTLEIND JSWENERGY NHPC SJVN GMRINFRA IDFCFIRSTB FEDERALBNK AUBANK INDIANB BANKINDIA UNIONBANK CANBK MAHABANK PNB BANKBARODA RECLTD PFC IRFC RVNL IRCTC HAL BEL BHEL SAIL TATAPOWER ADANIGREEN ADANIPOWER IDEA YESBANK SUZLON ENGINERSIN JIOFIN ZOMATO NYKAA PAYTM POLICYBZR DELHIVERY NAUKRI INDIAMART LTF MUTHOOTFIN MANAPPURAM CHOLAFIN BAJAJHLDNG SHRIRAMFIN PEL TATACHEM DEEPAKNTR AARTIIND ATUL SRF PIIND UPL COROMANDEL CHAMBLFERT GNFC FACT RCF GSFC TATACOMM INDIGO TORRENTPOWER CESC TORNTPHARM ALKEM AUROPHARMA LUPIN BIOCON GLAND LAURUSLABS IPCALAB ZYDUSLIFE ABB SIEMENS CUMMINSIND THERMAX VOLTAS BLUESTARCO DIXON AMBER SYRMA KAYNES TATATECH TATAELXSI KPITTECH COFORGE PERSISTENT MPHASIS LTTS 360ONE IEX MCX BSE CAMS CDSL KFINTECH ANGELONE MOTILALOFS ICICIGI NIACL GICRE STARHEALTH HDFCAMC UTIAMC NAM-INDIA SBICARD HUDCO IREDA IRB NBCC NCC DLF GODREJPROP OBEROIRLTY PRESTIGE BRIGADE SOBHA PHOENIXLTD LODHA MAHLIFE IBREALEST SUNTECK DMART VMART ABFRL SHOPERSTOP RAYMOND ARVIND VARDHMAN WELSPUNLIV TRIDENT KPRMILL PAGEIND LUXIND DOLLAR BATAINDIA RELAXO CAMPUS METROBRAND TTKPRESTIG CROMPTON HAVELLS POLYCAB KEI FINOLEX RRKABEL VGUARD BAJAJELEC WHIRLPOOL INOXWIND INDHOTEL EIHOTEL LEMONTREE CHALET DEVYANI JUBLFOOD WESTLIFE SAPPHIRE KALYANKJIL SENCO HINDZINC NATIONALUM APLAPOLLO JSL JINDALSTEL NMDC AMBUJACEM ACC SHREECEM RAMCOCEM JKCEMENT M&M TVSMOTOR ASHOKLEY ESCORTS SONACOMS MOTHERSON BHARATFORG MINDACORP ENDURANCE GABRIEL MRF CEAT BALKRISIND GRSE COCHINSHIP MAZDOCK BDL MIDHANI PARAS MTARTECH DATAPATTNS AVANTEL ASTRAMICRO DCXINDIA
AARTIDRUGS AAVAS ABSLAMC AFFLE AIAENG AJANTPHARM AKZOINDIA ALEMBICLTD ALKYLAMINE ALOKINDS ANANDRATHI ANANTRAJ APARINDS APLLTD APTUS ASAHIINDIA ASHOKA ASTERDM ASTRAL ATGL AVANTIFEED AWL BALAMINES BANDHANBNK BAYERCROP BBTC BLUEDART BSOFT CANFINHOME CAPLIPOINT CARBORUN CASTROLIND CCL CEATLTD CENTRALBK CERA CGCL CRAFTSMAN CREDITACC CRISIL CSBBANK CUB CYIENT DABUR DALBHARAT DCAL DCBBANK DCMSHRIRAM EASEMYTRIP ELGIEQUIP EMAMILTD EQUITASBNK ERIS ESABINDIA EXIDEIND FINEORG FINCABLES FSL GALAXYSURF GARFIBRES GESHIP GILLETTE GLAXO GLENMARK GMDCLTD GODREJCP GRANULES GRAPHITE GRINDWELL GRINFRA GUJALKALI GUJGASLTD HAPPSTMNDS HONASA IIFL INTELLECT IOC ISEC JBCHEPHARM JINDALSAW JUBLINGREA JUSTDIAL JYOTHYLAB KAJARIA KARURVYSYA KEC KIRLOSENG KRBL KSB KTKBANK LALPATHLAB LATENTVIEW MANYAVAR MAPMYINDIA MARICO MASTEK MAXHEALTH MEDANTA METROPOLIS MGL MRF NAVINFLUOR NETWEB NH OFSS PATANJALI PETRONET PFIZER PIDILITIND PNCINFRA POLYMED PRAJIND PRINCEPIPE PVRINOX QUESS RADICO RAILTEL RALLIS RAMCOCEM RATNAMANI RBLBANK RELAXO SAPPHIRE SCHAEFFLER SEQUENT SHANKARA SKFINDIA SOLARINDS STAR STLTECH SUDARS ZYDUSLIFE
"""

SYMBOLS = list(dict.fromkeys([s.strip() for s in data.split() if s.strip()]))
print(f"TOTAL LOADED: {len(SYMBOLS)}")

# --- FILES FOR TRACKING ---
ACTIVE_FILE = "active_positions.json"
DAILY_FILE = "daily_pnl.json"

def load_json(file, default):
    if os.path.exists(file):
        try: return json.load(open(file))
        except: return default
    return default

# --- LOGIN ---
obj = SmartConnect(api_key=API_KEY)
obj.generateSession(CLIENT_ID, PASSWORD, pyotp.TOTP(TOTP_SECRET).now())
print("Angel Login OK")

# --- TOKEN MAP ---
try:
    master = pd.read_json("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json")
    nse = master[(master['exch_seg']=='NSE') & (master['symbol'].str.endswith('-EQ'))]
    TMap = {str(r['symbol']).replace('-EQ',''): str(r['token']) for _, r in nse.iterrows() if str(r['symbol']).replace('-EQ','') in SYMBOLS}
except: TMap = {}
print(f"Tokens: {len(TMap)}/{len(SYMBOLS)}")

def check_position_pnl():
    active = load_json(ACTIVE_FILE, [])
    daily = load_json(DAILY_FILE, {"date": datetime.now().strftime("%Y-%m-%d"), "pnl": 0.0, "trades": 0, "wins": 0, "loss": 0})
    # Reset if new day
    if daily.get("date")!= datetime.now().strftime("%Y-%m-%d"):
        daily = {"date": datetime.now().strftime("%Y-%m-%d"), "pnl": 0.0, "trades": 0, "wins": 0, "loss": 0}

    new_active = []
    for pos in active:
        token = TMap.get(pos['symbol'])
        if not token:
            new_active.append(pos)
            continue
        try:
            p = {"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":(datetime.now()-timedelta(days=1)).strftime("%Y-%m-%d 09:15"),"todate":datetime.now().strftime("%Y-%m-%d %H:%M")}
            d = obj.getCandleData(p).get('data')
            if not d:
                new_active.append(pos)
                continue
            ltp = d[-1][4] # close
            # Check SL / Target
            if pos['type'] == 'BUY':
                # Trailing SL Logic
                if ltp >= pos['t2'] and pos['sl'] < pos['t1']:
                    pos['sl'] = pos['t1'] # T2 hit -> SL to T1
                    send_tg(f"🔄 *TRAILING* {pos['symbol']} SL -> T1 {pos['t1']:.1f} | LTP {ltp}")
                elif ltp >= pos['t1'] and pos['sl'] < pos['entry']:
                    pos['sl'] = pos['entry'] # T1 hit -> SL to Cost
                    send_tg(f"🔄 *TRAILING* {pos['symbol']} SL -> COST {pos['entry']:.1f} | LTP {ltp}")

                if ltp <= pos['sl']:
                    pnl = ltp - pos['entry']
                    daily['pnl'] += pnl
                    daily['trades'] += 1
                    if pnl>0: daily['wins']+=1
                    else: daily['loss']+=1
                    send_tg(f"❌ *SL HIT* {pos['symbol']} {pos['type']} PnL {pnl:.1f} | Daily PnL {daily['pnl']:.1f}")
                elif ltp >= pos['t5']:
                    pnl = pos['t5'] - pos['entry']
                    daily['pnl'] += pnl
                    daily['trades'] += 1
                    daily['wins']+=1
                    send_tg(f"✅ *T5 HIT* {pos['symbol']} PnL {pnl:.1f} | Daily PnL {daily['pnl']:.1f}")
                else:
                    new_active.append(pos)
            else: # SELL
                if ltp <= pos['t2'] and pos['sl'] > pos['t1']:
                    pos['sl'] = pos['t1']
                    send_tg(f"🔄 *TRAILING* {pos['symbol']} SL -> T1 {pos['t1']:.1f} | LTP {ltp}")
                elif ltp <= pos['t1'] and pos['sl'] > pos['entry']:
                    pos['sl'] = pos['entry']
                    send_tg(f"🔄 *TRAILING* {pos['symbol']} SL -> COST {pos['entry']:.1f} | LTP {ltp}")

                if ltp >= pos['sl']:
                    pnl = pos['entry'] - ltp
                    daily['pnl'] += pnl
                    daily['trades'] += 1
                    if pnl>0: daily['wins']+=1
                    else: daily['loss']+=1
                    send_tg(f"❌ *SL HIT* {pos['symbol']} {pos['type']} PnL {pnl:.1f} | Daily PnL {daily['pnl']:.1f}")
                elif ltp <= pos['t5']:
                    pnl = pos['entry'] - pos['t5']
                    daily['pnl'] += pnl
                    daily['trades'] += 1
                    daily['wins']+=1
                    send_tg(f"✅ *T5 HIT* {pos['symbol']} PnL {pnl:.1f} | Daily PnL {daily['pnl']:.1f}")
                else:
                    new_active.append(pos)
        except:
            new_active.append(pos)

    json.dump(new_active, open(ACTIVE_FILE,'w'))
    json.dump(daily, open(DAILY_FILE,'w'))
    return new_active, daily

def scan_one(sym):
    token = TMap.get(sym)
    if not token: return None
    try:
        p = {"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":(datetime.now()-timedelta(days=5)).strftime("%Y-%m-%d 09:15"),"todate":datetime.now().strftime("%Y-%m-%d %H:%M")}
        c = obj.getCandleData(p)
        d = c.get('data')
        if not d or len(d) < 25: return None
        df = pd.DataFrame(d, columns=['date','open','high','low','close','volume'])
        df['ema9'] = df['close'].ewm(span=9).mean()
        df['ema15'] = df['close'].ewm(span=15).mean()
        df['vol_avg'] = df['volume'].rolling(20).mean()
        df['vwap'] = (df['close']*df['volume']).cumsum()/df['volume'].cumsum()
        delta = df['close'].diff()
        gain = delta.where(delta>0,0).rolling(14).mean()
        loss = -delta.where(delta<0,0).rolling(14).mean()
        df['rsi'] = 100-(100/(1+gain/loss))
        df['high20'] = df['high'].rolling(20).max()
        df['low20'] = df['low'].rolling(20).min()
        last = df.iloc[-1]
        prev = df.iloc[-2]

        # --- BUY CONDITION तुझंच ---
        is_breakout = last['close'] > df['high20'].iloc[-2]
        is_green = last['close'] > last['open']
        is_vol = last['volume'] > last['vol_avg']*1.2
        is_cross_up = last['ema9'] > last['ema15'] and prev['ema9'] <= prev['ema15']
        is_vwap_up = last['close'] > last['vwap']
        is_rsi60 = last['rsi'] >= 60

        if is_breakout and is_green and is_vol and is_cross_up and is_vwap_up and is_rsi60:
            risk = last['close'] - last['low']
            if risk > 0:
                entry = last['close']
                return {
                    "symbol": sym, "type": "BUY", "entry": entry,
                    "sl": last['low'], "t1": entry + risk*1, "t2": entry + risk*2, "t5": entry + risk*5,
                    "rsi": last['rsi'], "msg": f"BUY {sym} @ {entry:.1f} (Green Close)\nSL {last['low']:.1f} (Low)\nT1 {entry+risk*1:.1f} | T2 {entry+risk*2:.1f} | T5 {entry+risk*5:.1f}\nRSI {last['rsi']:.0f} | VWAP UP | Vol {last['volume']/last['vol_avg']:.1f}x"
                }

        # --- SELL CONDITION तुझंच ---
        is_breakdown = last['close'] < df['low20'].iloc[-2]
        is_red = last['close'] < last['open']
        is_vol_s = last['volume'] > last['vol_avg']*1.2
        is_cross_down = last['ema9'] < last['ema15'] and prev['ema9'] >= prev['ema15']
        is_vwap_down = last['close'] < last['vwap']
        is_rsi40 = last['rsi'] <= 40

        if is_breakdown and is_red and is_vol_s and is_cross_down and is_vwap_down and is_rsi40:
            risk = last['high'] - last['close']
            if risk > 0:
                entry = last['close']
                return {
                    "symbol": sym, "type": "SELL", "entry": entry,
                    "sl": last['high'], "t1": entry - risk*1, "t2": entry - risk*2, "t5": entry - risk*5,
                    "rsi": last['rsi'], "msg": f"SELL {sym} @ {entry:.1f} (Red Close)\nSL {last['high']:.1f} (High)\nT1 {entry-risk*1:.1f} | T2 {entry-risk*2:.1f} | T5 {entry-risk*5:.1f}\nRSI {last['rsi']:.0f} | VWAP DN | Vol {last['volume']/last['vol_avg']:.1f}x"
                }
    except: return None
    return None

# --- MAIN 1 MIN LOOP ---
send_tg(f"🚀 *LIVE BOT STARTED*\n1000 Stocks | 2 Active | 6 Daily | 1 Min Signal\nCond: Breakout+Vol+9x15+VWAP+RSI\nTrailing SL ON")

for loop in range(360): # 6 Hours = 9:15 to 15:30
    active, daily = check_position_pnl()

    if daily['trades'] >= 6:
        send_tg(f"🛑 *DAILY LIMIT 6 DONE* PnL {daily['pnl']:.1f} | Wins {daily['wins']}")
        break

    if len(active) < 2: # फक्त 2 Active
        results = []
        # 1000 ला Batch मध्ये Scan करतो - Rate Limit नको म्हणून
        for i in range(0, len(SYMBOLS), 100):
            batch = SYMBOLS[i:i+100]
            with ThreadPoolExecutor(max_workers=20) as ex:
                futs = [ex.submit(scan_one, s) for s in batch if s in TMap]
                for f in as_completed(futs):
                    r = f.result()
                    if r: results.append(r)
            time.sleep(1) # थोडा Gap

        # नवीन Trade Add कर
        for sig in results[:2-len(active)]:
            if sig['symbol'] in [a['symbol'] for a in active]: continue
            active.append(sig)
            json.dump(active, open(ACTIVE_FILE,'w'))
            send_tg(f"🔔 *NEW {sig['type']} SIGNAL*\n{sig['msg']}\nActive {len(active)}/2 | Daily {daily['trades']}/6 | PnL {daily['pnl']:.1f}")
            if len(active) >= 2: break

    today = datetime.now().strftime("%d-%m %H:%M")
    print(f"{today} Active {len(active)}/2 Daily {daily['trades']}/6 PnL {daily['pnl']:.1f}")
    time.sleep(60) # 1 मिनिट

# Final Report
daily = load_json(DAILY_FILE, {})
send_tg(f"📊 *FINAL DAILY REPORT {daily.get('date')}*\nTrades {daily.get('trades')}/6 | Wins {daily.get('wins')} Loss {daily.get('loss')}\n*PnL {daily.get('pnl',0):.1f} pts*\nActive Left {len(load_json(ACTIVE_FILE,[]))}")
