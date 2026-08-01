import asyncio
from playwright.async_api import async_playwright
import requests
import os

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
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

async def main():
    seen_ids = get_seen_ids()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        url = "https://www.facebook.com/marketplace/search/?query=carnage"
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)
        
        links = await page.query_selector_all('a[href*="/marketplace/item/"]')
        new_found = False
        
        for link_elem in links[:10]:
            href = await link_elem.get_attribute('href')
            if href:
                item_id = href.split('/item/')[1].split('/')[0]
                full_link = f"https://www.facebook.com{href}"
                
                if item_id not in seen_ids:
                    text = await link_elem.inner_text()
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    price = lines[0] if len(lines) > 0 else "N/A"
                    title = lines[1] if len(lines) > 1 else "Carnage Item"
                    
                    send_telegram(title, price, full_link)
                    seen_ids.add(item_id)
                    new_found = True
                    
        if new_found:
            save_seen_ids(seen_ids)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
