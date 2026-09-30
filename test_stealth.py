import asyncio
from playwright.async_api import async_playwright
import csv

async def test_playwright():
    async with async_playwright() as p:
        # Launch browser with realistic viewport & user-agent
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox'
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
            locale="en-US"
        )
        page = await context.new_page()
        
        # Add stealth script to bypass navigator.webdriver detection
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        url = "https://www.tiktok.com/tag/dulich"
        print(f"[*] Navigating to {url}...")
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception as e:
            print(f"[!] Navigation notice: {e}")
            
        await page.wait_for_timeout(4000)
        
        # Scroll down several times
        urls = set()
        for i in range(5):
            await page.evaluate("window.scrollBy(0, 1500)")
            await page.wait_for_timeout(2000)
            
            # Find all links containing video
            elements = await page.query_selector_all("a")
            for el in elements:
                href = await el.get_attribute("href")
                if href and ("/video/" in href or "/v/" in href):
                    if not href.startswith("http"):
                        href = "https://www.tiktok.com" + href
                    # clean URL
                    clean_url = href.split('?')[0]
                    urls.add(clean_url)
            print(f"Scroll {i+1}: Found {len(urls)} video links so far.")
            
        print("\nExtracted URLs:")
        videos_list = []
        for u in urls:
            print(u)
            parts = u.split('/')
            author = parts[3].replace('@', '') if len(parts) > 3 else ''
            v_id = parts[-1] if parts else ''
            videos_list.append({
                'id': v_id,
                'author': author,
                'webVideoUrl': u
            })
            
        if videos_list:
            with open("dulich_tiktok_links.csv", "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=['id', 'author', 'webVideoUrl'])
                writer.writeheader()
                writer.writerows(videos_list)
            print(f"\n[+] Saved {len(videos_list)} links to dulich_tiktok_links.csv")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_playwright())
