import asyncio
from playwright.async_api import async_playwright
import requests
import os
import re

TELEGRAM_BOT_TOKEN = os.environ.get("BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("CHAT_ID")
FB_COOKIES_STR = os.environ.get("FB_COOKIES", "")
SEEN_FILE = "seen_ids.txt"

def get_seen_ids():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(f.read().splitlines())
    return set()

def save_seen_ids(seen_ids):
    with open(SEEN_FILE, "w") as f:
        f.write("\n".join(seen_ids))

def send_telegram(title, price, link):
    msg = f"🔥 **New Carnage Listing Found!**\n\n📌 Title: {title}\n💰 Price: {price}\n\n🔗 Link: {link}"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        print(f"Telegram status: {r.status_code}")
    except Exception as e:
        print(f"Telegram error: {e}")

def parse_cookies(cookie_str):
    cookies = []
    if not cookie_str:
        return cookies
    items = cookie_str.split(";")
    for item in items:
        if "=" in item:
            name, value = item.strip().split("=", 1)
            cookies.append({
                "name": name,
                "value": value,
                "domain": ".facebook.com",
                "path": "/"
            })
    return cookies

async def main():
    seen_ids = get_seen_ids()
    print(f"Loaded {len(seen_ids)} seen IDs.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )

        fb_cookies = parse_cookies(FB_COOKIES_STR)
        if fb_cookies:
            await context.add_cookies(fb_cookies)
            print("Successfully injected FB Session Cookies!")
        else:
            print("Warning: FB_COOKIES secret not found or empty.")

        page = await context.new_page()
        
        url = "https://www.facebook.com/marketplace/search/?query=carnage"
        print(f"Navigating directly to {url}...")
        
        # Fixed timeout issue by using domcontentloaded instead of networkidle
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)

        # Scroll to load listings
        await page.evaluate("window.scrollBy(0, 1000);")
        await page.wait_for_timeout(4000)

        links = await page.query_selector_all('a[href*="/marketplace/item/"]')
        print(f"Found {len(links)} item links on Facebook Marketplace!")

        new_found = False
        
        for link_elem in links[:15]:
            href = await link_elem.get_attribute('href')
            if href:
                match = re.search(r'/item/(\d+)', href)
                if match:
                    item_id = match.group(1)
                    full_link = f"https://www.facebook.com/marketplace/item/{item_id}/"
                    
                    if item_id not in seen_ids:
                        text = await link_elem.inner_text()
                        lines = [l.strip() for l in text.split('\n') if l.strip()]
                        
                        price = lines[0] if len(lines) > 0 else "N/A"
                        title = lines[1] if len(lines) > 1 else "Carnage Item"
                        
                        print(f"New Item Detected: {title} ({price})")
                        send_telegram(title, price, full_link)
                        seen_ids.add(item_id)
                        new_found = True

        if new_found:
            save_seen_ids(seen_ids)
            print("Saved new IDs to seen_ids.txt.")
        else:
            print("No new items found.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
