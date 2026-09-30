# ⚡ TikTok Video Scraper By Location & Hashtag (High-Speed Multithreaded)

Công cụ tự động thu thập và bóc tách danh sách link video TikTok theo từ khóa địa điểm (Phường, Thành phố) và Hashtag với **tốc độ cao nhờ công nghệ đa luồng (Multithreading Parallel Scanning)**.

---

## 🌟 Tính Năng Nổi Bật & Tối Ưu Tốc Độ

* 🚀 **Quét đa luồng siêu tốc (Multithreaded Concurrent Workers)**: Cho phép chạy từ **5 đến 10+ luồng song song cùng lúc** (`--workers 5`), giúp rút ngắn thời gian quét toàn bộ 700+ địa điểm từ 60 phút xuống chỉ còn **5 - 8 phút** (nhanh gấp 5-10 lần).
* 🛡️ **Tự phục hồi & Cách ly kết nối theo luồng**: Mỗi worker thread tự khởi tạo và giải phóng kết nối độc lập, tự động retry khi gặp lỗi TLS/HTTP2 ngắt mạng.
* 🔒 **Ghi file an toàn đa luồng (Thread-safe Lock)**: Sử dụng cơ chế khóa luồng `threading.Lock()` đảm bảo dữ liệu ghi xuống CSV không bị đè hay trùng lặp.
* 💾 **Ghi dữ liệu thời gian thực & Khôi phục tiến độ**: Tự động lưu tức thì và bỏ qua các địa điểm đã quét trong file kết quả cũ nếu khởi chạy lại.
* 📍 **Tùy chọn điểm bắt đầu (`--start-from`)**: Cho phép bắt đầu quét từ một địa điểm bất kỳ trong danh sách (ví dụ: `Hà Đông, Hà Nội`).

---

## 📁 Cấu Trúc Thư Mục

```text
build_data/
│
├── crawl_quan_an_phuong_fast.py # Tool cào video ĐA LUỒNG SIÊU TỐC theo phường (Khuyên dùng)
├── crawl_quan_an_phuong.py      # Tool cào video tuần tự tiêu chuẩn
├── scrape_tiktok_ddgs.py        # Tool cào video theo hashtag/từ khóa đơn lẻ
├── danh_sach_phuong.csv         # File danh sách phường/thành phố đầu vào
├── ket_qua_quan_an_phuong.csv   # File xuất kết quả tổng hợp (tự động tạo)
├── requirements.txt             # Danh sách thư viện Python cần thiết
└── README.md                    # Tài liệu hướng dẫn sử dụng
```

---

## 🚀 Hướng Dẫn Cài Đặt

```bash
pip install -r requirements.txt
```

---

## 💡 Hướng Dẫn Sử Dụng Tool Đa Luồng Siêu Tốc (`crawl_quan_an_phuong_fast.py`)

### 1. Chạy đa luồng song song toàn bộ danh sách (Mặc định 5 luồng):
```bash
python crawl_quan_an_phuong_fast.py -w 5 -n 15
```

### 2. Tăng tốc tối đa với 10 luồng song song:
```bash
python crawl_quan_an_phuong_fast.py -w 10 -n 15
```

### 3. Chạy bắt đầu từ địa điểm cụ thể (ví dụ: Hà Đông) với 5 luồng:
```bash
python crawl_quan_an_phuong_fast.py -s "Hà Đông" -w 5 -n 15
```

### 4. Thử nghiệm nhanh 10 địa điểm đầu tiên:
```bash
python crawl_quan_an_phuong_fast.py -l 10 -w 5 -n 15
```

---

## ⚙️ Bảng Bật Tham Số Hỗ Trợ

| Tham số | Ý nghĩa | Mặc định |
| :--- | :--- | :--- |
| **`-w`**, **`--workers`** | Số luồng chạy song song cùng lúc | `5` |
| **`-n`**, **`--number`** | Số lượng video tối đa lấy cho mỗi địa điểm | `15` |
| **`-s`**, **`--start-from`** | Địa điểm bắt đầu quét trong danh sách | Không chọn |
| **`-l`**, **`--limit`** | Giới hạn số lượng địa điểm muốn quét | Toàn bộ |
| **`-i`**, **`--input`** | Đường dẫn file CSV đầu vào | `danh_sach_phuong.csv` |
| **`-o`**, **`--output`** | Đường dẫn file CSV đầu ra | `ket_qua_quan_an_phuong.csv` |
