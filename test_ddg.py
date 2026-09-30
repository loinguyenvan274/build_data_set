import csv
from duckduckgo_search import DDGS

def search_tiktok_hashtag(hashtag: str, max_results: int = 50, output_csv: str = "tiktok_ddg.csv"):
    query = f'site:tiktok.com video "{hashtag}"'
    print(f"[*] Querying search index for TikTok videos: {query}...")
    
    videos_data = []
    seen_urls = set()
    
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=max_results * 2)
        for r in results:
            url = r.get('href', '')
            title = r.get('title', '')
            snippet = r.get('body', '')
            
            if '/video/' in url and url not in seen_urls:
                seen_urls.add(url)
                clean_url = url.split('?')[0]
                parts = clean_url.split('/')
                author = parts[3].replace('@', '') if len(parts) > 3 else ''
                v_id = parts[-1] if parts else ''
                
                videos_data.append({
                    'id': v_id,
                    'author': author,
                    'webVideoUrl': clean_url,
                    'title': title,
                    'snippet': snippet
                })
                print(f"[{len(videos_data)}] Found: {clean_url}")
                if len(videos_data) >= max_results:
                    break
                    
    print(f"\n[+] Total TikTok video links found: {len(videos_data)}")
    if videos_data:
        with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=['id', 'author', 'webVideoUrl', 'title', 'snippet'])
            writer.writeheader()
            writer.writerows(videos_data)
        print(f"[+] Exported to {output_csv}")

if __name__ == "__main__":
    search_tiktok_hashtag("dulich", 20, "dulich_tiktok_search.csv")
