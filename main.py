import os
import time
import random
import threading
import requests
from flask import Flask

app = Flask(__name__)

# Configuration
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

BARCELONA_LAT = "41.3851"
BARCELONA_LNG = "2.1734"

# Target Matrix
TARGETS = [
    {"kw": "iphone x", "min": 40, "max": 80},
    {"kw": "iphone xr", "min": 40, "max": 90},
    {"kw": "iphone 11", "min": 60, "max": 130},
    {"kw": "iphone 11 pro", "min": 80, "max": 140},
    {"kw": "iphone 12", "min": 90, "max": 150},
    {"kw": "iphone 12 pro", "min": 100, "max": 170},
    {"kw": "iphone 13", "min": 100, "max": 180},
    {"kw": "iphone 13 pro", "min": 140, "max": 280},
    {"kw": "iphone 14", "min": 140, "max": 220},
    {"kw": "iphone 14 pro", "min": 250, "max": 400},
    {"kw": "iphone 15", "min": 240, "max": 375},
    {"kw": "iphone 15 pro", "min": 300, "max": 450},
]

SEEN_ITEMS = set()

def send_telegram_alert(item, target):
    title = item.get("title", "No Title")
    price = item.get("price", "N/A")
    item_id = item.get("id", "")
    web_slug = item.get("web_slug", "")
    
    link = f"https://es.wallapop.com/item/{web_slug}" if web_slug else f"https://es.wallapop.com/item/{item_id}"
    
    message = (
        f"🚨 **BARCELONA DEAL DETECTED**\n\n"
        f"📱 **Item:** {title}\n"
        f"💰 **Price:** €{price} (Target: €{target['min']}-€{target['max']})\n"
        f"📍 **Location:** Barcelona Radius (20km)\n\n"
        f"🔗 [Open Listing in Wallapop]({link})"
    )
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}", flush=True)

def scrape_cycle():
    global SEEN_ITEMS
    
    # Establish persistent session to maintain cookies & headers
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Origin": "https://es.wallapop.com",
        "Referer": "https://es.wallapop.com/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "Sec-Ch-Ua": '"Chromium";v="128", "Not=A?Brand";v="24", "Google Chrome";v="128"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
        "X-DeviceOS": "WEB"
    })

    # Initial session warm-up request
    try:
        session.get("https://es.wallapop.com", timeout=10)
        time.sleep(2)
    except Exception as e:
        print(f"Warm-up ping failed: {e}", flush=True)

    print("--- Starting Initial Cache Seeding ---", flush=True)
    for target in TARGETS:
        kw = target["kw"]
        min_p = target["min"]
        max_p = target["max"]
        
        url = (
            f"https://api.wallapop.com/api/v3/general/search?"
            f"keywords={kw}&latitude={BARCELONA_LAT}&longitude={BARCELONA_LNG}"
            f"&distance_in_km=20&min_sale_price={min_p}&max_sale_price={max_p}"
            f"&category_id=12545&order_by=creation_date"
        )
        
        try:
            res = session.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                items = data.get("search_objects", [])
                print(f"Seeding '{kw}' (€{min_p}-€{max_p}) -> Status: 200 | Items Found: {len(items)}", flush=True)
                for item in items:
                    SEEN_ITEMS.add(item.get("id"))
            else:
                print(f"Seeding '{kw}' -> Status: {res.status_code}", flush=True)
        except Exception as e:
            print(f"Error seeding '{kw}': {e}", flush=True)
            
        time.sleep(random.uniform(2.0, 4.0))

    print("✅ Initial Cache Seeding Complete. Live alert monitoring is now active.", flush=True)

    # Continuous Loop with randomized jitter
    while True:
        time.sleep(10)
        print("--- Starting Full Pass (12 Keywords) ---", flush=True)
        for target in TARGETS:
            kw = target["kw"]
            min_p = target["min"]
            max_p = target["max"]
            
            url = (
                f"https://api.wallapop.com/api/v3/general/search?"
                f"keywords={kw}&latitude={BARCELONA_LAT}&longitude={BARCELONA_LNG}"
                f"&distance_in_km=20&min_sale_price={min_p}&max_sale_price={max_p}"
                f"&category_id=12545&order_by=creation_date"
            )
            
            try:
                res = session.get(url, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    items = data.get("search_objects", [])
                    print(f"Checking '{kw}' (€{min_p}-€{max_p}) -> Status: 200 | Items Found: {len(items)}", flush=True)
                    
                    for item in items:
                        item_id = item.get("id")
                        if item_id and item_id not in SEEN_ITEMS:
                            SEEN_ITEMS.add(item_id)
                            send_telegram_alert(item, target)
                else:
                    print(f"Checking '{kw}' -> Status: {res.status_code}", flush=True)
            except Exception as e:
                print(f"Error checking '{kw}': {e}", flush=True)
                
            time.sleep(random.uniform(2.5, 4.5))

@app.route('/')
def home():
    return "Wallapop Arbitrage Engine is Live", 200

if __name__ == "__main__":
    t = threading.Thread(target=scrape_cycle, daemon=True)
    t.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
