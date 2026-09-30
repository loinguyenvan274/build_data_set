import csv
import os
import sys
import time
import argparse
from ddgs import DDGS

# Reconfigure UTF-8 output encoding for Windows terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

def get_processed_locations(output_csv_path: str) -> set:
    """Đọc tập hợp các địa điểm (phuong, thanh_pho) đã quét thành công trong file CSV đầu ra."""
    processed = set()
    if os.path.exists(output_csv_path) and os.path.getsize(output_csv_path) > 0:
        try:
            with open(output_csv_path, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    phuong = row.get('phuong', '').strip()
                    thanh_pho = row.get('thanh_pho', '').strip()
                    if phuong and thanh_pho:
                        processed.add((phuong, thanh_pho))
        except Exception as e:
            print(f"[!] Lưu ý khi đọc file kết quả cũ: {e}", file=sys.stderr)
    return processed

def safe_search_query(query: str, max_results: int = 50, max_retries: int = 3):
    """
    Thực hiện truy vấn với cơ chế tự phục hồi: 
    Nếu bị ngắt kết nối TLS/h2 (unexpected EOF) hoặc Rate-limit, tự động nghỉ 5-10s và tạo lại DDGS session mới.
    """
    for attempt in range(1, max_retries + 1):
        try:
            # Tạo session mới cho mỗi đợt truy vấn để giải phóng socket cũ
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                return results
        except Exception as e:
            err_msg = str(e)
            print(f"   [!] Sự cố kết nối (Lần {attempt}/{max_retries}): {err_msg[:120]}")
            if attempt < max_retries:
                wait_time = attempt * 5 # Tạm dừng 5s, 10s...
                print(f"   [*] Tạm dừng {wait_time}s trước khi mở lại kết nối...")
                time.sleep(wait_time)
            else:
                print(f"   [!] Đã hết số lần thử lại cho truy vấn này.")
                return []

def scrape_videos_for_keyword(phuong: str, thanh_pho: str, max_count: int = 15):
    """Tìm 15 video cho địa điểm sử dụng các mẫu query của scrape_tiktok_ddgs.py với safe_search_query."""
    keyword = f"quán ăn ở {phuong} {thanh_pho}".strip()
    
    queries = [
        f'site:tiktok.com/@ "{keyword}"',
        f'site:tiktok.com/video "{keyword}"',
        f'tiktok video "{keyword}"',
        f'hashtag {keyword} site:tiktok.com',
        f'tiktok "{keyword}"',
        f'"{keyword}" site:tiktok.com'
    ]
    
    videos_data = []
    seen_ids = set()
    
    for q in queries:
        if len(videos_data) >= max_count:
            break
            
        results = safe_search_query(q, max_results=40, max_retries=3)
        if not results:
            continue
            
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
                        'phuong': phuong,
                        'thanh_pho': thanh_pho,
                        'search_keyword': keyword,
                        'id': video_id,
                        'author': author,
                        'webVideoUrl': standard_url,
                        'title': title,
                        'snippet': snippet
                    })
                    
                    if len(videos_data) >= max_count:
                        break
                        
    return videos_data

