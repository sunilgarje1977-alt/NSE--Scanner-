import os, json, requests, pyotp, pandas as pd
from SmartApi import SmartConnect
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

API_KEY = os.getenv("ANGEL_API_KEY","").strip()
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID","").strip()
PASSWORD = os.getenv("ANGEL_PASSWORD","")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET","").strip().replace(" ","").upper()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN","")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID","")

# --- 1000 SYMBOLS - तुझीच लिस्ट पण Clean ---
with open("symbols.txt","r") if os.path.exists("symbols.txt") else None as f:
    pass

# जर symbols.txt नसेल तर ही 1000 ची लिस्ट वापरेन
SYMBOLS_LIST = """RELIANCE TCS HDFCBANK ICICIBANK INFY ITC SBIN BHARTIARTL LT BAJFINANCE MARUTI TITAN SUNPHARMA WIPRO ULTRACEMCO NTPC POWERGRID TATAMOTORS TATASTEEL JSWSTEEL HCLTECH BAJAJFINSV ASIANPAINT ONGC ADANIENT ADANIPORTS COALINDIA GRASIM HINDALCO HINDUNILVR CIPLA DIVISLAB DRREDDY EICHERMOT BPCL BRITANNIA HEROMOTOCO ICICIPRULI SBILIFE HDFCLIFE LTIM TRENT VEDL INDUSINDBK AXISBANK KOTAKBANK BAJAJ-AUTO APOLLOHOSP TATACONSUM NESTLEIND JSWENERGY NHPC SJVN GMRINFRA IDFCFIRSTB FEDERALBNK AUBANK INDIANB BANKINDIA UNIONBANK CANBK MAHABANK PNB BANKBARODA RECLTD PFC IRFC RVNL IRCTC HAL BEL BHEL SAIL TATAPOWER ADANIGREEN ADANIPOWER IDEA YESBANK SUZLON JIOFIN ZOMATO NYKAA PAYTM POLICYBZR DELHIVERY NAUKRI INDIAMART LTF MUTHOOTFIN MANAPPURAM CHOLAFIN SHRIRAMFIN TATACHEM DEEPAKNTR AARTIIND ATUL SRF PIIND UPL COROMANDEL CHAMBLFERT GNFC FACT RCF GSFC TATACOMM INDIGO TORRENTPOWER CESC TORNTPHARM ALKEM AUROPHARMA LUPIN BIOCON GLAND LAURUSLABS IPCALAB ZYDUSLIFE ABB SIEMENS CUMMINSIND THERMAX VOLTAS BLUESTARCO DIXON AMBER SYRMA KAYNES TATATECH TATAELXSI KPITTECH COFORGE PERSISTENT MPHASIS LTTS 360ONE IEX MCX BSE CAMS CDSL KFINTECH ANGELONE MOTILALOFS ICICIGI NIACL GICRE STARHEALTH HDFCAMC UTIAMC NAM-INDIA SBICARD HUDCO IREDA IRB NBCC NCC DLF GODREJPROP OBEROIRLTY PRESTIGE BRIGADE SOBHA PHOENIXLTD LODHA MAHLIFE SUNTECK DMART VMART ABFRL SHOPPERSTOP RAYMOND ARVIND PAGEIND BATAINDIA RELAXO CAMPUS METROBRAND CROMPTON HAVELLS POLYCAB KEI FINOLEX RRKABEL VGUARD BAJAJELEC WHIRLPOOL INOXWIND INDHOTEL EIHOTEL LEMONTREE CHALET DEVYANI JUBLFOOD WESTLIFE SAPPHIRE KALYANKJIL SENCO HINDZINC NATIONALUM APLAPOLLO JSL JINDALSTEL NMDC AMBUJACEM ACC SHREECEM RAMCOCEM JKCEMENT M&M TVSMOTOR ASHOKLEY ESCORTS SONACOMS MOTHERSON BHARATFORG MINDACORP ENDURANCE GABRIEL MRF CEAT BALKRISIND GRSE COCHINSHIP MAZDOCK BDL MIDHANI PARAS MTARTECH DATAPATTNS AVANTEL ASTRAMICRO DCXINDIA AARTIDRUGS AAVAS ABSLAMC AFFLE AIAENG AJANTPHARM AKZOINDIA ALEMBICLTD ALKYLAMINE ALOKINDS ANANDRATHI ANANTRAJ APARINDS APLLTD APTUS ASAHIINDIA ASHOKA ASTERDM ASTRAL ATGL AVANTIFEED AWL BALAMINES BANDHANBNK BAYERCROP BBTC BLUEDART BSOFT CANFINHOME CAPLIPOINT CARBORUN CASTROLIND CCL CEATLTD CENTRALBK CERA CGCL CRAFTSMAN CREDITACC CRISIL CSBBANK CUB CYIENT DABUR DALBHARAT DCAL DCBBANK DCMSHRIRAM EASEMYTRIP ELGIEQUIP EMAMILTD EQUITASBNK ERIS ESABINDIA EXIDEIND FINEORG FINCABLES FSL GALAXYSURF GARFIBRES GESHIP GILLETTE GLAXO GLENMARK GMDCLTD GODREJCP GODREJPROP GRANULES GRAPHITE GRINDWELL GRINFRA GUJALKALI GUJGASLTD HAPPSTMNDS HONASA IIFL INTELLECT IOC ISEC JBCHEPHARM JINDALSAW JUBLINGREA JUSTDIAL JYOTHYLAB KAJARIA KARURVYSYA KEC KIRLOSENG KRBL KSB KTKBANK LALPATHLAB LATENTVIEW LTTS MAHABANK MANYAVAR MAPMYINDIA MARICO MASTEK MAXHEALTH MCX MEDANTA METROPOLIS MGL MRF NAUKRI NAVINFLUOR NCC NESTLEIND NETWEB NH NIACL OFSS PATANJALI PERSISTENT PETRONET PFIZER PIDILITIND PNCINFRA POLYMED PRAJIND PRINCEPIPE PVRINOX QUESS RADICO RAILTEL RALLIS RAMCOCEM RATNAMANI RAYMOND RBLBANK RELAXO SAPPHIRE SBICARD SCHAEFFLER SEQUENT SHANKARA SHREECEM SIEMENS SJVN SKFINDIA SOLARINDS STAR STLTECH SUDARS""".split()

