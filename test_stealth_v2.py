import asyncio
import csv
import re
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def scrape_stealth():
    url = "https://www.tiktok.com/tag/dulich"
    print(f"[*] Navigating to {url} with stealth...")
    
    video_links = set()
    videos_data = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900}
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(5000)
        
        for i in range(10):
            await page.evaluate("window.scrollBy(0, 1000)")
            await page.wait_for_timeout(2000)
            
            # Find all links
            links = await page.query_selector_all("a")
            for l in links:
                href = await l.get_attribute("href")
                if href and ("/video/" in href or "/v/" in href):
                    if not href.startswith("http"):
                        href = "https://www.tiktok.com" + href
                    clean_u = href.split("?")[0]
                    if clean_u not in video_links:
                        video_links.add(clean_u)
                        parts = clean_u.split('/')
                        author = parts[3].replace('@', '') if len(parts) > 3 else ''
                        v_id = parts[-1] if parts else ''
                        videos_data.append({
                            'id': v_id,
                            'author': author,
                            'webVideoUrl': clean_u
                        })
                        print(f"[{len(video_links)}] Found: {clean_u}")
                        
        await browser.close()
        
    print(f"\n[+] Total videos found: {len(videos_data)}")
    if videos_data:
        with open("tiktok_stealth_dulich.csv", "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=['id', 'author', 'webVideoUrl'])
            writer.writeheader()
            writer.writerows(videos_data)
        print("[+] Saved to tiktok_stealth_dulich.csv")

if __name__ == "__main__":
    asyncio.run(scrape_stealth())
