import os, datetime, pytz, requests, pyotp, time
import pandas as pd
from SmartApi import SmartConnect
from concurrent.futures import ThreadPoolExecutor, as_completed

API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PWD = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")
TELE_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELE_CHAT = os.getenv("TELEGRAM_CHAT_ID")

IST = pytz.timezone('Asia/Kolkata')
def ist_now(): return datetime.datetime.now(IST)
def send_tg(m):
    try: requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", json={"chat_id": TELE_CHAT, "text": m, "parse_mode":"Markdown"}, timeout=15)
    except: pass

smart = SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PWD, pyotp.TOTP(TOTP_SECRET).now())

SYMBOLS = ["PGEL","BHEL","SAIL","SUZLON","IRFC","RVNL","IREDA","NHPC","SJVN","HUDCO","IRCON","NBCC","NCC","BEL","BDL","HAL","MAZDOCK","COCHINSHIP","GRSE","OIL","NMDC","TATACHEM","ASHOKLEY","VOLTAS","KEI","APARINDS","FEDERALBNK","BANKINDIA","IDBI","AUROPHARMA","LUPIN","GLENMARK","BIOCON","AARTIIND","BSOFT","CUMMINSIND","ESCORTS","INDHOTEL","BHARATFORG","UNOMINDA","TORNTPOWER","SONACOMS","POLYCAB","COFORGE","BSE","MUTHOOTFIN","PAYTM","VMM","WAAREENER","360ONE","AAVAS","ACE","AFFLE","AMBER","ANGELONE","BEML","BLS","KPITTECH","TATAELXSI","LTTS","CONCOR","PRESTIGE","PHOENIXLTD","SBICARD","IRB","JINDALSTEL","JSL","JSWENERGY","JUBLFOOD","KALYANKJIL","KAYNES","KEC","KFINTECH","M&MFIN","MASTEK","MCX","MEDANTA","NATCOPHARM","NAUKRI","OLECTRA","PEL","PNBHOUSING","RECLTD","SIEMENS","SUNTV","SYNGENE","TRENT","TRIDENT","ZYDUSLIFE","ZOMATO","DELHIVERY","MAPMYINDIA","PNCINFRA","GRINFRA","MTARTECH","CYIENT","TANLA","ROUTE","HAPPSTMNDS","LICI","LODHA","LTF","AUBANK","ADANIGREEN","BANKBARODA","BANDHANBNK","CANBK","CDSL","CGPOWER","CHOLAFIN","DABUR","DLF","DMART","GAIL","GODREJCP","HAVELLS","IDFCFIRSTB","INDIGO","IOC","IRCTC","LALPATHLAB","LAURUSLABS","LTIM","MOTHERSON","MPHASIS","PERSISTENT","PNB","RBLBANK","SRF","TATAPOWER","TITAN","VEDL","DIXON","SAFARI","CAMPUS","INDIAMART","INTELLECT","NETWEB","SYRMA","DATAPATTNS","PARAS","TATATECH","ELECON","HFCL","IEX","JWL","TEXRAIL","RAILTEL","RITES","CESC","MGL","WAAREERTL","VARUNBEV","VBL","DEVYANI","CHALET","VMART","ABFRL","RAYMOND","SOBHA","BRIGADE","ANANTRAJ","KARURVYSYA","CUB","UJJIVAN","FORTIS","KIMS","SULA"]

def calc_rsi(s, p=14):
    d=s.diff(); g=d.where(d>0,0).ewm(alpha=1/p).mean(); l=(-d.where(d<0,0)).ewm(alpha=1/p).mean()
    return 100 - (100/(1+g/l))

