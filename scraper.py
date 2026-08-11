import asyncio
from playwright.async_api import async_playwright
import requests
import os
import re

TELEGRAM_BOT_TOKEN = os.environ.get("BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("CHAT_ID")
STATE_FILE = "state.json"
SEEN_FILE = "seen_ids.txt"

def get_seen_ids():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(f.read().splitlines())
    return set()

def save_seen_ids(seen_ids):
    with open(SEEN_FILE, "w") as f:
        f.write("\n".join(seen_ids))

# 🚀 Image එකත් එක්ක Telegram යවන විදිහට වෙනස් කරන ලද ෆන්ක්ෂන් එක
def send_telegram(title, price, link, image_url=None):
    msg = f"🔥 **New Carnage Listing Found!**\n\n📌 Title: {title}\n💰 Price: {price}\n\n🔗 Link: {link}"
    
    # Image URL එකක් තියෙනවා නම් sendPhoto පාවිච්චි කරයි, නැත්නම් sendMessage පාවිච්චි කරයි
    if image_url:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "photo": image_url,
            "caption": msg,
            "parse_mode": "Markdown"
        }
    else:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown"
        }

    try:
        r = requests.post(url, data=payload)
        print(f"Telegram status: {r.status_code}")
    except Exception as e:
        print(f"Telegram error: {e}")

async def main():
    seen_ids = get_seen_ids()
    print(f"Loaded {len(seen_ids)} seen IDs.")

    if not os.path.exists(STATE_FILE):
        print(f"❌ Error: {STATE_FILE} not found!")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--window-size=1920,1080"
            ]
        )
        
        context = await browser.new_context(
            storage_state=STATE_FILE,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US"
        )

        page = await context.new_page()
        
        url = "https://www.facebook.com/marketplace/search/?query=carnage"
        print(f"Navigating directly to {url}...")
        
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)

        print("Scrolling to load all listings...")
        for _ in range(5):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            await page.wait_for_timeout(3000)

        links = await page.query_selector_all('a[href*="/marketplace/item/"]')
        print(f"Found {len(links)} total item links on Facebook Marketplace!")

        new_found = False
        
        for link_elem in links:
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
                        
                        # 🖼️ Image එකේ Link එක ගන්නා කොටස:
                        image_url = None
                        img_elem = await link_elem.query_selector('img')
                        if img_elem:
                            image_url = await img_elem.get_attribute('src')
                        
                        print(f"New Item Detected: {title} ({price})")
                        
                        # Image එකත් සමඟ Telegram එකට යැවීම
                        send_telegram(title, price, full_link, image_url)
                        
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
