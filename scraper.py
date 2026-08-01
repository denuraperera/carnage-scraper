import asyncio
from playwright.async_api import async_playwright
import requests
import os
import re

TELEGRAM_BOT_TOKEN = os.environ.get("BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("CHAT_ID")
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
        print(f"Telegram response: {r.status_code}")
    except Exception as e:
        print(f"Telegram error: {e}")

async def main():
    seen_ids = get_seen_ids()
    print(f"Loaded {len(seen_ids)} seen IDs.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Real Desktop Browser User-Agent & Viewport
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()
        
        url = "https://www.facebook.com/marketplace/search/?query=carnage"
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(3000)
        
        # Scroll down to force load Marketplace listings
        await page.evaluate("window.scrollBy(0, 500);")
        await page.wait_for_timeout(3000)

        # Broad selector for marketplace item links
        links = await page.query_selector_all('a[href*="/marketplace/item/"]')
        print(f"Found {len(links)} item links on page.")

        new_found = False
        
        for link_elem in links[:15]:
            href = await link_elem.get_attribute('href')
            if href:
                # Extract clean Item ID using Regex
                match = re.search(r'/item/(\d+)', href)
                if match:
                    item_id = match.group(1)
                    full_link = f"https://www.facebook.com/marketplace/item/{item_id}/"
                    
                    if item_id not in seen_ids:
                        text = await link_elem.inner_text()
                        lines = [line.strip() for line in text.split('\n') if line.strip()]
                        
                        price = lines[0] if len(lines) > 0 else "N/A"
                        title = lines[1] if len(lines) > 1 else "Carnage Item"
                        
                        print(f"New item detected: {title} ({price})")
                        send_telegram(title, price, full_link)
                        seen_ids.add(item_id)
                        new_found = True

        if new_found:
            save_seen_ids(seen_ids)
            print("Updated seen_ids.txt")
        else:
            print("No new items found in this run.")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
