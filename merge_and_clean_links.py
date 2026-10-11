import csv
import glob
import os
import sys
import re

# Force UTF-8 output encoding for Windows terminal compatibility
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

def is_valid_tiktok_video(row):
    """
    Kiểm tra một dòng dữ liệu video TikTok có hợp lệ (không phải link rác) hay không.
    """
    # Lấy thông tin từ các cột trong file CSV
    phuong = row.get('phuong', '').strip()
    thanh_pho = row.get('thanh_pho', '').strip()
    query = row.get('search_query', row.get('search_keyword', '')).strip()
    video_id = row.get('video_id', row.get('id', '')).strip()
    author = row.get('author', '').strip()
    url = row.get('video_url', row.get('webVideoUrl', '')).strip()
    title = row.get('title', '').strip()
    snippet = row.get('snippet', '').strip()

    # 1. Kiểm tra URL phải bắt đầu bằng https://www.tiktok.com/@... hoặc https://tiktok.com/@...
    if not (url.startswith("https://www.tiktok.com/") or url.startswith("https://tiktok.com/")):
        return False, "Không phải tên miền tiktok.com tiêu chuẩn"

    # Không nhận subdomain phụ kiểu support16-normal-...
    if "support" in url or "nbcmiami" in url:
        return False, "Link tên miền rác/subdomain phụ"

    # 2. Kiểm tra định dạng URL phải có dạng @username/video/123456789
    match = re.search(r'tiktok\.com/@([^/]+)/video/(\d+)', url)
    if not match:
        return False, "URL không đúng cấu trúc @username/video/id"

    extracted_author = match.group(1).strip()
    extracted_id = match.group(2).strip()

    # Tác giả không được rỗng hoặc là kí tự rác như '_sauce90' không chính xác hoặc rỗng
    if not extracted_author or extracted_author in ['/video', '', '_']:
        return False, "Tác giả bị rỗng hoặc rác"

    # Cập nhật thông tin tác giả và video_id chuẩn hóa từ URL nếu thiếu
    if not author:
        author = extracted_author
    if not video_id:
        video_id = extracted_id

    # 3. Lọc bỏ các thông báo lỗi / trang bị xóa / private / 404 dựa trên title và snippet
    combined_text = (title + " " + snippet).lower()
    
    junk_keywords = [
        "redirecting to /404",
        "/404?fromurl=",
        "this account is private",
        "video currently unavailable",
        "4 0 4 couldn't find this page",
        "log in to tiktok",
        "this post may not be comfortable",
        "tiktok for goodadvertisesell on tiktok",
        "couldn't find this page",
        "support16-normal",
        "video unavailable"
    ]
    
    for kw in junk_keywords:
        if kw in combined_text:
            return False, f"Chứa nội dung trang lỗi/chặn: '{kw}'"

    # Trả về kết quả dòng dữ liệu đã được chuẩn hóa
    clean_row = {
        'phuong': phuong,
        'thanh_pho': thanh_pho,
        'search_query': query,
        'video_id': video_id,
        'author': author,
        'video_url': f"https://www.tiktok.com/@{author}/video/{video_id}",
        'title': title,
        'snippet': snippet
    }
    return True, clean_row

def merge_and_clean_csv_files(input_folder, output_csv):
    csv_files = glob.glob(os.path.join(input_folder, "*.csv"))
    print(f"[*] Tìm thấy {len(csv_files)} file CSV trong thư mục: {input_folder}")
    for f in csv_files:
        print(f" - {os.path.basename(f)} ({os.path.getsize(f):,} bytes)")

    total_read_rows = 0
    total_junk_rows = 0
    total_duplicate_rows = 0
    clean_rows = []
    seen_video_ids = set()

    for file_path in csv_files:
        if os.path.abspath(file_path) == os.path.abspath(output_csv):
            continue
            
        print(f"\n[*] Đang xử lý file: {os.path.basename(file_path)}...")
        with open(file_path, mode='r', encoding='utf-8-sig', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_read_rows += 1
                
                is_valid, res = is_valid_tiktok_video(row)
                if not is_valid:
                    total_junk_rows += 1
                    continue
                    
                v_id = res['video_id']
                if v_id in seen_video_ids:
                    total_duplicate_rows += 1
                    continue
                    
                seen_video_ids.add(v_id)
                clean_rows.append(res)

    print(f"\n==========================================")
    print(f"📊 BÁO CÁO KẾT QUẢ GỘP & LỌC DỮ LIỆU:")
    print(f" - Tổng số dòng đọc vào: {total_read_rows:,} dòng")
    print(f" - Số dòng link rác bị loại bỏ: {total_junk_rows:,} dòng")
    print(f" - Số dòng trùng lặp link bị loại: {total_duplicate_rows:,} dòng")
    print(f" - Số link video TikTok sạch thu được: {len(clean_rows):,} dòng")
    print(f"==========================================")

    # Ghi xuất file CSV mới sạch 100%
    fieldnames = ['phuong', 'thanh_pho', 'search_query', 'video_id', 'author', 'video_url', 'title', 'snippet']
    with open(output_csv, mode='w', newline='', encoding='utf-8-sig') as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(clean_rows)

    print(f"\n[🎉] Đã lưu file sạch thành công tại: {output_csv}")

if __name__ == "__main__":
    input_dir = r"D:\year_4\pbl\build_data\danh_sach_link"
    output_file = r"D:\year_4\pbl\build_data\danh_sach_link\ket_qua_quan_an_gop_sach.csv"
    merge_and_clean_csv_files(input_dir, output_file)
