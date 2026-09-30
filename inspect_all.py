import asyncio
import json
from playwright.async_api import async_playwright

def find_video_ids(data, results=None):
    if results is None:
        results = []
    if isinstance(data, dict):
        # Check if dict looks like a video item
        if "id" in data and ("author" in data or "authorStats" in data or "stats" in data or "video" in data):
            results.append(data)
        for k, v in data.items():
            find_video_ids(v, results)
    elif isinstance(data, list):
        for item in data:
            find_video_ids(item, results)
    return results

async def inspect_all():
    url = "https://www.tiktok.com/search?q=dulich"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900}
        )
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        
        elem = await page.query_selector('script#__UNIVERSAL_DATA_FOR_REHYDRATION__')
        if elem:
            text = await elem.inner_text()
            data = json.loads(text)
            
            video_nodes = find_video_ids(data)
            print(f"[+] Found {len(video_nodes)} potential video nodes in rehydration JSON!")
            for idx, node in enumerate(video_nodes[:10]):
                v_id = node.get("id")
                author = node.get("author")
                if isinstance(author, dict):
                    author = author.get("uniqueId") or author.get("nickname")
                desc = node.get("desc", "")
                stats = node.get("stats", {})
                print(f"Node {idx+1}: ID={v_id}, Author={author}, Desc={desc[:40]}, Stats={stats}")
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_all())
