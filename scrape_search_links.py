import asyncio
import csv
import re
from playwright.async_api import async_playwright

async def scrape_tiktok_hashtag(hashtag: str, max_count: int = 50, output_csv: str = "tiktok_dulich.csv"):
    url = f"https://www.tiktok.com/search?q={hashtag}"
    print(f"[*] Searching TikTok for #{hashtag} at {url}...")
    
    video_links = set()
    videos_data = []
    
    async with async_playwright() as p:
        # Launch browser with arguments to avoid automation detection
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh"
        )
        
        page = await context.new_page()
        
        # Avoid webdriver flag
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(4000)
        
        # Scroll loop to load video items
        scroll_count = 0
        max_scrolls = 20
        
        while len(video_links) < max_count and scroll_count < max_scrolls:
            content = await page.content()
            
            # Find all video links matching regex pattern: /@[\w.-]+/video/\d+
            found_urls = re.findall(r'href="(/@[^/]+/video/\d+)"', content)
            found_urls += re.findall(r'(https://www\.tiktok\.com/@[^/]+/video/\d+)', content)
            
            for u in found_urls:
                if not u.startswith("http"):
                    u = "https://www.tiktok.com" + u
                clean_u = u.split("?")[0]
                
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
                    print(f"[{len(video_links)}/{max_count}] Found: {clean_u}")
                    if len(video_links) >= max_count:
                        break
                        
            # Scroll down
            await page.evaluate("window.scrollBy(0, 1500)")
            await page.wait_for_timeout(2000)
            scroll_count += 1
            
        await browser.close()
        
    print(f"\n[+] Total videos found: {len(videos_data)}")
    if videos_data:
        with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=['id', 'author', 'webVideoUrl'])
            writer.writeheader()
            writer.writerows(videos_data)
        print(f"[+] Saved to {output_csv}")
    else:
        print("[!] No video links found.")

if __name__ == "__main__":
    asyncio.run(scrape_tiktok_hashtag("dulich", 20, "tiktok_dulich_search.csv"))
