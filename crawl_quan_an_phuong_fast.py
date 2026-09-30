import csv
import os
import sys
import time
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from ddgs import DDGS

# Force UTF-8 output encoding for Windows terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Thread lock để đảm bảo ghi file CSV và in log không bị đè dòng
csv_lock = threading.Lock()
print_lock = threading.Lock()

def safe_print(msg: str):
    with print_lock:
        print(msg)

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
            safe_print(f"[!] Lưu ý khi đọc file kết quả cũ: {e}")
    return processed

def safe_search_query_thread(query: str, max_results: int = 40, max_retries: int = 3):
    """Thực hiện truy vấn độc lập theo luồng với cơ chế tự tạo lại session DDGS và tự động thử lại khi gặp lỗi."""
    for attempt in range(1, max_retries + 1):
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                return results
        except Exception as e:
            if attempt < max_retries:
                time.sleep(attempt * 2)
            else:
                return []
    return []

def process_single_location(phuong: str, thanh_pho: str, target_count: int = 15):
    """Xử lý tìm kiếm 15 video cho 1 địa điểm cụ thể độc lập trong 1 worker thread."""
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
        if len(videos_data) >= target_count:
            break
            
        results = safe_search_query_thread(q, max_results=40, max_retries=3)
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
                    
                    if len(videos_data) >= target_count:
                        break
                        
    return phuong, thanh_pho, videos_data

def run_fast_multithread_crawler(input_csv: str, output_csv: str, target_count: int = 15, 
                                max_workers: int = 5, limit: int = None, start_from: str = None):
    """Chạy cào dữ liệu siêu tốc đa luồng (Multithreading Parallel Crawler)."""
    if not os.path.exists(input_csv):
        safe_print(f"[!] Lỗi: Không tìm thấy file '{input_csv}'!")
        return

    processed_locations = get_processed_locations(output_csv)
    if processed_locations:
        safe_print(f"[*] Đã tìm thấy {len(processed_locations)} địa điểm đã quét trong '{output_csv}'.")

    # Đọc danh sách địa điểm từ file
    locations = []
    with open(input_csv, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            phuong = row.get('Tên', '').strip()
            thanh_pho = row.get('Thành Phố', '').strip()
            if phuong and thanh_pho:
                locations.append((phuong, thanh_pho))

    total_in_file = len(locations)
    safe_print(f"[*] Tổng số địa điểm trong file gốc: {total_in_file}")

    # Xử lý điểm bắt đầu (start_from) nếu có
    if start_from:
        start_clean = start_from.strip().lower()
        start_idx = None
        for i, (p, tp) in enumerate(locations):
            full_str = f"{p},{tp}".lower()
            if start_clean in full_str or start_clean in f"{p} {tp}".lower() or start_clean in p.lower():
                start_idx = i
                safe_print(f"[*] Đã xác định vị trí bắt đầu tại dòng {i+1}: '{p}, {tp}'")
                break
        if start_idx is not None:
            locations = locations[start_idx:]

    # Lọc các địa điểm chưa quét
    unprocessed = [loc for loc in locations if loc not in processed_locations]
    safe_print(f"[*] Số địa điểm còn lại cần quét: {len(unprocessed)}")

    if limit and limit > 0:
        unprocessed = unprocessed[:limit]
        safe_print(f"[*] Giới hạn quét {limit} địa điểm trong lượt này.")

    if not unprocessed:
        safe_print("[+] Tất cả địa điểm được chọn đã được quét xong hoàn tất!")
        return

    # Mở file CSV và ghi header nếu chưa có
    file_exists = os.path.exists(output_csv) and os.path.getsize(output_csv) > 0
    fieldnames = ['phuong', 'thanh_pho', 'search_keyword', 'id', 'author', 'webVideoUrl', 'title', 'snippet']

    if not file_exists:
        with open(output_csv, mode='a', newline='', encoding='utf-8-sig') as f_out:
            writer = csv.DictWriter(f_out, fieldnames=fieldnames)
            writer.writeheader()

    start_time = time.time()
    completed_count = 0
    total_to_process = len(unprocessed)
    
    safe_print(f"\n🚀 BẮT ĐẦU CÀO ĐA LUỒNG VỚI {max_workers} WORKERS SONG SONG...")

    # Chạy đa luồng bằng ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Gửi tất cả các task tìm kiếm địa điểm vào thread pool
        future_to_loc = {
            executor.submit(process_single_location, p, tp, target_count): (p, tp) 
            for (p, tp) in unprocessed
        }
        
        for future in as_completed(future_to_loc):
            p, tp = future_to_loc[future]
            try:
                res_phuong, res_tp, vids = future.result()
                completed_count += 1
                
                # Ghi dữ liệu an toàn theo luồng (Thread-safe writing)
                if vids:
                    with csv_lock:
                        with open(output_csv, mode='a', newline='', encoding='utf-8-sig') as f_out:
                            writer = csv.DictWriter(f_out, fieldnames=fieldnames)
                            writer.writerows(vids)
                            f_out.flush()
                    safe_print(f"[{completed_count}/{total_to_process}]  {res_phuong}, {res_tp} -> Đã lưu {len(vids)}/{target_count} video")
                else:
                    safe_print(f"[{completed_count}/{total_to_process}] ⚠️ {res_phuong}, {res_tp} -> 0 video")
                    
            except Exception as exc:
                safe_print(f"[!] Lỗi khi xử lý {p}, {tp}: {exc}")

    elapsed = time.time() - start_time
    safe_print(f"\n[🎉] ĐÃ HOÀN THÀNH {completed_count} ĐỊA ĐIỂM TRONG {elapsed:.1f} GIÂY!")
    safe_print(f"📊 Tốc độ trung bình: {completed_count / (elapsed / 60):.1f} địa điểm/phút.")
    safe_print(f"💾 File dữ liệu đầu ra: {output_csv}")

def main():
    parser = argparse.ArgumentParser(description="Tool cào video TikTok siêu tốc đa luồng (Multithreading Fast Crawler)")
    parser.add_argument("-i", "--input", type=str, default="danh_sach_phuong.csv", help="File CSV danh sách phường")
    parser.add_argument("-o", "--output", type=str, default="ket_qua_quan_an_phuong.csv", help="File CSV xuất kết quả")
    parser.add_argument("-n", "--number", type=int, default=15, help="Số lượng video tối đa mỗi địa điểm (mặc định: 15)")
    parser.add_argument("-w", "--workers", type=int, default=5, help="Số luồng chạy song song (mặc định: 5 luồng)")
    parser.add_argument("-s", "--start-from", type=str, default=None, help="Vị trí bắt đầu quét (Ví dụ: 'Hà Đông')")
    parser.add_argument("-l", "--limit", type=int, default=None, help="Giới hạn số địa điểm quét trong đợt này")

    args = parser.parse_args()
    run_fast_multithread_crawler(
        input_csv=args.input,
        output_csv=args.output,
        target_count=args.number,
        max_workers=args.workers,
        limit=args.limit,
        start_from=args.start_from
    )

if __name__ == "__main__":
    main()