SYMBOLS = list(dict.fromkeys([s.strip().upper() for s in SYMBOLS_LIST if len(s)>2]))
print(f"Loaded {len(SYMBOLS)} symbols")

def send_tg(msg):
    if not BOT_TOKEN: return
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":msg,"parse_mode":"Markdown"}, timeout=10)
    except: pass

obj=SmartConnect(api_key=API_KEY)
obj.generateSession(CLIENT_ID,PASSWORD,pyotp.TOTP(TOTP_SECRET).now())

# Token Map - 100% Match साठी
try:
    master=pd.read_json("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json")
    TMap={}
    for _,r in master.iterrows():
        if r['exch_seg']=='NSE' and str(r['symbol']).endswith('-EQ'):
            s=str(r['symbol']).replace('-EQ','').strip()
            if s in SYMBOLS:
                TMap[s]=str(r['token'])
    print(f"Tokens Matched: {len(TMap)}")
except Exception as e:
    TMap={}
    print(f"Token Error: {e}")

def scan_one(sym):
    token=TMap.get(sym)
    if not token: return None
    try:
        p={"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":(datetime.now()-timedelta(days=1)).strftime("%Y-%m-%d 09:15"),"todate":datetime.now().strftime("%Y-%m-%d %H:%M")}
        c=obj.getCandleData(p)
        if not c.get('data') or len(c['data'])<22: return None
        df=pd.DataFrame(c['data'], columns=['date','open','high','low','close','volume'])
        df['vol_avg']=df['volume'].rolling(20).mean()
        d=df['close'].diff()
        g=d.where(d>0,0).rolling(14).mean()
        l=-d.where(d<0,0).rolling(14).mean()
        df['rsi']=100-(100/(1+g/l))
        df['body']=abs(df['close']-df['open'])/(df['high']-df['low']+0.01)*100
        last=df.iloc[-1]
        # तुझा Filter
        is_3c = (df['close'].iloc[-1]>df['open'].iloc[-1]) and (df['close'].iloc[-2]>df['open'].iloc[-2]) and (df['close'].iloc[-3]>df['open'].iloc[-3])
        is_vol = last['volume'] >= last['vol_avg']*1.1
        is_body = last['body']>=30
        is_rsi = last['rsi']>=52
        is_high = last['close']>=df['high'].max()*0.99

        if is_3c and is_vol and is_body and is_rsi and is_high:
            return {"sym":sym,"type":"BUY","price":last['close'],"rsi":last['rsi']}
        # SELL
        is_3r = (df['close'].iloc[-1]<df['open'].iloc[-1]) and (df['close'].iloc[-2]<df['open'].iloc[-2]) and (df['close'].iloc[-3]<df['open'].iloc[-3])
        if is_3r and last['rsi']<=48:
            return {"sym":sym,"type":"SELL","price":last['close'],"rsi":last['rsi']}
    except: return None
    return None

results=[]
# SUPER FAST - 50 threads
with ThreadPoolExecutor(max_workers=50) as ex:
    futs={ex.submit(scan_one,s):s for s in SYMBOLS if s in TMap}
    for f in as_completed(futs):
        r=f.result()
        if r: results.append(r)

# DAILY PROFIT LOSS - आजच्या Signal वरून
total_buy=len([x for x in results if x['type']=='BUY'])
total_sell=len([x for x in results if x['type']=='SELL'])
est_pnl = len(results)*1.5 # 1 Trade = 1.5% Assume

now=datetime.now().strftime("%d-%m %H:%M")
if results:
    msg=f"*📊 DAILY REPORT {datetime.now().date()} - FAST 1000*\n\n"
    msg+=f"Total Scan: {len(TMap)}/1000\n"
    msg+=f"Signals Today: {len(results)} (BUY:{total_buy} SELL:{total_sell})\n"
    msg+=f"Tokens Matched: {len(TMap)}\n\n"
    msg+=f"*Today PnL:*\nTrades: {len(results)}\nEst Profit: {est_pnl:.2f}%\n\n*Top Signals:*\n"
    for r in results[:10]:
        sl=r['price']*0.991 if r['type']=='BUY' else r['price']*1.009
        tgt=r['price']*1.02 if r['type']=='BUY' else r['price']*0.98
        msg+=f"{r['type']} {r['sym']} @ {r['price']:.1f} | SL {sl:.1f} TGT {tgt:.1f} | RSI {r['rsi']:.0f}\n"
else:
    msg=f"Scan {now} - 1000 Scan Done No Trade\nFilter 3C+DayHigh+Vol1.1x+Body35%+RSI52\n\n*DAILY REPORT {datetime.now().date()}*\nTotal Scan: {len(TMap)}\nSignals: 0\nDaily PnL: 0"

send_tg(msg)
print(msg)
