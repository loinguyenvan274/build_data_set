import asyncio
import csv
from playwright.async_api import async_playwright

async def test_mobile():
    url = "https://www.tiktok.com/tag/dulich"
    print(f"[*] Testing mobile user-agent on {url}...")
    
    video_links = set()
    videos_data = []
    
    async with async_playwright() as p:
        # iPhone 13 Pro User-Agent and Viewport
        iphone_13 = p.devices['iPhone 13 Pro']
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(**iphone_13)
        page = await context.new_page()
        
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(4000)
        
        # Check links
        for i in range(5):
            await page.evaluate("window.scrollBy(0, 1500)")
            await page.wait_for_timeout(2000)
            
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
        
    print(f"\n[+] Total videos found on mobile web: {len(videos_data)}")
    if videos_data:
        with open("tiktok_mobile_dulich.csv", "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=['id', 'author', 'webVideoUrl'])
            writer.writeheader()
            writer.writerows(videos_data)
        print("[+] Saved to tiktok_mobile_dulich.csv")

if __name__ == "__main__":
    asyncio.run(test_mobile())
