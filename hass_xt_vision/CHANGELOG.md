# Changelog

## [1.2.1] - 2026-06-30

### Fixed
- Gửi ảnh chụp snapshot định kỳ mỗi 2 giây/lần lên thực thể camera trong Home Assistant (giúp thực thể camera luôn hiển thị ảnh xem trước trực tiếp thay vì bị trống khi chưa phát hiện chuyển động).

---

## [1.2.0] - 2026-06-29

### Added
- Tích hợp Bảng cài đặt trực tuyến toàn bộ thông số RTSP và MQTT trực tiếp trên Web UI.
- Thêm tính năng tự động liên kết MQTT Service Integration (`services: - mqtt:need`).
- Hiển thị chi tiết lý do trạng thái kết nối MQTT trên thẻ badge Web UI.

### Fixed
- Khắc phục lỗi luồng video đen trên Home Assistant Ingress bằng cơ chế snapshot polling ~15 FPS.
- Tự động thay thế ảnh chờ "Connecting..." loại bỏ hoàn toàn lỗi 404 snapshot.
- Bắt buộc giao thức FFMPEG TCP Transport giúp kết nối camera RTSP cực kỳ ổn định.
- Tự động fallback kết nối ngầm sang `core-mosquitto` khi chạy dưới dạng HA Add-on.

---

## [1.1.0] - 2026-06-29

### Added
- Thêm huy hiệu hiển thị phiên bản v1.1.0 trực quan trên thanh Web UI Navbar.
- Bổ sung file CHANGELOG.md hiển thị lịch sử cập nhật trong Home Assistant.

### Fixed
- Tương thích hoàn toàn với thư viện `paho-mqtt` v2.0+ mới nhất.
- Tự động nhận diện đường dẫn tương đối tương thích 100% với Home Assistant Ingress Proxy.
- Tối ưu hóa quy trình tự động build Docker image đa kiến trúc (AMD64 & ARM64).

---

## [1.0.0] - 2026-06-28

### Added
- Khởi tạo hệ thống HASS-XT AI Vision Camera cho Home Assistant.
- Xử lý luồng RTSP đa luồng kết hợp lọc chuyển động OpenCV MOG2.
- Nhận diện vật thể AI (Người, Xe, Vật nuôi) và tự động vẽ Bounding Box.
- Đồng bộ thực thể tự động qua Home Assistant MQTT Auto-Discovery.