def analyze(sym):
    try:
        time.sleep(0.2)
        r=smart.searchScrip("NSE", sym)
        token=r['data'][0]['symboltoken']
        today=ist_now().strftime("%Y-%m-%d")
        hist=smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":f"{today} 09:00","todate":f"{today} 15:30"})
        if not hist or not hist.get('data') or len(hist['data'])<25:
            hist=smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":(ist_now()-datetime.timedelta(days=1)).strftime("%Y-%m-%d 09:00"),"todate":f"{today} 15:30"})
            if not hist or not hist.get('data'): return None
        df=pd.DataFrame(hist['data'], columns=['Time','Open','High','Low','Close','Volume'])
        for c in df.columns[1:]: df[c]=df[c].astype(float)
        df['EMA9']=df['Close'].ewm(span=9).mean()
        df['EMA15']=df['Close'].ewm(span=15).mean()
        df['VWAP']=((df['High']+df['Low']+df['Close'])/3*df['Volume']).cumsum()/df['Volume'].cumsum()
        df['AvgVol']=df['Volume'].rolling(20).mean()
        df['RSI']=calc_rsi(df['Close'])
        c=df.iloc[-1]; p=df.iloc[-2]
        ltp=c['Close']; ema9=c['EMA9']; ema15=c['EMA15']; vwap=c['VWAP']; vol=c['Volume']; avg=c['AvgVol']; rsi=c['RSI']
        if ltp<50 or vol<avg*0.8: return None

        # FRESH CROSS - सकाळी होतो
        fresh_buy = p['EMA9']<=p['EMA15'] and ema9>ema15 and ema9>vwap and ltp>vwap and 50<=rsi<=70
        fresh_sell = p['EMA9']>=p['EMA15'] and ema9<ema15 and ema9<vwap and ltp<vwap and 30<=rsi<=50

        # TRENDING - दुपारी हेच चालतं
        trend_buy = ema9>ema15 and ltp>vwap and ema9>vwap and 55<=rsi<=68 and ltp>ema9
        trend_sell = ema9<ema15 and ltp<vwap and ema9<vwap and 32<=rsi<=48

        if fresh_buy: return (3, rsi, f"🔥 FRESH BUY {sym} @ {ltp:.1f} 9x15 Cross RSI{rsi:.0f} VWAP+{(ltp/vwap-1)*100:.1f}%")
        if trend_buy: return (2, rsi, f"🟢 TREND BUY {sym} @ {ltp:.1f} 9>15 RSI{rsi:.0f} VWAP+{(ltp/vwap-1)*100:.1f}% Vol{int(vol/avg*100)}%")
        if fresh_sell: return (1, -rsi, f"💥 FRESH SELL {sym} @ {ltp:.1f} 9x15 Down RSI{rsi:.0f}")
        if trend_sell: return (0, -rsi, f"🔴 TREND SELL {sym} @ {ltp:.1f} 9<15 RSI{rsi:.0f}")
        return None
    except: return None

res=[]
with ThreadPoolExecutor(max_workers=5) as ex:
    fut={ex.submit(analyze,s):s for s in set(SYMBOLS)}
    for f in as_completed(fut):
        r=f.result()
        if r: res.append(r)

res=sorted(res, key=lambda x: (x[0], x[1]), reverse=True)
now=ist_now().strftime("%d-%b %H:%M")

if res:
    buys=[x[2] for x in res if "BUY" in x[2]][:15]
    sells=[x[2] for x in res if "SELL" in x[2]][:10]
    txt=""
    if buys: txt+= "*BUY (On Spot):*\n" + "\n".join(buys) + "\n\n"
    if sells: txt+= "*SELL:*\n" + "\n".join(sells)
    msg=f"📊 *BSE SmallCap 9/15 + VWAP + RSI {now}*\n{len(set(SYMBOLS))} checked\n\n{txt}"
else:
    msg=f"📊 BSE 1000 SmallCap 9/15 + VWAP + RSI {now}\n168 checked\n\n⏸️ No Fresh Cross - Market Sideways\nपण Trending List साठी Vol filter थोडा कमी केला आहे - पुढच्या Candle ला Signal येईल"

send_tg(msg)
print(msg) 
