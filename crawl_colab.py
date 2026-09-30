# ==============================================================================
# TIKTOK VIDEO SCRAPER - GOOGLE DRIVE & GOOGLE COLAB INTEGRATED EDITION
# Tự động đọc dữ liệu đầu vào và lưu kết quả trực tiếp lên Google Drive
# ==============================================================================

import csv
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from ddgs import DDGS

# Khóa luồng đảm bảo ghi file và in log an toàn trong Colab
csv_lock = threading.Lock()
print_lock = threading.Lock()

def safe_print(msg: str):
    with print_lock:
        print(msg)
        sys.stdout.flush()

def mount_google_drive():
    """Tự động kết nối với Google Drive trên môi trường Colab."""
    try:
        from google.colab import drive
        drive_path = '/content/drive'
        if not os.path.exists(drive_path + '/MyDrive'):
            safe_print("[*] Đang kết nối với Google Drive của bạn...")
            drive.mount(drive_path, force_remount=False)
            safe_print("✅ Kết nối Google Drive thành công!")
        else:
            safe_print("✅ Google Drive đã được kết nối từ trước.")
        return True
    except Exception as e:
        safe_print(f"[!] Không ở trong môi trường Google Colab hoặc kết nối Drive thất bại: {e}")
        return False

def resolve_file_path(filename: str, default_drive_dir: str = "/content/drive/MyDrive") -> str:
    """
    Tự động định vị file: 
    Ưu tiên đường dẫn trong Google Drive (/content/drive/MyDrive/filename),
    nếu không có sẽ dùng đường dẫn thư mục hiện tại.
    """
    drive_file_path = os.path.join(default_drive_dir, filename)
    if os.path.exists(drive_file_path):
        return drive_file_path
    elif os.path.exists(filename):
        return filename
    return drive_file_path  # Mặc định trả về đường dẫn Google Drive để lưu mới

def get_processed_locations(output_csv_path: str) -> set:
    """Đọc tập hợp các địa điểm (phuong, thanh_pho) đã quét trước đó để bỏ qua (Resume Mode)."""
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
    """Thực hiện truy vấn với cơ chế tự tạo lại session DDGS và tự động thử lại khi trễ mạng."""
    for attempt in range(1, max_retries + 1):
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                return results
        except Exception:
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

