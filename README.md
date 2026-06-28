# 👁️ HASS-XT Vision - Home Assistant AI Camera Add-on Repository

[![Home Assistant Add-on](https://img.shields.io/badge/Home%20Assistant-Add--on-blue.svg)](https://www.home-assistant.io/)
[![Python 3.11](https://img.shields.io/badge/python-3.11-brightgreen.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Kho lưu trữ chính thức cho **HASS-XT AI Vision** - Add-on camera thông minh tích hợp AI phát hiện chuyển động và nhận diện vật thể (Người, Xe hơi, Vật nuôi) cho **Home Assistant**.

---

## 🛠️ Hướng Dẫn Thêm Cửa Hàng (Repository) vào Home Assistant

1. Mở Home Assistant của bạn.
2. Truy cập vào **Settings** -> **Add-ons** -> **Add-on Store**.
3. Nhấn vào dấu 3 chấm góc trên bên phải, chọn **Repositories**.
4. Dán đường dẫn repository này vào:
   ```text
   https://github.com/xtapo/HASS-XT
   ```
5. Nhấn **Add**. Tìm **HASS-XT AI Vision** trong danh sách cửa hàng, chọn **Install** và cấu hình RTSP URL cùng MQTT Broker!

---

## ✨ Tính Năng Nổi Bật

- 🚀 **Tối Ưu CPU & RAM**: Sử dụng thuật toán OpenCV MOG2 lọc chuyển động trước khi kích hoạt mô hình AI.
- 🎯 **Nhận Diện AI Chính Xác**: Nhận diện vật thể (Person, Car, Dog, Cat) và tự động vẽ Bounding Box trực quan.
- 📡 **Home Assistant MQTT Auto-Discovery**: Tự động khai báo thực thể trong Home Assistant không cần cấu hình YAML thủ công.
- 💻 **Web Dashboard Hiện Đại**: Giao diện Dark Mode Glassmorphic hỗ trợ xem luồng video trực tiếp (MJPEG Live Stream).

---

## 💻 Khởi Chạy Độc Lập (Docker / Local App)

Mã nguồn Add-on nằm trong thư mục [`hass_xt_vision`](hass_xt_vision/).

### Triển khai bằng Docker:
```bash
cd hass_xt_vision
docker build -t hass-xt-vision .
docker run -d -p 8000:8000 -e RTSP_URL="rtsp://192.168.1.100:554/stream1" hass-xt-vision
```

### Chạy trực tiếp bằng Python:
```bash
cd hass_xt_vision
pip install -r requirements.txt
python -m app.main
```
Truy cập Web UI tại: `http://localhost:8000`

---

## 📄 Giấy Phép (License)

Dự án được phát hành dưới giấy phép **MIT License**. Chi tiết xem tại file [LICENSE](LICENSE).
