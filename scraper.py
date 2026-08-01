import asyncio
from playwright.async_api import async_playwright
import requests
import os
import re
import urllib.parse

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

def send_telegram(title, link):
    msg = f"🔥 **New Carnage Deal Found!**\n\n📌 Title: {title}\n🔗 Link: {link}"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        print(f"Telegram status: {r.status_code}")
    except Exception as e:
        print(f"Telegram error: {e}")

async def main():
    seen_ids = get_seen_ids()
    print(f"Loaded {len(seen_ids)} seen IDs.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # Using DuckDuckGo HTML (No JS, Anti-bot friendly)
        search_url = "https://html.duckduckgo.com/html/?q=site:facebook.com/marketplace/item+carnage+sri+lanka"
        print("Navigating to DuckDuckGo HTML...")
        
        await page.goto(search_url, wait_until="domcontentloaded")
        
        # Grab all links on the page
        links = await page.query_selector_all('a')
        print(f"Scanning {len(links)} links on DDG...")

        new_found = False
        
        for link_elem in links:
            href = await link_elem.get_attribute('href')
            if href:
                # DuckDuckGo wraps links, so we unquote them to find the real URL
                decoded_url = urllib.parse.unquote(href)
                
                # Check if it's a Facebook Marketplace Item URL
                match = re.search(r'facebook\.com/marketplace/item/(\d+)', decoded_url)
                if match:
                    item_id = match.group(1)
                    full_link = f"https://www.facebook.com/marketplace/item/{item_id}/"
                    
                    if item_id not in seen_ids:
                        print(f"New Facebook ID found: {item_id}")
                        title = "Carnage Listing (via Search)"
                        
                        send_telegram(title, full_link)
                        seen_ids.add(item_id)
                        new_found = True

        if new_found:
            save_seen_ids(seen_ids)
            print("Saved new IDs successfully.")
        else:
            print("No new items found in search results.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
