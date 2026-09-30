import asyncio
import json
from playwright.async_api import async_playwright

async def inspect_rehydration():
    url = "https://www.tiktok.com/tag/dulich"
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
            print("Top level keys:", list(data.keys()))
            default_scope = data.get("__DEFAULT_SCOPE__", {})
            print("Default scope keys:", list(default_scope.keys()))
            
            # Print structure of default_scope keys
            for k, v in default_scope.items():
                if isinstance(v, dict):
                    print(f"Key '{k}' sub-keys:", list(v.keys()))
                    # If any dict has item or list or video
                    for sub_k, sub_v in v.items():
                        if isinstance(sub_v, list):
                            print(f"   -> List under '{k}.{sub_k}': length {len(sub_v)}")
                        elif isinstance(sub_v, dict):
                            print(f"   -> Dict under '{k}.{sub_k}': keys {list(sub_v.keys())}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_rehydration())
