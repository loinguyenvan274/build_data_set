import asyncio
import json
import csv
from playwright.async_api import async_playwright

async def test_intercept():
    extracted_videos = []
    
    async def handle_response(response):
        # Intercept TikTok JSON responses containing item_list or itemList or data
        url = response.url
        if any(keyword in url for keyword in ["/api/challenge/item_list/", "/api/search/item_list/", "/api/item_list/"]):
            print(f"[+] Intercepted API endpoint: {url}")
            print(f"[+] API Status: {response.status}")
            try:
                body_bytes = await response.body()
                print(f"[+] Received body bytes length: {len(body_bytes)}")
                if body_bytes:
                    data = json.loads(body_bytes.decode('utf-8', errors='ignore'))
                    items = data.get("itemList") or data.get("item_list") or []
                    print(f"[+] Found {len(items)} items in API response!")
                    for item in items:
                        v_id = item.get("id") or item.get("item", {}).get("id")
                        author = item.get("author", {}).get("uniqueId") or item.get("authorStats", {}).get("uniqueId")
                        desc = item.get("desc", "")
                        stats = item.get("stats", {})
                        
                        if v_id and author:
                            video_url = f"https://www.tiktok.com/@{author}/video/{v_id}"
                            extracted_videos.append({
                                'id': v_id,
                                'author': author,
                                'webVideoUrl': video_url,
                                'desc': desc,
                                'playCount': stats.get('playCount', 0),
                                'diggCount': stats.get('diggCount', 0),
                                'commentCount': stats.get('commentCount', 0)
                            })
            except Exception as e:
                print(f"[!] Error reading body: {e}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()
        page.on("response", handle_response)
        
        hashtag = "dulich"
        target_url = f"https://www.tiktok.com/tag/{hashtag}"
        print(f"[*] Navigating to {target_url}...")
        
        try:
            await page.goto(target_url, wait_until="networkidle", timeout=30000)
        except Exception:
            pass
            
        await page.wait_for_timeout(3000)
        
        # Scroll to trigger more API requests
        for i in range(5):
            await page.evaluate("window.scrollBy(0, 2000)")
            await page.wait_for_timeout(3000)
            
        print(f"\nTotal videos captured via API interception: {len(extracted_videos)}")
        if extracted_videos:
            with open("tiktok_dulich_api.csv", "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=['id', 'author', 'webVideoUrl', 'desc', 'playCount', 'diggCount', 'commentCount'])
                writer.writeheader()
                writer.writerows(extracted_videos)
            print("[+] Saved to tiktok_dulich_api.csv")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_intercept())
