import json, os, requests
def clean(s): return os.getenv(s,"").strip()
def send_tg(m):
    url=f"https://api.telegram.org/bot{clean('TELEGRAM_BOT_TOKEN')}/sendMessage"
    requests.post(url, json={"chat_id": clean('TELEGRAM_CHAT_ID'), "text": m, "parse_mode":"Markdown"}, timeout=15)
try:
    with open("trades_state.json",'r') as f: state=json.load(f)
except:
    send_tg("📊 आज No Trades"); exit()
trades=state.get("trades",[]); pnl=0; w=0; l=0; a=0; txt=""
for t in trades:
    p=t.get("pnl",0)
    if t["status"]=="CLOSED":
        if p>0: w+=1
        else: l+=1
        pnl+=p
        txt+=f"{'✅' if p>0 else '❌'} {t['symbol']} {p:+.1f}\n"
    else:
        a+=1; txt+=f"⏳ {t['symbol']} @ {t['entry']:.1f}\n"
send_tg(f"📊 *P&L {state.get('date')}*\n\n{txt}\nT:{len(trades)}/6 W:{w} L:{l} A:{a}\n💰 *Net {pnl:+.1f} pts*")
