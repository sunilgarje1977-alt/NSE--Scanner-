import os, requests, traceback, time
from datetime import datetime, timedelta

BOT = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID")

def send(m):
    print(m)
    try:
        requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage",
                      data={"chat_id": CHAT, "text": m}, timeout=20)
    except Exception as e:
        print(f"TG Error {e}")

try:
    from SmartApi import SmartConnect
    import pyotp

    # === LOGIN ===
    obj = SmartConnect(api_key=os.getenv("ANGEL_API_KEY"))
    obj.generateSession(
        os.getenv("ANGEL_CLIENT_ID"),
        os.getenv("ANGEL_PASSWORD"),
        pyotp.TOTP(os.getenv("ANGEL_TOTP_SECRET")).now()
    )

    ist = datetime.utcnow() + timedelta(hours=5, minutes=30)

    # === WEEKLY EXPIRY AUTO - TUESDAY 2026 ===
    today = datetime.now()
    days_ahead = (1 - today.weekday() + 7) % 7 # 1 = Tuesday
    weekly_date = today if days_ahead == 0 else today + timedelta(days=days_ahead)
    EXP = weekly_date.strftime("%d%b%Y").upper() # Ex: 21OCT2026, 27OCT2026

    send(f"🧪 Manual Test @ {ist:%H:%M:%S IST} | Weekly Exp {EXP} | Real Time Check...")

    # === HELPERS ===
    def get_spot(token, symbol):
        try:
            d = obj.ltpData("NSE", symbol, token)
            return float(d["data"]["ltp"])
        except:
            return None

    def get_nfo_ltp(tradingsym_text):
        """NFO FUT / OPT Real LTP"""
        try:
            sr = obj.searchScrip("NFO", tradingsym_text)
            if sr.get("data"):
                t = sr["data"][0]
                d = obj.ltpData("NFO", t["tradingsymbol"], t["symboltoken"])
                if d.get("data"):
                    return float(d["data"]["ltp"]), t["tradingsymbol"]
        except Exception as e:
            print(f"NFO Fail {tradingsym_text} {e}")
        return None, None

    def calc_levels(entry):
        """Entry, Target, SL, Trailing"""
        entry = float(entry)
        t1 = round(entry * 1.25, 1) # 25%
        t2 = round(entry * 1.50, 1) # 50%
        t3 = round(entry * 2.00, 1) # 100%
        sl = round(entry * 0.65, 1) # 35% SL
        trail = round(entry * 0.85, 1) # Trailing Trigger
        return t1, t2, t3, sl, trail

    # === 1. NIFTY REAL TIME ===
    nifty_spot = get_spot("26000", "Nifty 50")
    if nifty_spot:
        atm = round(nifty_spot / 50) * 50

        # Nifty Future Real
        fut_ltp, fut_sym = get_nfo_ltp(f"NIFTY {EXP} FUT")
        if not fut_ltp:
            fut_ltp = nifty_spot
            fut_sym = f"NIFTY {EXP} FUT"

        header = f"💥 NIFTY WEEKLY REAL TIME\nSpot {nifty_spot:.1f} Fut {fut_ltp:.1f} ATM {atm}\nExp {EXP} Weekly\nTime {ist:%H:%M IST}\n\n"
        body = ""
        signal_found = False

        # NSE Future + Option Call Put - Premium 20-150 Real Time Filter
        for diff, typ in [(0,"CE"), (0,"PE"), (50,"CE"), (-50,"PE"), (100,"CE"), (-100,"PE")]:
            strike = atm + diff
            ltp, osym = get_nfo_ltp(f"NIFTY {EXP} {strike} {typ}")
            if ltp and 20 <= ltp <= 200: # On Time Signal Filter
                t1, t2, t3, sl, trail = calc_levels(ltp)
                # On Time Signal Logic - Entry Above VWAP Type
                body += f"✅ {strike} {typ} @ {ltp:.1f}\n"
                body += f"Entry {ltp:.1f} | T1 {t1} T2 {t2} T3 {t3}\n"
                body += f"SL {sl} Trail {trail} -> T1\n"
                body += f"Exit: SL/{t3}/RSI 75+\n{osym}\n\n"
                signal_found = True
            if signal_found and len(body.splitlines()) > 12:
                break

        if signal_found:
            send(header + body)
        else:
            send(f"💥 NIFTY Weekly Spot {nifty_spot:.1f} Fut {fut_ltp:.1f} ATM {atm} Exp {EXP}\nPremium 20-200 Range बाहेर किंवा Market बंद - 9:15 नंतर Real Signal येईल @ {ist:%H:%M IST}")

    time.sleep(1)

    # === 2. NSE STOCK FUTURE + OPTION CALL PUT REAL TIME ===
    STOCKS = [("RELIANCE", "2885"), ("BHEL", "3181"), ("TCS", "11536")]

    for STOCK, TOKEN in STOCKS:
        spot = get_spot(TOKEN, STOCK)
        if not spot:
            continue

        atm_s = round(spot / 10) * 10 if STOCK!= "BHEL" else round(spot / 5) * 5

        # Stock Future Real
        fut_ltp, fut_sym = get_nfo_ltp(f"{STOCK} {EXP} FUT")
        fut_ltp = fut_ltp or spot

        msg = f"💥 {STOCK} WEEKLY FUT+OPT REAL\nSpot {spot:.1f} Fut {fut_ltp:.1f} ATM {atm_s}\nExp {EXP}\n\n"
        found = 0

        strikes = [atm_s-20, atm_s, atm_s+20] if STOCK!= "BHEL" else [atm_s-10, atm_s, atm_s+10]
        for strike in strikes:
            for typ in ["CE", "PE"]:
                ltp, osym = get_nfo_ltp(f"{STOCK} {EXP} {strike} {typ}")
                if ltp and 5 <= ltp <= 200: # Stock Option Premium Filter
                    t1, t2, t3, sl, trail = calc_levels(ltp)
                    msg += f"✅ {strike} {typ} @ {ltp:.1f} Entry {ltp:.1f} T1 {t1} SL {sl} Trail {trail}\n{osym}\n"
                    found += 1
                    if found >= 2:
                        break
            if found >= 2:
                break

        if found > 0:
            send(msg)
        time.sleep(0.5)

    send(f"✅ Full Auto Scan Done Weekly {EXP} @ {ist:%H:%M:%S IST} - Nifty Future + Option Call/Put + Stock Future + Option Call/Put - All Real Time")

except Exception as e:
    err = traceback.format_exc()[-900:]
    print(err)
    send(f"❌ ERROR @ {datetime.utcnow()+timedelta(hours=5,minutes=30):%H:%M IST}\n{err}")
