document.addEventListener("DOMContentLoaded", () => {
    const liveStream = document.getElementById("live-stream");
    const versionBadge = document.getElementById("version-badge");
    const mqttBadge = document.getElementById("mqtt-badge");
    const fpsBadge = document.getElementById("fps-badge");
    const motionBadge = document.getElementById("motion-badge");
    const countValue = document.getElementById("count-value");
    const personStatus = document.getElementById("person-status");
    const detectionsList = document.getElementById("detections-list");

    const rtspUrlInput = document.getElementById("rtsp-url-input");
    const mqttHostInput = document.getElementById("mqtt-host-input");
    const mqttPortInput = document.getElementById("mqtt-port-input");
    const mqttUserInput = document.getElementById("mqtt-user-input");
    const mqttPassInput = document.getElementById("mqtt-pass-input");

    const sensitivityInput = document.getElementById("sensitivity-input");
    const sensitivityVal = document.getElementById("sensitivity-val");
    const confidenceInput = document.getElementById("confidence-input");
    const confidenceVal = document.getElementById("confidence-val");
    const saveBtn = document.getElementById("save-btn");

    function getBaseUrl() {
        let path = window.location.pathname;
        if (!path.endsWith('/')) {
            path += '/';
        }
        return path;
    }

    const baseUrl = getBaseUrl();

    // Fast image stream updating compatible with HA Ingress
    let streamActive = true;
    function updateLiveStream() {
        if (!streamActive || !liveStream) return;
        const img = new Image();
        img.onload = () => {
            liveStream.src = img.src;
            setTimeout(updateLiveStream, 66); // ~15 FPS
        };
        img.onerror = () => {
            setTimeout(updateLiveStream, 500);
        };
        img.src = baseUrl + "api/snapshot?t=" + Date.now();
    }
    updateLiveStream();

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
            const res = await fetch(baseUrl + "api/config");
            const data = await res.json();
            if (rtspUrlInput) rtspUrlInput.value = data.rtsp_url || "";
            if (mqttHostInput) mqttHostInput.value = data.mqtt_host || "";
            if (mqttPortInput) mqttPortInput.value = data.mqtt_port || 1883;
            if (mqttUserInput) mqttUserInput.value = data.mqtt_user || "";
            if (mqttPassInput) mqttPassInput.value = data.mqtt_password || "";

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
                rtsp_url: rtspUrlInput.value.trim(),
                mqtt_host: mqttHostInput.value.trim(),
                mqtt_port: parseInt(mqttPortInput.value) || 1883,
                mqtt_user: mqttUserInput.value.trim(),
                mqtt_password: mqttPassInput.value.trim(),
                motion_sensitivity: parseInt(sensitivityInput.value),
                ai_confidence: parseFloat(confidenceInput.value)
            };

            saveBtn.textContent = "Đang áp dụng...";
            saveBtn.disabled = true;

            const res = await fetch(baseUrl + "api/config", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            alert("Đã lưu và áp dụng cấu hình mới thành công!");
        } catch (err) {
            alert("Lỗi khi lưu cấu hình!");
        } finally {
            saveBtn.textContent = "Lưu Cấu Hình Tức Thời";
            saveBtn.disabled = false;
        }
    });

    // Poll telemetry status
    async function updateStatus() {
        try {
            const res = await fetch(baseUrl + "api/status");
            const data = await res.json();

            // Version
            if (versionBadge && data.version) {
                versionBadge.textContent = "v" + data.version;
            }

            // MQTT status
            if (data.mqtt_connected) {
                mqttBadge.textContent = "MQTT: Connected";
                mqttBadge.className = "badge badge-connected";
            } else {
                const text = data.mqtt_status_text || "Disconnected";
                mqttBadge.textContent = "MQTT: " + text;
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
