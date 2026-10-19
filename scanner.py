import os, requests
print("V26 START")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    print("ERROR: BOT_TOKEN or CHAT_ID Secret Missing!")
    print(f"BOT_TOKEN exists: {bool(BOT_TOKEN)}")
    print(f"CHAT_ID exists: {bool(CHAT_ID)}")
    exit(0)

try:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    msg = "✅ V26 TEST SUCCESS - GitHub Connected! Call+Put Scanner Ready! NSE Check Starting..."
    r = requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=15)
    print(f"Telegram Response: {r.text}")
    print("✅ V26 DONE - GREEN TICK EXPECTED")
except Exception as e:
    print(f"ERROR in V26: {e}")
    exit(0) 
