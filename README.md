# 👁️ HASS-XT Vision - Home Assistant AI Camera Add-on & Standalone App

[![Home Assistant Add-on](https://img.shields.io/badge/Home%20Assistant-Add--on-blue.svg)](https://www.home-assistant.io/)
[![Python 3.11](https://img.shields.io/badge/python-3.11-brightgreen.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**HASS-XT Vision** là ứng dụng camera thông minh tích hợp AI phát hiện chuyển động và nhận diện vật thể (Người, Xe hơi, Vật nuôi) cho **Home Assistant**. Hệ thống hỗ trợ kết nối RTSP Stream, tự động khai báo thực thể qua **MQTT Auto-Discovery** và cung cấp **Web Dashboard** hiện đại trực quan.

---

## ✨ Tính Năng Nổi Bật

- 🚀 **Tối Ưu CPU & RAM**: Sử dụng thuật toán OpenCV MOG2 lọc chuyển động trước khi kích hoạt mô hình AI, giảm tải tối đa cho phần cứng nhỏ gọn như Raspberry Pi.
- 🎯 **Nhận Diện AI Chính Xác**: Nhận diện vật thể (Person, Car, Dog, Cat) và tự động vẽ Bounding Box trực quan.
- 📡 **Home Assistant MQTT Auto-Discovery**: Tự động khai báo thực thể trong Home Assistant không cần cấu hình YAML thủ công:
  - `binary_sensor.<device>_motion` (Cảm biến phát hiện chuyển động)
  - `binary_sensor.<device>_person` (Cảm biến phát hiện có người)
  - `sensor.<device>_count` (Bộ đếm số lượng vật thể)
  - `camera.<device>_snapshot` (Thực thể camera chụp ảnh kèm Bounding Box AI)
- 💻 **Web Dashboard Hiện Đại**: Giao diện Dark Mode Glassmorphic hỗ trợ xem luồng video trực tiếp (MJPEG Live Stream), theo dõi thông số FPS và điều chỉnh độ nhạy theo thời gian thực.
- 📦 **Đa Dạng Phương Thức Triển Khai**: Hoạt động mượt mà dưới dạng Home Assistant Add-on, Docker Container hoặc App Python độc lập.

---

## 🛠️ Hướng Dẫn Cài Đặt (Installation)

### 1. Cài đặt làm Home Assistant Add-on (Khuyên dùng)

1. Mở Home Assistant, truy cập **Settings** -> **Add-ons** -> **Add-on Store**.
2. Nhấn vào dấu 3 chấm góc trên bên phải, chọn **Repositories**.
3. Thêm URL GitHub repository này vào danh sách.
4. Tìm **HASS-XT AI Vision** trong danh sách **Local Add-ons**, nhấn **Install** và cấu hình RTSP URL cũng như thông tin MQTT Broker.
5. Nhấn **Start** và bật tùy chọn **Show in sidebar** để xem Web Dashboard.

### 2. Triển khai bằng Docker

```bash
# Clone repository
git clone https://github.com/your-username/HASS-XT.git
cd HASS-XT

# Build Docker image
docker build -t hass-xt-vision .

# Chạy Docker container
docker run -d \
  --name hass-xt-vision \
  -p 8000:8000 \
  -e RTSP_URL="rtsp://192.168.1.100:554/stream1" \
  -e MQTT_HOST="192.168.1.50" \
  -e MQTT_PORT="1883" \
  hass-xt-vision
```

### 3. Chạy trực tiếp bằng Python (Local Machine)

```bash
# Cài đặt thư viện
pip install -r requirements.txt

# Khởi chạy ứng dụng
python -m app.main
```
Truy cập Web UI tại: `http://localhost:8000`

---

## ⚙️ Cấu Hình (Configuration Options)

| Tham Số | Mô Tả | Mặc Định |
| :--- | :--- | :--- |
| `rtsp_url` | Đường dẫn RTSP stream từ Camera IP | `rtsp://...` |
| `mqtt_host` | Địa chỉ IP/Hostname của MQTT Broker | `core-mosquitto` / `localhost` |
| `mqtt_port` | Cổng kết nối MQTT Broker | `1883` |
| `mqtt_user` | Tài khoản MQTT (nếu có) | `""` |
| `mqtt_password` | Mật khẩu MQTT (nếu có) | `""` |
| `motion_sensitivity` | Độ nhạy phát hiện chuyển động (5 - 100) | `25` |
| `ai_confidence` | Ngưỡng tin cậy AI (0.1 - 0.9) | `0.5` |

---

## 📄 Giấy Phép (License)

Dự án được phát hành dưới giấy phép **MIT License**. Chi tiết xem tại file [LICENSE](LICENSE).
