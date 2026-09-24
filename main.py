import os
import time
import json
import random
import threading
from flask import Flask
from playwright.sync_api import sync_playwright
import requests

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

BARCELONA_LAT = 41.3851
BARCELONA_LNG = 2.1734

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

seen_item_ids = set()

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def send_telegram_alert(title, price, item_url, location):
    message = (
        f"🚨 **BARCELONA DEAL DETECTED**\n\n"
        f"📱 **Item:** {title}\n"
        f"💰 **Price:** €{price}\n"
        f"📍 **Location:** {location}\n\n"
        f"🔗 [Open Listing in Wallapop]({item_url})"
    )
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json=payload, timeout=5)
    except Exception as e:
        log(f"Failed to send Telegram alert: {e}")

def run_playwright_scraper():
    global seen_item_ids
    is_seeded = False

    with sync_playwright() as p:
        # Launch browser with stealth-like arguments
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
            ]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800},
            locale="es-ES",
            geolocation={"latitude": BARCELONA_LAT, "longitude": BARCELONA_LNG},
            permissions=["geolocation"]
        )

        page = context.new_page()

        log("--- Playwright Browser Engine Initialized ---")

        while True:
            for target in TARGETS:
                kw = target["kw"]
                min_p = target["min"]
                max_p = target["max"]

                # Intercept JSON network responses triggered by browser navigation
                latest_items = []

                def handle_response(response):
                    nonlocal latest_items
                    if "/api/v3/general/search" in response.url and response.status == 200:
                        try:
                            data = response.json()
                            items = data.get("search_objects", [])
                            if items:
                                latest_items = items
                        except Exception:
                            pass

                # Attach listener
                page.on("response", handle_response)

                search_url = (
                    f"https://es.wallapop.com/app/search?"
                    f"keywords={kw.replace(' ', '%20')}&"
                    f"min_sale_price={min_p}&"
                    f"max_sale_price={max_p}&"
                    f"latitude={BARCELONA_LAT}&"
                    f"longitude={BARCELONA_LNG}&"
                    f"order_by=creation_date"
                )

                try:
                    log(f"Browsing: '{kw}' (€{min_p}-€{max_p})")
                    page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                    
                    # Short wait for network requests triggered by page hydration
                    time.sleep(3.5)

                    if latest_items:
                        log(f"Intercepted {len(latest_items)} live items for '{kw}'")
                        for item in latest_items[:5]:
                            item_id = item.get("id")
                            if item_id and item_id not in seen_item_ids:
                                title = item.get("title", "No Title")
                                price = item.get("price", "N/A")
                                web_path = item.get("web_slug", "")
                                item_url = f"https://es.wallapop.com/item/{web_path}" if web_path else "https://es.wallapop.com"
                                location = item.get("location", {}).get("city", "Barcelona")

                                if is_seeded:
                                    log(f"🔥 NEW DEAL FOUND: {title} (€{price})")
                                    send_telegram_alert(title, price, item_url, location)
                                else:
                                    log(f"🌱 [Seeding Cache] Recorded: {item_id} ({title})")

                                seen_item_ids.add(item_id)
                    else:
                        log(f"⚠️ No API response intercepted for '{kw}' (possible anti-bot prompt or empty page)")

                except Exception as e:
                    log(f"Error visiting '{kw}': {e}")
                finally:
                    # Clean up event listener for the next target
                    page.remove_listener("response", handle_response)

                # Avoid aggressive polling
                time.sleep(random.uniform(4.0, 7.0))

            if not is_seeded:
                is_seeded = True
                log("✅ Cache seeding complete. Live alert monitoring is now active.")

            time.sleep(15)

@app.route('/')
def home():
    return "Wallapop Playwright Scraper Engine Active", 200

if __name__ == "__main__":
    t = threading.Thread(target=run_playwright_scraper, daemon=True)
    t.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
