import csv
import argparse
import sys
from ddgs import DDGS

def scrape_tiktok_by_hashtag(hashtag: str, max_count: int = 50, output_csv: str = "tiktok_videos.csv"):
    clean_tag = hashtag.lstrip('#')
    print(f"[*] Scraping TikTok video links for hashtag: #{clean_tag} (Target: {max_count} videos)...")
    
    queries = [
        f'site:tiktok.com/@ "{clean_tag}"',
        f'site:tiktok.com/video "{clean_tag}"',
        f'tiktok video "{clean_tag}"',
        f'hashtag {clean_tag} site:tiktok.com',
        f'tiktok #"{clean_tag}"'
    ]
    
    videos_data = []
    seen_ids = set()
    
    with DDGS() as ddgs:
        for q in queries:
            if len(videos_data) >= max_count:
                break
            print(f"[*] Querying: {q}")
            try:
                results = ddgs.text(q, max_results=100)
                for r in results:
                    url = r.get('href', '')
                    title = r.get('title', '')
                    snippet = r.get('body', '')
                    
                    if '/video/' in url:
                        clean_url = url.split('?')[0]
                        parts = clean_url.split('/')
                        
                        video_id = ''
                        author = ''
                        for idx, p in enumerate(parts):
                            if p.startswith('@'):
                                author = p.replace('@', '')
                            elif p == 'video' and idx + 1 < len(parts):
                                video_id = parts[idx + 1]
                                
                        if video_id and video_id not in seen_ids:
                            seen_ids.add(video_id)
                            standard_url = f"https://www.tiktok.com/@{author}/video/{video_id}" if author else clean_url
                            
                            videos_data.append({
                                'id': video_id,
                                'author': author,
                                'webVideoUrl': standard_url,
                                'title': title,
                                'snippet': snippet
                            })
                            print(f"[{len(videos_data)}/{max_count}] Found: {standard_url}")
                            if len(videos_data) >= max_count:
                                break
            except Exception as e:
                print(f"[!] Query notice: {e}", file=sys.stderr)
                
    print(f"\n[+] Total unique TikTok video URLs scraped: {len(videos_data)}")
    
    if videos_data:
        with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=['id', 'author', 'webVideoUrl', 'title', 'snippet'])
            writer.writeheader()
            writer.writerows(videos_data)
        print(f"[+] Successfully exported video list to CSV file: {output_csv}")
        return True
    else:
        print("[!] No video URLs could be found.")
        return False

def main():
    parser = argparse.ArgumentParser(description="TikTok Hashtag Video Link Scraper (Python CLI)")
    parser.add_argument("hashtag", type=str, help="Hashtag/keyword (e.g. dulich)")
    parser.add_argument("-n", "--number", type=int, default=50, help="Number of videos to scrape (default: 50)")
    parser.add_argument("-o", "--output", type=str, default="tiktok_videos.csv", help="Output CSV path (default: tiktok_videos.csv)")
    
    args = parser.parse_args()
    scrape_tiktok_by_hashtag(args.hashtag, args.number, args.output)

if __name__ == "__main__":
    main()
