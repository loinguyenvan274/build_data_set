import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def debug():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
            locale="vi-VN"
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        await page.goto("https://www.tiktok.com/tag/dulich", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)
        
        # Check buttons
        buttons = await page.query_selector_all("button")
        print(f"Total buttons found: {len(buttons)}")
        for b in buttons:
            try:
                txt = await b.inner_text()
                if txt:
                    safe_txt = txt.encode('ascii', errors='ignore').decode('ascii').strip()
                    print(f"Button text found: '{safe_txt}'")
                    lower_txt = txt.lower()
                    if any(k in lower_txt for k in ["chấp nhận", "accept", "allow", "tiếp tục", "continue", "khách", "guest", "đồng ý", "decline"]):
                        print(" --> Clicking cookie / login popup button...")
                        await b.click()
                        await page.wait_for_timeout(2000)
            except Exception as e:
                pass
                        
        # Scroll and check video links
        for i in range(5):
            await page.evaluate("window.scrollBy(0, 1500)")
            await page.wait_for_timeout(2000)
            
        links = await page.query_selector_all("a[href*='/video/']")
        print(f"\nVideo links found after clicking popup: {len(links)}")
        for l in links[:5]:
            href = await l.get_attribute("href")
            print("Link:", href)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug())
