import asyncio
import argparse
import csv
import sys
from TikTokApi import TikTokApi

async def scrape_hashtag_tiktok_api(hashtag: str, max_count: int, output_csv: str):
    print(f"[*] Starting scraper via TikTokApi for hashtag: #{hashtag}, max videos: {max_count}")
    videos_data = []
    
    try:
        async with TikTokApi() as api:
            # Create session using chromium installed by playwright
            await api.create_sessions(num_sessions=1, headless=True, sleep_after=3)
            tag = api.hashtag(name=hashtag)
            
            count = 0
            async for video in tag.videos(count=max_count):
                v_dict = video.as_dict
                video_id = v_dict.get('id', '')
                desc = v_dict.get('desc', '')
                author_name = v_dict.get('author', {}).get('uniqueId', '')
                
                # Construct web URL
                web_url = f"https://www.tiktok.com/@{author_name}/video/{video_id}" if author_name and video_id else ""
                
                stats = v_dict.get('stats', {})
                play_count = stats.get('playCount', 0)
                digg_count = stats.get('diggCount', 0)
                comment_count = stats.get('commentCount', 0)
                share_count = stats.get('shareCount', 0)
                
                videos_data.append({
                    'id': video_id,
                    'author': author_name,
                    'webVideoUrl': web_url,
                    'desc': desc,
                    'playCount': play_count,
                    'diggCount': digg_count,
                    'commentCount': comment_count,
                    'shareCount': share_count
                })
                count += 1
                print(f"[{count}/{max_count}] Found: {web_url}")
                if count >= max_count:
                    break
    except Exception as e:
        print(f"[!] TikTokApi encountered an issue: {e}", file=sys.stderr)
        return False, videos_data

    return True, videos_data

async def scrape_hashtag_playwright(hashtag: str, max_count: int, output_csv: str):
    print(f"[*] Fallback to direct Playwright scraping for hashtag: #{hashtag}...")
    from playwright.async_api import async_playwright
    
    videos_data = []
    video_urls = set()
    
    url = f"https://www.tiktok.com/tag/{hashtag}"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()
        
        print(f"[*] Navigating to {url}...")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)
        
        # Scroll loop to collect video links
        scroll_attempts = 0
        max_scrolls = max_count // 2 + 10
        
        while len(video_urls) < max_count and scroll_attempts < max_scrolls:
            # Find video anchor links matching pattern /video/
            links = await page.query_selector_all('a[href*="/video/"]')
            for link in links:
                href = await link.get_attribute('href')
                if href and '/video/' in href:
                    if not href.startswith('http'):
                        href = 'https://www.tiktok.com' + href
                    if href not in video_urls:
                        video_urls.add(href)
                        parts = href.split('/')
                        video_id = parts[-1] if parts else ''
                        author = parts[-3].replace('@', '') if len(parts) >= 4 else ''
                        
                        videos_data.append({
                            'id': video_id,
                            'author': author,
                            'webVideoUrl': href,
                            'desc': '',
                            'playCount': 0,
                            'diggCount': 0,
                            'commentCount': 0,
                            'shareCount': 0
                        })
                        print(f"[{len(video_urls)}/{max_count}] Found: {href}")
                        if len(video_urls) >= max_count:
                            break
            
            # Scroll down
            await page.evaluate("window.scrollBy(0, 1000)")
            await asyncio.sleep(2)
            scroll_attempts += 1
            
        await browser.close()
        
    return True, videos_data

async def main():
    parser = argparse.ArgumentParser(description="TikTok Hashtag Video Scraper")
    parser.add_argument("hashtag", type=str, help="Hashtag to scrape (e.g., dulich)")
    parser.add_argument("-n", "--number", type=int, default=20, help="Number of videos to scrape (default: 20)")
    parser.add_argument("-o", "--output", type=str, default="tiktok_videos.csv", help="Output CSV file path")
    
    args = parser.parse_args()
    
    # Try TikTokApi first
    success, data = await scrape_hashtag_tiktok_api(args.hashtag, args.number, args.output)
    
    # If TikTokApi failed or got 0 videos, use Playwright browser fallback
    if not success or len(data) == 0:
        print("[!] TikTokApi yielded no results or errored. Switching to Playwright web scraping fallback...")
        _, data = await scrape_hashtag_playwright(args.hashtag, args.number, args.output)
        
    if data:
        # Save to CSV
        with open(args.output, mode='w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=['id', 'author', 'webVideoUrl', 'desc', 'playCount', 'diggCount', 'commentCount', 'shareCount'])
            writer.writeheader()
            writer.writerows(data)
        print(f"\n[+] Successfully saved {len(data)} video links to {args.output}!")
    else:
        print("\n[!] Could not fetch any videos. Please check your internet connection or hashtag.")

if __name__ == "__main__":
    asyncio.run(main())
