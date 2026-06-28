document.addEventListener("DOMContentLoaded", () => {
    const mqttBadge = document.getElementById("mqtt-badge");
    const fpsBadge = document.getElementById("fps-badge");
    const motionBadge = document.getElementById("motion-badge");
    const countValue = document.getElementById("count-value");
    const personStatus = document.getElementById("person-status");
    const detectionsList = document.getElementById("detections-list");

    const sensitivityInput = document.getElementById("sensitivity-input");
    const sensitivityVal = document.getElementById("sensitivity-val");
    const confidenceInput = document.getElementById("confidence-input");
    const confidenceVal = document.getElementById("confidence-val");
    const saveBtn = document.getElementById("save-btn");

    // Dynamic slider label update
    sensitivityInput.addEventListener("input", (e) => {
        sensitivityVal.textContent = e.target.value;
    });

    confidenceInput.addEventListener("input", (e) => {
        confidenceVal.textContent = parseFloat(e.target.value).toFixed(2);
    });

    // Load initial config
    async function loadConfig() {
        try {
            const res = await fetch("/api/config");
            const data = await res.json();
            sensitivityInput.value = data.motion_sensitivity;
            sensitivityVal.textContent = data.motion_sensitivity;
            confidenceInput.value = data.ai_confidence;
            confidenceVal.textContent = parseFloat(data.ai_confidence).toFixed(2);
        } catch (err) {
            console.error("Error loading config:", err);
        }
    }

    // Save config
    saveBtn.addEventListener("click", async () => {
        try {
            const payload = {
                motion_sensitivity: parseInt(sensitivityInput.value),
                ai_confidence: parseFloat(confidenceInput.value)
            };
            const res = await fetch("/api/config", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            alert("Đã lưu cấu hình mới thành công!");
        } catch (err) {
            alert("Lỗi khi lưu cấu hình!");
        }
    });

    // Poll telemetry status
    async function updateStatus() {
        try {
            const res = await fetch("/api/status");
            const data = await res.json();

            // MQTT status
            if (data.mqtt_connected) {
                mqttBadge.textContent = "MQTT: Connected";
                mqttBadge.className = "badge badge-connected";
            } else {
                mqttBadge.textContent = "MQTT: Disconnected";
                mqttBadge.className = "badge badge-disconnected";
            }

            // FPS
            fpsBadge.textContent = `FPS: ${data.fps}`;

            // Motion Badge
            if (data.motion_detected) {
                motionBadge.textContent = "CẢNH BÁO CHUYỂN ĐỘNG";
                motionBadge.className = "badge badge-alert";
            } else {
                motionBadge.textContent = "KÍNH TRONG";
                motionBadge.className = "badge badge-clear";
            }

            // Object Count
            countValue.textContent = data.detections_count;

            // Person Status
            const hasPerson = data.detections.some(d => d.class === "person");
            personStatus.textContent = hasPerson ? "Có người!" : "Không";
            personStatus.style.color = hasPerson ? "#ef4444" : "#38bdf8";

            // Detections List
            if (data.detections.length === 0) {
                detectionsList.innerHTML = '<p class="empty-msg">Chưa phát hiện chuyển động nào...</p>';
            } else {
                detectionsList.innerHTML = data.detections.map(d => `
                    <div class="detection-item">
                        <span><strong>${d.class.toUpperCase()}</strong></span>
                        <span class="badge badge-info">${Math.round(d.confidence * 100)}%</span>
                    </div>
                `).join('');
            }
        } catch (err) {
            console.error("Error polling status:", err);
        }
    }

    loadConfig();
    setInterval(updateStatus, 1000);
});
