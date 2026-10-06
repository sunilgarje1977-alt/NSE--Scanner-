import os, requests, pyotp, time
import pandas as pd
from SmartApi import SmartConnect
from datetime import datetime, timedelta

API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PASSWORD = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")

obj = SmartConnect(api_key=API_KEY)
clean = TOTP_SECRET.strip().replace(" ","").upper()
obj.generateSession(CLIENT_ID, PASSWORD, pyotp.TOTP(clean).now())

master = requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json", timeout=30).json()
token_map = {d['symbol'].replace('-EQ',''): d['token'] for d in master if d.get('exch_seg')=='NSE' and str(d.get('symbol','')).endswith('-EQ')}

RAW_LIST = ["360ONE","AADHARHFC","AAVAS","ABSLAMC","AEGISLOG","AFFLE","AARTIIND","ABFRL","ADANIGREEN","ADANIPOWER","AJANTPHARM","AKZOINDIA","ALEMBICLTD","ALKYLAMINE","AMBER","ANANDRATHI","ANGELONE","ANURAS","APARINDS","APLAPOLLO","APLLTD","APTUS","ARCHEAN","ASAHIINDIA","ASTERDM","ASTRAL","ATUL","AUBANK","AVANTIFEED","AVANTEL","BALAMINES","BALKRISIND","BALRAMCHIN","BANDHANBNK","BANKINDIA","BATAINDIA","BAYERCROP","BDL","BEML","BHEL","BIKAJI","BIOCON","BIRLACORPN","BLUEDART","BLUESTARCO","BSE","CAMS","CAMPUS","CAPLIPOINT","CARBORUNIV","CARTRADE","CASTROLIND","CCL","CEAT","CENTRALBK","CERA","CESC","CGCL","CHALET","CHAMBLFERT","CHEMPLASTS","CHENNPETRO","CHOICEIN","CHOLAFIN","CLEAN","COCHINSHIP","COFORGE","CRAFTSMAN","CREDITACC","CROMPTON","CSBBANK","CUB","CUPID","CYIENT","DATAPATTNS","DBCORP","DCBBANK","DEEPAKFERT","DEEPAKNTR","DELTACORP","DEVYANI","EASEMYTRIP","EDELWEISS","EICHERMOT","ELECON","ELGIEQUIP","EMBASSYDEV","ENDURANCE","EQUITASBNK","ERIS","EXIDEIND","FDC","FEDERALBNK","FINEORG","FSL","GABRIEL","GARFIBRES","GESHIP","GHCL","GLENMARK","GMRINFRA","GNFC","GODREJPROP","GRANULES","GRAPHITE","GRINDWELL","GRSE","GSFC","GSPL","GULFOILLUB","HAPPSTMNDS","HFCL","HINDCOPPER","HOMEFIRST","HONASA","HUDCO","IEX","IDBI","IDFCFIRSTB","IIFL","INDIACEM","INDIAMART","INDIANB","INDIGO","INDOCO","INDUSINDBK","INTELLECT","IOB","IPCALAB","IRCON","IRFC","JBCHEPHARM","JINDALSTEL","JUBLINGREA","JUBLFOOD","JUSTDIAL","JYOTHYLAB","KAJARIACER","KALYANKJIL","KARURVYSYA","KEC","KEI","KFINTECH","KPITTECH","KRBL","KPRMILL","KIMS","LATENTVIEW","LAURUSLABS","LEMONTREE","LTF","MANAPPURAM","MANYAVAR","MASTEK","MAXHEALTH","MCX","MEDANTA","METROPOLIS","MFSL","MOTHERSON","MOIL","MRPL","MUTHOOTFIN","NAM-INDIA","NATIONALUM","NAUKRI","NBCC","NCC","NH","NHPC","NMDC","NOCIL","NUVAMA","OBEROIRLTY","OLECTRA","ONWARDTEC","PEL","PERSISTENT","PETRONET","PFIZER","PHOENIXLTD","PNBHOUSING","PNCINFRA","POLYCAB","POLYMED","PRAJIND","PRESTIGE","PVRINOX","QUESS","RADICO","RAIN","RAILTEL","RALLIS","RBLBANK","REDINGTON","RITES","ROUTE","RVNL","SAIL","SAPPHIRE","SBICARD","SBFC","SOBHA","SONACOMS","SOUTHBANK","STLTECH","SUZLON","SYNGENE","TATACHEM","TATACOMM","TEJASNET","THOMASCOOK","TITAGARH","TRIDENT","TVSMOTOR","UJJIVANSFB","UNOMINDA","VOLTAS","WELCORP","YESBANK","ZEEL","ZENSARTECH","ZYDUSLIFE","BLS","DELHIVERY","DMART","FIVESTAR","GLAND","GRINFRA","LICHSGFIN","METROBRAND","NAZARA","NYKAA","POONAWALLA","TATATECH","UTIAMC","VIJAYA","ZOMATO","ANANTRAJ","ASHOKA","BAJAJHIND","BALMLAWRIE","CIGNITITEC","DCAL","DHANI","ECLERX","EIDPARRY","ENGINERSIN","EQUITAS","ESABINDIA","GMDCLTD","GODREJAGRO","GPPL","HATSUN","HEG","HINDOILEXP","HLEGLAS","IFCI","IOLCP","ITDC","JINDALSAW","JKLAKSHMI","JKTYRE","KAYNES","KIRLOSENG","KSB","KSL","LLOYDSME","LUMAXTECH","MAYURUNIQ","MMTC","NESCO","NLCINDIA","PFOCUS","PRAKASH","RENUKA","SAREGAMA","SHOPERSTOP","SOUTHWEST","SUNFLAG","TATAMETALI","TATVA","TIINDIA","TRITURBINE","UCOBANK","UFLEX","VGUARD","WELSPUNLIV","ZENTEC","AAREYDRUGS","ADFFOODS","ADL","AHLADA","AHLUCONT","AIAENG","AJMERA","ALICON","ALKALI","ALOKINDS","AMBIKA","ANDHRSUGAR","ANUP","APCOTEX","APOLLOPIPE","ARVIND","ARVINDFASN","ASHIANA","ASTEC","ATULAUTO","AURIONPRO","AVTNPL","BAGFILMS","BANARISUG","BANCOINDIA","BASF","BBL","BBOX","BCG","BFINVEST","BGRENERGY","BHAGCHEM","BHARATWIRE","BIGBLOC","BIRLACABLE","BLKASHYAP","BOMDYEING","BORORENEW","BUTTERFLY","CAMLINFINE","CANTABIL","CAPACITE","CDSL","CENTURYPLY","CHOLAFIN","DAMODARIND","DBL","DCMSHRIRAM","DHANUKA","DLINKINDIA","DODLA","DPSCLTD","DYNAMATECH","EIDPARRY","EMKAY","ENDURANCE","EQUITASBNK","ERIS","ESTER","FCL","GALAXYSURF","GICRE","GIPCL","GPIL","HATHWAY","HIKAL","HMT","HSCL","HUHTAMAKI","IFBAGRO","JMA","JSL","JSLHISAR","KANSAINER","KOLTEPATIL","KTKBANK","LAOPALA","LGBBROSLTD","LUMAXIND","LUXIND","MAHABANK","MAHLOG","MINDACORP","MOLDTECH","OAL"]

