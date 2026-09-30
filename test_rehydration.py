import asyncio
import json
import csv
from playwright.async_api import async_playwright

async def extract_via_rehydration():
    url = "https://www.tiktok.com/tag/dulich"
    videos_data = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        # Use persistent or custom context
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900}
        )
        page = await context.new_page()
        
        print(f"[*] Loading {url}...")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        
        # Try finding __UNIVERSAL_DATA_FOR_REHYDRATION__ or SIGI_STATE or __INIT_DATA__
        script_content = None
        selectors = [
            'script#__UNIVERSAL_DATA_FOR_REHYDRATION__',
            'script#SIGI_STATE',
            'script#__INIT_DATA__'
        ]
        
        for sel in selectors:
            elem = await page.query_selector(sel)
            if elem:
                script_content = await elem.inner_text()
                print(f"[+] Found data script element: {sel}")
                break
                
        if script_content:
            try:
                data = json.loads(script_content)
                # Parse rehydration data structure
                default_scope = data.get("__DEFAULT_SCOPE__", {})
                
                # Check challenge item detail or search
                challenge_detail = default_scope.get("webapp.challenge-detail", {})
                itemList = challenge_detail.get("itemList", [])
                
                if not itemList:
                    # Search alternative keys in JSON recursively or via dict keys
                    for k, v in default_scope.items():
                        if isinstance(v, dict) and "itemList" in v:
                            itemList = v["itemList"]
                            break
                            
                print(f"[+] Found {len(itemList)} videos in rehydration data!")
                
                for item in itemList:
                    v_id = item.get("id") or item.get("video", {}).get("id")
                    author = item.get("author", {}).get("uniqueId") if isinstance(item.get("author"), dict) else item.get("author")
                    desc = item.get("desc", "")
                    stats = item.get("stats", {})
                    
                    if v_id:
                        v_url = f"https://www.tiktok.com/@{author}/video/{v_id}" if author else f"https://www.tiktok.com/video/{v_id}"
                        videos_data.append({
                            'id': v_id,
                            'author': author or '',
                            'webVideoUrl': v_url,
                            'desc': desc,
                            'playCount': stats.get('playCount', 0),
                            'diggCount': stats.get('diggCount', 0),
                            'commentCount': stats.get('commentCount', 0)
                        })
                        print(f" - {v_url}")
            except Exception as e:
                print(f"[!] Error parsing JSON script: {e}")
        else:
            print("[!] No rehydration script tag found on page.")
            
        await browser.close()
        
    if videos_data:
        with open("rehydration_videos.csv", "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=['id', 'author', 'webVideoUrl', 'desc', 'playCount', 'diggCount', 'commentCount'])
            writer.writeheader()
            writer.writerows(videos_data)
        print(f"\n[+] Saved {len(videos_data)} videos to rehydration_videos.csv")

if __name__ == "__main__":
    asyncio.run(extract_via_rehydration())