def run_batch_crawler(input_csv: str, output_csv: str, target_count: int = 15, limit: int = None, delay: float = 2.0, start_from: str = None):
    """Chạy cào dữ liệu theo từng địa điểm với hỗ trợ bắt đầu từ một địa điểm cụ thể."""
    if not os.path.exists(input_csv):
        print(f"[!] Lỗi: Không tìm thấy file '{input_csv}'!", file=sys.stderr)
        return

    processed_locations = get_processed_locations(output_csv)
    if processed_locations:
        print(f"[*] Đã tìm thấy {len(processed_locations)} địa điểm đã quét trong '{output_csv}'.")

    # Đọc danh sách địa điểm từ file
    locations = []
    with open(input_csv, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            phuong = row.get('Tên', '').strip()
            thanh_pho = row.get('Thành Phố', '').strip()
            if phuong and thanh_pho:
                locations.append((phuong, thanh_pho))

    print(f"[*] Tổng số địa điểm trong file gốc: {len(locations)}")

    # Xử lý điểm bắt đầu (start_from) nếu có
    if start_from:
        start_from_clean = start_from.strip().lower()
        start_idx = None
        for i, (p, tp) in enumerate(locations):
            full_name = f"{p},{tp}".lower()
            full_name_space = f"{p} {tp}".lower()
            if start_from_clean in full_name or start_from_clean in full_name_space or start_from_clean in p.lower():
                start_idx = i
                print(f"[*] Đã xác định vị trí bắt đầu tại dòng {i+1}: '{p}, {tp}'")
                break
                
        if start_idx is not None:
            locations = locations[start_idx:]
        else:
            print(f"[!] Không tìm thấy địa điểm khớp với '{start_from}' trong file. Sẽ chạy từ đầu.")

    # Lọc các địa điểm chưa quét
    unprocessed = [loc for loc in locations if loc not in processed_locations]
    print(f"[*] Số địa điểm còn lại cần quét: {len(unprocessed)}")

    if limit and limit > 0:
        unprocessed = unprocessed[:limit]
        print(f"[*] Giới hạn quét {limit} địa điểm trong đợt này.")

    if not unprocessed:
        print("[+] Tất cả địa điểm được chọn đã được quét xong hoàn tất!")
        return

    # Mở file kết quả và ghi tiếp (append)
    file_exists = os.path.exists(output_csv) and os.path.getsize(output_csv) > 0
    fieldnames = ['phuong', 'thanh_pho', 'search_keyword', 'id', 'author', 'webVideoUrl', 'title', 'snippet']

    with open(output_csv, mode='a', newline='', encoding='utf-8-sig') as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
            f_out.flush()

        for idx, (phuong, thanh_pho) in enumerate(unprocessed, start=1):
            kw = f"quán ăn ở {phuong} {thanh_pho}"
            print(f"\n[{idx}/{len(unprocessed)}] Đang tìm: '{kw}'...")
            
            vids = scrape_videos_for_keyword(phuong, thanh_pho, max_count=target_count)
            
            if vids:
                writer.writerows(vids)
                f_out.flush() # Ghi ngay xuống đĩa cứng
                print(f" ->  Đã lưu {len(vids)}/{target_count} video cho {phuong}, {thanh_pho}")
            else:
                print(f" ->  Không tìm thấy video nào.")
            
            time.sleep(delay)

    print(f"\n[🎉] Đã hoàn thành đợt quét! Dữ liệu được lưu tại: {output_csv}")

def main():
    parser = argparse.ArgumentParser(description="Tool tự động lấy video TikTok quán ăn có chống lỗi TLS/h2")
    parser.add_argument("-i", "--input", type=str, default="danh_sach_phuong.csv", help="File CSV danh sách phường")
    parser.add_argument("-o", "--output", type=str, default="ket_qua_quan_an_phuong.csv", help="File CSV xuất kết quả")
    parser.add_argument("-n", "--number", type=int, default=15, help="Số lượng video tối đa mỗi địa điểm (mặc định: 15)")
    parser.add_argument("-s", "--start-from", type=str, default=None, help="Vị trí bắt đầu quét (Ví dụ: 'Hà Đông' hoặc 'Hà Đông, Hà Nội')")
    parser.add_argument("-l", "--limit", type=int, default=None, help="Giới hạn số phường quét trong đợt chạy")
    parser.add_argument("-d", "--delay", type=float, default=2.0, help="Thời gian nghỉ (giây) giữa các lần quét")

    args = parser.parse_args()
    run_batch_crawler(args.input, args.output, target_count=args.number, limit=args.limit, delay=args.delay, start_from=args.start_from)

if __name__ == "__main__":
    main()
