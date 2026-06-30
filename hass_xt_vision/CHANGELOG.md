# Changelog

## [2.1.0] - 2026-06-30

### Added
- Tích hợp tính năng chẩn đoán kết nối toàn diện: Kiểm tra đồng thời kết nối Home Assistant API, AI Proxy (Vision API), và MQTT Broker từ Web UI, hiển thị kết quả chẩn đoán chi tiết và tô màu trạng thái trực quan bên cạnh các trường nhập dữ liệu.
- Bổ sung công cụ kiểm tra độc lập và chi tiết kết nối API tới Telegram Bot.
- Tích hợp thông báo qua Telegram: Tự động gửi ảnh chụp thực thể (photo) kèm mô tả chi tiết của AI dưới dạng chú thích (caption) tới Chat ID nhóm hoặc cá nhân của người dùng ngay sau khi phân tích thành công. Dự phòng gửi tin nhắn văn bản thuần túy nếu gửi ảnh thất bại.
- Định dạng danh sách lựa chọn nhanh thực thể có sẵn từ Home Assistant theo phong cách trực quan: `entity_id · friendly_name · domain`.

### Optimized
- Thêm bộ lọc trùng lặp ảnh (MD5 Image Hash Compare): Tự động tính toán mã băm ảnh chụp camera, nếu ảnh không thay đổi so với lần phân tích thành công trước đó thì tự động bỏ qua cuộc gọi API tới AI Proxy, giảm thiểu đáng kể chi phí token AI và tránh tạo các bản ghi lịch sử trùng lặp vô ích. Cho phép bỏ qua bộ lọc này khi người dùng thực hiện chạy quét thủ công (Force Scan).

### Changed
- Nâng cấp Addon thành **AI Vision Entity Describer Addon** phiên bản v2.1.0, chạy uvicorn trên cổng mới `1237`.

---

## [1.2.2] - 2026-06-30

### Fixed
- Sửa lỗi cú pháp phân tách tùy chọn FFMPEG (`rtsp_transport|tcp`) sử dụng ký tự gạch đứng `|` tương thích hoàn hảo với môi trường Docker Linux trên Home Assistant (khắc phục lỗi *Unable to parse option value*).

---

## [1.2.1] - 2026-06-30

### Fixed
- Khắc phục lỗi hiển thị camera thực thể trống trên giao diện Home Assistant bằng cách tự động đồng bộ khung hình snapshot định kỳ 2 giây.

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