STOCKS = list(dict.fromkeys(RAW_LIST))
print(f"Total Smallcap 400 Loaded: {len(RAW_LIST)}")
print(f"After dedup: {len(STOCKS)}")
print(f"Starting 60 Days Backtest for {len(STOCKS)} stocks...")

# --- BACKTEST LOGIC ---
trades = []
start_date = datetime.now() - timedelta(days=60)

for sym in STOCKS:
    token = token_map.get(sym)
    if not token: continue
    try:
        params = {"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":start_date.strftime("%Y-%m-%d %H:%M"),"todate":datetime.now().strftime("%Y-%m-%d %H:%M")}
        data = obj.getCandleData(params)
        if not data.get('data') or len(data['data']) < 100: continue
        df = pd.DataFrame(data['data'], columns=['ts','o','h','l','c','v'])
        df['ema9'] = df['c'].ewm(span=9).mean()
        df['ema15'] = df['c'].ewm(span=15).mean()
        df['vol20'] = df['v'].rolling(20).mean()
        df['vwap'] = (df['c']*df['v']).cumsum()/df['v'].cumsum()

        for i in range(20, len(df)-3):
            if df.iloc[i]['c'] < 50: continue
            if df.iloc[i]['v'] < 20000: continue
            if df.iloc[i]['vol20']==0 or df.iloc[i]['v'] < df.iloc[i]['vol20']*1.8: continue
            # LONG
            if df.iloc[i-1]['ema9'] < df.iloc[i-1]['ema15'] and df.iloc[i]['ema9'] > df.iloc[i]['ema15'] and df.iloc[i]['c'] > df.iloc[i]['vwap']:
                entry = df.iloc[i]['c']
                sl = df.iloc[i]['vwap']*0.997
                # check next 3 candles for target 0.8% or SL
                for j in range(1,4):
                    if df.iloc[i+j]['l'] <= sl: trades.append(-0.3); break
                    if df.iloc[i+j]['h'] >= entry*1.008: trades.append(0.8); break
                else: trades.append(0.1)
            # SHORT
            if df.iloc[i-1]['ema9'] > df.iloc[i-1]['ema15'] and df.iloc[i]['ema9'] < df.iloc[i]['ema15'] and df.iloc[i]['c'] < df.iloc[i]['vwap']:
                entry = df.iloc[i]['c']
                sl = df.iloc[i]['vwap']*1.003
                for j in range(1,4):
                    if df.iloc[i+j]['h'] >= sl: trades.append(-0.3); break
                    if df.iloc[i+j]['l'] <= entry*0.992: trades.append(0.8); break
                else: trades.append(0.1)
        time.sleep(0.1)
    except Exception as e:
        continue

if trades:
    win = len([t for t in trades if t>0])
    print(f"Total Trades: {len(trades)}")
    print(f"Win Trades: {win} ({win/len(trades)*100:.1f}%)")
    print(f"Avg Profit per Trade: {sum(trades)/len(trades):.3f}%")
    print(f"Total Profit 60 Days: {sum(trades):.2f}%")
else:
    print("No Trades Found - Check Filters") 