def run_colab_drive_scraper(input_filename: str = "danh_sach_phuong.csv", 
                            output_filename: str = "ket_qua_quan_an_phuong.csv", 
                            drive_folder: str = "/content/drive/MyDrive",
                            target_count: int = 15, 
                            max_workers: int = 5, 
                            start_from: str = None,
                            limit: int = None):
    """Hàm chạy chính tự động kết nối và đồng bộ trực tiếp với Google Drive."""
    # Kết nối với Google Drive
    mount_google_drive()
    
    # Xác định đường dẫn file trên Google Drive
    input_path = resolve_file_path(input_filename, drive_folder)
    output_path = os.path.join(drive_folder, output_filename) if os.path.exists(drive_folder) else output_filename

    safe_print(f"📂 File danh sách đầu vào: {input_path}")
    safe_print(f"💾 File kết quả xuất trên Google Drive: {output_path}")

    if not os.path.exists(input_path):
        safe_print(f"[!] Lỗi: Không tìm thấy file '{input_path}' trên Google Drive!")
        safe_print(f"💡 Vui lòng copy file '{input_filename}' vào thư mục Google Drive của bạn ({drive_folder})!")
        return

    processed_locations = get_processed_locations(output_path)
    if processed_locations:
        safe_print(f"[*] Đã tìm thấy {len(processed_locations)} địa điểm đã quét trong file kết quả trên Drive. Sẽ tự động bỏ qua.")

    locations = []
    with open(input_path, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            phuong = row.get('Tên', '').strip()
            thanh_pho = row.get('Thành Phố', '').strip()
            if phuong and thanh_pho:
                locations.append((phuong, thanh_pho))

    safe_print(f"[*] Tổng số địa điểm trong file gốc: {len(locations)}")

    # Xử lý điểm bắt đầu (start_from) nếu có
    if start_from:
        start_clean = start_from.strip().lower()
        start_idx = None
        for i, (p, tp) in enumerate(locations):
            full_str = f"{p},{tp}".lower()
            if start_clean in full_str or start_clean in f"{p} {tp}".lower() or start_clean in p.lower():
                start_idx = i
                safe_print(f"[*] Đã định vị điểm bắt đầu tại dòng {i+1}: '{p}, {tp}'")
                break
        if start_idx is not None:
            locations = locations[start_idx:]

    unprocessed = [loc for loc in locations if loc not in processed_locations]
    safe_print(f"[*] Số địa điểm còn lại cần quét: {len(unprocessed)}")

    if limit and limit > 0:
        unprocessed = unprocessed[:limit]
        safe_print(f"[*] Giới hạn quét {limit} địa điểm trong đợt này.")

    if not unprocessed:
        safe_print("[+] Tất cả địa điểm được chọn đã được quét xong hoàn tất!")
        return

    file_exists = os.path.exists(output_path) and os.path.getsize(output_path) > 0
    fieldnames = ['phuong', 'thanh_pho', 'search_keyword', 'id', 'author', 'webVideoUrl', 'title', 'snippet']

    if not file_exists:
        # Tạo thư mục trên Google Drive nếu chưa tồn tại
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, mode='a', newline='', encoding='utf-8-sig') as f_out:
            writer = csv.DictWriter(f_out, fieldnames=fieldnames)
            writer.writeheader()

    start_time = time.time()
    completed_count = 0
    total_to_process = len(unprocessed)
    
    safe_print(f"\n🚀 ĐANG CHẠY ĐA LUỒNG - DỮ LIỆU TỰ ĐỘNG ĐỒNG BỘ TRỰC TIẾP LÊN GOOGLE DRIVE...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_loc = {
            executor.submit(process_single_location, p, tp, target_count): (p, tp) 
            for (p, tp) in unprocessed
        }
        for future in as_completed(future_to_loc):
            p, tp = future_to_loc[future]
            try:
                res_phuong, res_tp, vids = future.result()
                completed_count += 1
                if vids:
                    with csv_lock:
                        with open(output_path, mode='a', newline='', encoding='utf-8-sig') as f_out:
                            writer = csv.DictWriter(f_out, fieldnames=fieldnames)
                            writer.writerows(vids)
                            f_out.flush()
                    safe_print(f"[{completed_count}/{total_to_process}]  {res_phuong}, {res_tp} -> Đã lưu {len(vids)}/{target_count} video lên Google Drive")
                else:
                    safe_print(f"[{completed_count}/{total_to_process}] ⚠️ {res_phuong}, {res_tp} -> 0 video")
            except Exception as exc:
                safe_print(f"[!] Lỗi khi xử lý {p}, {tp}: {exc}")

    elapsed = time.time() - start_time
    safe_print(f"\n[🎉] ĐÃ HOÀN THÀNH {completed_count} ĐỊA ĐIỂM TRONG {elapsed:.1f} GIÂY!")
    safe_print(f"📁 Dữ liệu đã lưu an toàn trên Google Drive tại: {output_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Tool cào video TikTok hỗ trợ kết nối Google Drive")
    parser.add_argument("-i", "--input", type=str, default="danh_sach_phuong.csv")
    parser.add_argument("-o", "--output", type=str, default="ket_qua_quan_an_phuong.csv")
    parser.add_argument("-folder", "--drive-folder", type=str, default="/content/drive/MyDrive")
    parser.add_argument("-n", "--number", type=int, default=15)
    parser.add_argument("-w", "--workers", type=int, default=5)
    parser.add_argument("-s", "--start-from", type=str, default=None)
    parser.add_argument("-l", "--limit", type=int, default=None)

    args = parser.parse_args()
    run_colab_drive_scraper(
        input_filename=args.input, 
        output_filename=args.output, 
        drive_folder=args.drive_folder,
        target_count=args.number, 
        max_workers=args.workers, 
        start_from=args.start_from, 
        limit=args.limit
    )
