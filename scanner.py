import os, time, pyotp, requests
from SmartApi import SmartConnect

# --- 1. TOTP FIX (32 character) ---
def get_clean_totp():
    secret = os.getenv("ANGEL_TOTP_SECRET", "")
    # सगळे space, \n काढून टाकतो
    clean_secret = secret.replace(" ", "").replace("\n", "").replace("\r", "").strip()
    print(f"TOTP len after clean: {len(clean_secret)}")
    if len(clean_secret) != 32:
        print(f"ERROR: TOTP Secret 32 चा पाहिजे, तुझा {len(clean_secret)} आहे!")
        print("Angel App मधून परत Secret घे")
    return pyotp.TOTP(clean_secret).now()

# --- 2. TELEGRAM FUNCTION ---
def send_telegram(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Telegram Token/Chat ID नाहीये")
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        r = requests.post(url, data=payload, timeout=10)
        print(f"Telegram Response: {r.text}")
    except Exception as e:
        print(f"Telegram Failed: {e}")

# --- 3. MAIN SCANNER ---
try:
    api_key = os.getenv("ANGEL_API_KEY")
    client_id = os.getenv("ANGEL_CLIENT_ID")
    password = os.getenv("ANGEL_PASSWORD")
    
    obj = SmartConnect(api_key=api_key)
    totp = get_clean_totp()
    data = obj.generateSession(client_id, password, totp)
    print("Login Success:", data['status'])

    # तुझा 1000 Stocks चा Logic इथे...
    # उदाहरण:
    matches = [] # इथे तुझे breakout stocks येतील
    
    # --- 4. नेहमी Telegram पाठव (0 Match असेल तरी) ---
    if len(matches) == 0:
        msg = f"📊 *NSE 1000 Scan Done*\n\n⏰ Time: {time.strftime('%d-%m %H:%M')}\n❌ *0 Match Found*\nMarket मध्ये आज Breakout नाही."
        send_telegram(msg)
    else:
        msg = f"🚀 *Breakout Found: {len(matches)}*\n\n" + "\n".join(matches)
        send_telegram(msg)

except Exception as e:
    print(f"Error: {e}")
    send_telegram(f"⚠️ Scanner Error: {e}\nTOTP Len Check करा") 
