# Changelog

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
