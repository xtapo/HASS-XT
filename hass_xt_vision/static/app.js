// AI Vision Entity Describer Frontend Controller

// DOM Elements
const haUrlInput = document.getElementById('ha-url-input');
const haTokenInput = document.getElementById('ha-token-input');
const scanIntervalInput = document.getElementById('scan-interval-input');
const motionThresholdInput = document.getElementById('motion-threshold-input');
const aiBaseUrlInput = document.getElementById('ai-base-url-input');
const aiKeyInput = document.getElementById('ai-key-input');
const aiModelInput = document.getElementById('ai-model-input');
const aiPromptInput = document.getElementById('ai-prompt-input');
const mqttHostInput = document.getElementById('mqtt-host-input');
const mqttPortInput = document.getElementById('mqtt-port-input');
const mqttPrefixInput = document.getElementById('mqtt-prefix-input');
const mqttUserInput = document.getElementById('mqtt-user-input');
const mqttPassInput = document.getElementById('mqtt-pass-input');

const testHaBtn = document.getElementById('test-ha-btn');
const loadHaEntitiesBtn = document.getElementById('load-ha-entities-btn');
const haEntitiesStatus = document.getElementById('ha-entities-status');
const entityHelper = document.getElementById('entity-helper');
const entityPicker = document.getElementById('entity-picker');
const manualCameraIdInput = document.getElementById('manual-camera-id-input');
const addManualCameraBtn = document.getElementById('add-manual-camera-btn');

const testAllBtn = document.getElementById('test-all-btn');
const aiStatusText = document.getElementById('ai-status-text');
const mqttStatusText = document.getElementById('mqtt-status-text');
const tgTokenInput = document.getElementById('tg-token-input');
const tgChatInput = document.getElementById('tg-chat-input');
const tgStatusText = document.getElementById('tg-status-text');

const saveBtn = document.getElementById('save-btn');
const clearHistoryBtn = document.getElementById('clear-history-btn');
const manualScanSelect = document.getElementById('manual-scan-select');
const scanNowBtn = document.getElementById('scan-now-btn');
const historyList = document.getElementById('history-list');
const detailView = document.getElementById('detail-view');

const mqttBadge = document.getElementById('mqtt-badge');
const statusBadge = document.getElementById('status-badge');
const toastNotification = document.getElementById('notification-toast');

// Global State
let currentConfig = {};
let historyEntries = [];
let selectedEntryId = null;
let configuredCameras = [];
let cameraSettings = {};

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    fetchConfig();
    fetchStatus();
    fetchHistory();
    setupEventListeners();
    
    // Periodically poll status and history
    setInterval(fetchStatus, 5000);
    setInterval(fetchHistory, 10000);
});

// Setup Listeners
function setupEventListeners() {
    saveBtn.addEventListener('click', saveConfig);
    clearHistoryBtn.addEventListener('click', clearHistory);
    scanNowBtn.addEventListener('click', runManualScan);
    testHaBtn.addEventListener('click', testHAConnection);
    testAllBtn.addEventListener('click', testAllConnections);
    loadHaEntitiesBtn.addEventListener('click', queryHAEntities);
    
    // Picker listener to append entity
    entityPicker.addEventListener('change', (e) => {
        const val = e.target.value;
        if (!val) return;
        
        if (!configuredCameras.includes(val)) {
            configuredCameras.push(val);
            renderCameraList();
            showToast(`Đã thêm ${val} vào danh sách.`);
            updateManualTriggerDropdown();
        } else {
            showToast(`${val} đã tồn tại trong danh sách.`, true);
        }
        
        entityPicker.value = ''; // Reset picker selection
    });

    // Manual camera add button click
    addManualCameraBtn.addEventListener('click', () => {
        const val = manualCameraIdInput.value.trim();
        if (!val) {
            showToast('Vui lòng nhập entity_id!', true);
            return;
        }
        if (!val.includes('.')) {
            showToast('Entity ID không hợp lệ (ví dụ: camera.living_room)!', true);
            return;
        }
        
        if (!configuredCameras.includes(val)) {
            configuredCameras.push(val);
            renderCameraList();
            showToast(`Đã thêm ${val} vào danh sách.`);
            updateManualTriggerDropdown();
            manualCameraIdInput.value = '';
        } else {
            showToast(`${val} đã tồn tại trong danh sách.`, true);
        }
    });
}

// Show custom toast notification
function showToast(message, isError = false) {
    toastNotification.textContent = message;
    toastNotification.className = 'toast';
    if (isError) {
        toastNotification.style.borderLeft = '4px solid var(--danger)';
    } else {
        toastNotification.style.borderLeft = '4px solid var(--accent)';
    }
    toastNotification.classList.remove('hidden');
    
    setTimeout(() => {
        toastNotification.classList.add('hidden');
    }, 3500);
}

// Fetch configuration from FastAPI
async function fetchConfig() {
    try {
        const response = await fetch('api/config');
        if (!response.ok) throw new Error('Failed to load configuration');
        
        const data = await response.json();
        currentConfig = data;
        
        // Populate inputs
        haUrlInput.value = data.ha_url || '';
        haTokenInput.value = data.ha_token || '';
        
        // Populate global state and render
        configuredCameras = data.camera_entities || [];
        cameraSettings = data.camera_settings || {};
        renderCameraList();
        
        scanIntervalInput.value = data.scan_interval || 30;
        motionThresholdInput.value = data.motion_threshold !== undefined ? data.motion_threshold : 2.0;
        aiBaseUrlInput.value = data.ai_proxy_base_url || '';
        aiKeyInput.value = data.ai_api_key || '';
        aiModelInput.value = data.ai_model || '';
        aiPromptInput.value = data.ai_prompt || 'Hãy mô tả chi tiết hình ảnh này bằng tiếng Việt.';
        mqttHostInput.value = data.mqtt_host || 'core-mosquitto';
        mqttPortInput.value = data.mqtt_port || 1883;
        mqttPrefixInput.value = data.mqtt_prefix || 'ai_vision';
        mqttUserInput.value = data.mqtt_user || '';
        mqttPassInput.value = data.mqtt_password || '';
        tgTokenInput.value = data.telegram_bot_token || '';
        tgChatInput.value = data.telegram_chat_id || '';
        
        // Update manual select dropdown list
        updateManualTriggerDropdown();
        
        // Auto-query HA entities list if HA URL is valid to verify token
        if (data.ha_url) {
            queryHAEntities(false);
        }
    } catch (error) {
        console.error(error);
        showToast('Lỗi tải cấu hình!', true);
    }
}

// Save configuration to FastAPI
async function saveConfig() {
    saveBtn.disabled = true;
    saveBtn.textContent = 'Đang lưu...';
    
    const payload = {
        ha_url: haUrlInput.value.trim(),
        ha_token: haTokenInput.value.trim(),
        camera_entities: configuredCameras,
        camera_settings: cameraSettings,
        scan_interval: parseInt(scanIntervalInput.value) || 30,
        motion_threshold: parseFloat(motionThresholdInput.value) || 2.0,
        ai_proxy_base_url: aiBaseUrlInput.value.trim(),
        ai_api_key: aiKeyInput.value.trim(),
        ai_model: aiModelInput.value.trim(),
        mqtt_host: mqttHostInput.value.trim(),
        mqtt_port: parseInt(mqttPortInput.value) || 1883,
        mqtt_prefix: mqttPrefixInput.value.trim(),
        mqtt_user: mqttUserInput.value.trim(),
        mqtt_password: mqttPassInput.value.trim(),
        ai_prompt: aiPromptInput.value.trim(),
        telegram_bot_token: tgTokenInput.value.trim(),
        telegram_chat_id: tgChatInput.value.trim()
    };
    
    try {
        const response = await fetch('api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) throw new Error('Save failed');
        
        showToast('Cấu hình đã lưu thành công!');
        fetchConfig(); // Reload
        fetchStatus();
    } catch (error) {
        console.error(error);
        showToast('Không thể lưu cấu hình!', true);
    } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = 'Lưu Cấu Hình';
    }
}

// Fetch general status info
async function fetchStatus() {
    try {
        const response = await fetch('api/status');
        if (!response.ok) throw new Error('Status check failed');
        
        const data = await response.json();
        
        // MQTT status badge update
        mqttBadge.textContent = `MQTT: ${data.mqtt_status_text}`;
        mqttBadge.className = 'badge';
        if (data.mqtt_connected) {
            mqttBadge.classList.add('badge-success');
        } else if (data.mqtt_status_text.startsWith('Connecting')) {
            mqttBadge.classList.add('badge-info');
        } else {
            mqttBadge.classList.add('badge-disconnected');
        }
        
        statusBadge.textContent = 'API: Online';
        statusBadge.className = 'badge badge-success';
    } catch (error) {
        statusBadge.textContent = 'API: Offline';
        statusBadge.className = 'badge badge-danger';
    }
}

// Fetch SQLite history entries
async function fetchHistory() {
    try {
        const response = await fetch('api/history?limit=40');
        if (!response.ok) throw new Error('Failed to load history');
        
        const data = await response.json();
        historyEntries = data;
        
        renderHistoryList();
    } catch (error) {
        console.error(error);
        historyList.innerHTML = `<p class="empty-msg text-danger">Lỗi tải dữ liệu lịch sử.</p>`;
    }
}

// Render the scrollable log history column
function renderHistoryList() {
    if (historyEntries.length === 0) {
        historyList.innerHTML = `<p class="empty-msg">Chưa có bản ghi lịch sử vision nào.</p>`;
        return;
    }
    
    let html = '';
    historyEntries.forEach(entry => {
        const isActive = selectedEntryId === entry.id ? 'active' : '';
        const isSuccess = entry.status === 'success';
        const badgeClass = isSuccess ? 'badge-success' : 'badge-danger';
        const badgeText = isSuccess ? 'Thành công' : 'Lỗi';
        
        // Resolve image source
        let thumbContent = `<span class="thumb-placeholder">📷</span>`;
        if (entry.image_filename && isSuccess) {
            thumbContent = `<img src="images/${entry.image_filename}" class="history-thumb" alt="Thumbnail" onerror="this.outerHTML='<span class=\"thumb-placeholder\">📷</span>'">`;
        } else if (!isSuccess) {
            thumbContent = `<span class="thumb-placeholder text-danger">⚠️</span>`;
        }
        
        const descPreview = entry.description ? entry.description : (entry.error_message || 'Không có mô tả');
        
        html += `
            <div class="history-item ${isActive}" onclick="selectHistoryEntry(${entry.id})">
                <div class="history-thumb-wrapper">
                    ${thumbContent}
                </div>
                <div class="history-item-body">
                    <div class="history-item-meta">
                        <span class="history-item-title">${entry.entity_id}</span>
                        <span class="badge ${badgeClass} btn-sm" style="font-size: 0.6rem; padding: 0.05rem 0.25rem;">${badgeText}</span>
                    </div>
                    <p class="history-item-desc">${descPreview}</p>
                    <span class="history-item-time">${entry.timestamp}</span>
                </div>
                <button class="btn btn-danger btn-sm" style="padding: 0.25rem 0.4rem; margin: auto 0.5rem auto 0; border-radius: 4px;" onclick="deleteHistoryEntry(${entry.id}, event)">🗑️</button>
            </div>
        `;
    });
    
    historyList.innerHTML = html;
}

// Select details of an entry to expand
function selectHistoryEntry(id) {
    selectedEntryId = id;
    
    // Highlight list active
    const items = historyList.querySelectorAll('.history-item');
    items.forEach((item, index) => {
        if (historyEntries[index] && historyEntries[index].id === id) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
    
    const entry = historyEntries.find(e => e.id === id);
    if (!entry) return;
    
    const isSuccess = entry.status === 'success';
    const statusBadgeHtml = isSuccess 
        ? `<span class="badge badge-success">Thành công</span>` 
        : `<span class="badge badge-danger">Lỗi phân tích</span>`;
        
    let imgHtml = `
        <div class="empty-detail-state">
            <span class="empty-icon" style="font-size: 4rem;">⚠️</span>
            <p style="color: var(--danger)">Không có hình ảnh do tiến trình lỗi.</p>
        </div>
    `;
    
    if (entry.image_filename) {
        imgHtml = `<img src="images/${entry.image_filename}" class="detail-image" alt="Captured Vision Image" />`;
    }
    
    const descContent = isSuccess 
        ? entry.description 
        : `Lỗi mô tả:\n${entry.error_message || 'Lỗi không xác định khi kết nối API.'}`;

    const copyBtnHtml = isSuccess 
        ? `<button class="btn btn-secondary btn-sm" onclick="copyTextToClipboard(\`${entry.description.replace(/`/g, '\\`').replace(/\$/g, '\\$')}\`)">Sao chép mô tả</button>` 
        : '';

    detailView.className = 'detail-view-container';
    detailView.innerHTML = `
        <div class="detail-image-card">
            ${imgHtml}
        </div>
        
        <div class="detail-meta-box">
            <div class="detail-meta-item">
                <div class="detail-meta-label">Thực thể (Entity)</div>
                <div class="detail-meta-value">${entry.entity_id}</div>
            </div>
            <div class="detail-meta-item">
                <div class="detail-meta-label">Thời gian</div>
                <div class="detail-meta-value">${entry.timestamp}</div>
            </div>
            <div class="detail-meta-item">
                <div class="detail-meta-label">Trạng thái</div>
                <div class="detail-meta-value" style="margin-top: 0.25rem;">${statusBadgeHtml}</div>
            </div>
        </div>
        
        <div class="detail-desc-card">
            <div class="desc-card-header">
                <h3>Nội Dung Mô Tả Từ AI</h3>
                ${copyBtnHtml}
            </div>
            <div class="detail-desc-body">${descContent}</div>
        </div>
    `;
}

// Utility to copy AI description
function copyTextToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Đã sao chép mô tả vào bộ nhớ tạm!');
    }).catch(err => {
        console.error('Could not copy text: ', err);
    });
}

// Delete historical record
async function deleteHistoryEntry(id, event) {
    event.stopPropagation(); // Avoid triggering details click selection
    
    if (!confirm(`Bạn có chắc chắn muốn xóa bản ghi này?`)) return;
    
    try {
        const response = await fetch(`api/history/${id}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) throw new Error('Delete failed');
        
        showToast('Đã xóa bản ghi.');
        
        if (selectedEntryId === id) {
            selectedEntryId = null;
            detailView.className = 'detail-view-container empty';
            detailView.innerHTML = `
                <div class="empty-detail-state">
                    <span class="empty-icon">🖼️</span>
                    <p>Chọn một ảnh trong cột Lịch Sử để xem chi tiết mô tả và hình ảnh phóng to.</p>
                </div>
            `;
        }
        
        fetchHistory();
    } catch (error) {
        console.error(error);
        showToast('Không thể xóa bản ghi!', true);
    }
}

// Clear all history rows
async function clearHistory() {
    if (!confirm('BẠN CÓ CHẮC CHẮN muốn XÓA TOÀN BỘ lịch sử lưu trữ? Hành động này không thể hoàn tác.')) return;
    
    try {
        const response = await fetch('api/history/clear', {
            method: 'POST'
        });
        
        if (!response.ok) throw new Error('Clear failed');
        
        showToast('Đã xóa toàn bộ lịch sử.');
        selectedEntryId = null;
        detailView.className = 'detail-view-container empty';
        detailView.innerHTML = `
            <div class="empty-detail-state">
                <span class="empty-icon">🖼️</span>
                <p>Chọn một ảnh trong cột Lịch Sử để xem chi tiết mô tả và hình ảnh phóng to.</p>
            </div>
        `;
        
        fetchHistory();
    } catch (error) {
        console.error(error);
        showToast('Lỗi xóa lịch sử!', true);
    }
}

// Query HA entities to simplify adding camera entities
async function queryHAEntities(triggerToast = true) {
    const haUrl = haUrlInput.value.trim();
    const haToken = haTokenInput.value.trim();
    
    loadHaEntitiesBtn.disabled = true;
    loadHaEntitiesBtn.textContent = 'Đang quét...';
    haEntitiesStatus.textContent = 'Đang tìm kiếm camera...';
    
    try {
        let apiUrl = 'api/camera_entities';
        if (haUrl) {
            const params = new URLSearchParams({ ha_url: haUrl, ha_token: haToken });
            apiUrl += `?${params.toString()}`;
        }
        
        const response = await fetch(apiUrl);
        if (!response.ok) throw new Error('Failed to fetch entities');
        
        const entities = await response.json();
        
        if (entities.length === 0) {
            haEntitiesStatus.textContent = 'Không tìm thấy camera/entity nào.';
            entityHelper.classList.add('hidden');
            if (triggerToast) showToast('Không tìm thấy camera hoặc entity có ảnh nào!', true);
            return;
        }
        
        // Populate Picker dropdown
        let pickerHtml = '<option value="">-- Chọn camera/image/entity có ảnh --</option>';
        entities.forEach(ent => {
            const domain = ent.entity_id.split('.')[0];
            pickerHtml += `<option value="${ent.entity_id}">${ent.entity_id} · ${ent.friendly_name} · ${domain}</option>`;
        });
        entityPicker.innerHTML = pickerHtml;
        entityHelper.classList.remove('hidden');
        
        haEntitiesStatus.textContent = `Đã tìm thấy ${entities.length} thực thể.`;
        if (triggerToast) showToast(`Quét thành công! Tìm thấy ${entities.length} thực thể.`);
    } catch (error) {
        console.error(error);
        haEntitiesStatus.textContent = 'Lỗi kết nối HA API.';
        entityHelper.classList.add('hidden');
        if (triggerToast) showToast('Quét thực thể thất bại! Vui lòng kiểm tra lại URL và Token HA.', true);
    } finally {
        loadHaEntitiesBtn.disabled = false;
        loadHaEntitiesBtn.textContent = 'Tìm kiếm Entity từ HA';
    }
}

// Sync the quick run description drop down list
function updateManualTriggerDropdown() {
    let html = '<option value="">-- Chọn Camera --</option>';
    configuredCameras.forEach(ent => {
        html += `<option value="${ent}">${ent}</option>`;
    });
    manualScanSelect.innerHTML = html;
}

// Run single manual vision description cycle
async function runManualScan() {
    const entityId = manualScanSelect.value;
    if (!entityId) {
        showToast('Vui lòng chọn một thực thể trước!', true);
        return;
    }
    
    scanNowBtn.disabled = true;
    scanNowBtn.textContent = 'Đang chạy...';
    showToast(`Đang chạy chụp & mô tả cho ${entityId}...`);
    
    try {
        const response = await fetch('api/scan_now', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ entity_id: entityId })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'Mô tả thất bại');
        }
        
        showToast('Mô tả thành công!');
        await fetchHistory();
        
        // Auto select the newly created item
        if (historyEntries.length > 0) {
            selectHistoryEntry(historyEntries[0].id);
        }
    } catch (error) {
        console.error(error);
        showToast(`Quá trình lỗi: ${error.message}`, true);
        fetchHistory(); // Reload history anyway to show error row
    } finally {
        scanNowBtn.disabled = false;
        scanNowBtn.textContent = 'Chạy';
    }
}

// Test Home Assistant API connection and return detailed error explanation
async function testHAConnection() {
    const haUrl = haUrlInput.value.trim();
    const haToken = haTokenInput.value.trim();
    
    if (!haUrl) {
        showToast('Vui lòng nhập Home Assistant URL!', true);
        return;
    }
    
    testHaBtn.disabled = true;
    testHaBtn.textContent = 'Đang thử...';
    haEntitiesStatus.textContent = 'Đang kiểm tra kết nối tới Home Assistant...';
    haEntitiesStatus.className = 'small-text text-secondary';
    
    try {
        const response = await fetch('api/test_ha', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ha_url: haUrl, ha_token: haToken })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast(data.message);
            haEntitiesStatus.textContent = data.message;
            haEntitiesStatus.className = 'small-text text-success';
        } else {
            showToast(data.message || 'Lỗi kết nối!', true);
            haEntitiesStatus.textContent = data.message || 'Lỗi kết nối!';
            haEntitiesStatus.className = 'small-text text-danger';
        }
    } catch (error) {
        console.error(error);
        showToast('Không thể kết nối đến máy chủ addon!', true);
        haEntitiesStatus.textContent = 'Không thể kết nối đến API addon.';
        haEntitiesStatus.className = 'small-text text-danger';
    } finally {
        testHaBtn.disabled = false;
        testHaBtn.textContent = 'Kiểm tra kết nối HA';
    }
}

// Test all configured connections (HA, AI Proxy, MQTT) in parallel
async function testAllConnections() {
    const payload = {
        ha_url: haUrlInput.value.trim(),
        ha_token: haTokenInput.value.trim(),
        ai_proxy_base_url: aiBaseUrlInput.value.trim(),
        ai_api_key: aiKeyInput.value.trim(),
        ai_model: aiModelInput.value.trim(),
        mqtt_host: mqttHostInput.value.trim(),
        mqtt_port: parseInt(mqttPortInput.value) || 1883,
        mqtt_user: mqttUserInput.value.trim(),
        mqtt_password: mqttPassInput.value.trim(),
        telegram_bot_token: tgTokenInput.value.trim(),
        telegram_chat_id: tgChatInput.value.trim()
    };
    
    testAllBtn.disabled = true;
    testAllBtn.textContent = 'Đang kiểm tra...';
    
    // Clear & set loading text for all status fields
    haEntitiesStatus.textContent = 'Đang thử HA...';
    haEntitiesStatus.className = 'small-text text-secondary';
    aiStatusText.textContent = 'Đang thử AI Proxy...';
    aiStatusText.className = 'small-text text-secondary';
    mqttStatusText.textContent = 'Đang thử MQTT...';
    mqttStatusText.className = 'small-text text-secondary';
    tgStatusText.textContent = 'Đang thử Telegram...';
    tgStatusText.className = 'small-text text-secondary';
    
    try {
        const response = await fetch('api/test_all', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) throw new Error('Yêu cầu chẩn đoán thất bại');
        
        const results = await response.json();
        
        // 1. Render HA Result
        haEntitiesStatus.textContent = results.ha.message;
        haEntitiesStatus.className = `small-text text-${results.ha.status === 'success' ? 'success' : 'danger'}`;
        
        // 2. Render AI Proxy Result
        aiStatusText.textContent = results.ai.message;
        aiStatusText.className = `small-text text-${results.ai.status === 'success' ? 'success' : 'danger'}`;
        
        // 3. Render MQTT Result
        mqttStatusText.textContent = results.mqtt.message;
        mqttStatusText.className = `small-text text-${results.mqtt.status === 'success' ? 'success' : 'danger'}`;
        
        // 4. Render Telegram Result
        tgStatusText.textContent = results.telegram.message;
        tgStatusText.className = `small-text text-${results.telegram.status === 'success' ? 'success' : 'danger'}`;
        
        const hasErrors = results.ha.status === 'error' || results.ai.status === 'error' || results.mqtt.status === 'error' || results.telegram.status === 'error';
        if (hasErrors) {
            showToast('Một số kết nối cấu hình gặp lỗi!', true);
        } else {
            showToast('Tất cả kết nối đã kiểm tra thành công!');
        }
    } catch (error) {
        console.error(error);
        showToast('Không thể kết nối đến API kiểm thử!', true);
        haEntitiesStatus.textContent = 'Lỗi chẩn đoán kết nối.';
        haEntitiesStatus.className = 'small-text text-danger';
        aiStatusText.textContent = 'Lỗi chẩn đoán kết nối.';
        aiStatusText.className = 'small-text text-danger';
        mqttStatusText.textContent = 'Lỗi chẩn đoán kết nối.';
        mqttStatusText.className = 'small-text text-danger';
        tgStatusText.textContent = 'Lỗi chẩn đoán kết nối.';
        tgStatusText.className = 'small-text text-danger';
    } finally {
        testAllBtn.disabled = false;
        testAllBtn.textContent = 'Kiểm tra kết nối';
    }
}

// Render dynamic camera card list
function renderCameraList() {
    const cameraListContainer = document.getElementById('camera-list');
    if (!cameraListContainer) return;
    
    if (configuredCameras.length === 0) {
        cameraListContainer.innerHTML = `<p class="empty-msg" style="padding: 1rem; font-size: 0.8rem; text-align: center;">Chưa cấu hình camera nào.</p>`;
        return;
    }
    
    let html = '';
    configuredCameras.forEach(entityId => {
        const settings = cameraSettings[entityId] || {};
        const scanInterval = settings.scan_interval !== undefined ? settings.scan_interval : '';
        const aiPrompt = settings.ai_prompt || '';
        const aiModel = settings.ai_model || '';
        const motionThreshold = settings.motion_threshold !== undefined ? settings.motion_threshold : '';
        
        // Use clean identifier for HTML ID
        const safeId = 'settings-' + entityId.replace(/\./g, '_');
        
        html += `
            <div class="camera-item-card" id="card-${entityId.replace(/\./g, '_')}">
                <div class="camera-item-header">
                    <span class="camera-item-title">${entityId}</span>
                    <div class="camera-item-actions">
                        <button type="button" class="camera-action-btn toggle-settings-btn" title="Cài đặt riêng" onclick="toggleCameraSettings('${entityId}')">
                            ⚙️
                        </button>
                        <button type="button" class="camera-action-btn delete-btn" title="Xóa camera" onclick="removeCameraFromConfig('${entityId}')">
                            🗑️
                        </button>
                    </div>
                </div>
                <div class="camera-item-settings collapsed" id="${safeId}">
                    <div class="camera-setting-row">
                        <label>Chu kỳ quét riêng (giây, bỏ trống để dùng mặc định):</label>
                        <input type="number" min="5" class="text-input cam-interval-input" 
                               value="${scanInterval}" placeholder="Mặc định"
                               onchange="updateCameraSetting('${entityId}', 'scan_interval', this.value)">
                    </div>
                    <div class="camera-setting-row">
                        <label>Ngưỡng chuyển động riêng (%, bỏ trống để dùng mặc định):</label>
                        <input type="number" min="0.1" step="0.1" class="text-input cam-motion-input" 
                               value="${motionThreshold}" placeholder="Mặc định"
                               onchange="updateCameraSetting('${entityId}', 'motion_threshold', this.value)">
                    </div>
                    <div class="camera-setting-row">
                        <label>Prompt gửi AI riêng (bỏ trống để dùng mặc định):</label>
                        <textarea rows="2" class="text-input cam-prompt-input" 
                                  placeholder="Mặc định"
                                  onchange="updateCameraSetting('${entityId}', 'ai_prompt', this.value)">${aiPrompt}</textarea>
                    </div>
                    <div class="camera-setting-row">
                        <label>Vision Model riêng (bỏ trống để dùng mặc định):</label>
                        <input type="text" class="text-input cam-model-input" 
                               value="${aiModel}" placeholder="Mặc định"
                               onchange="updateCameraSetting('${entityId}', 'ai_model', this.value)">
                    </div>
                </div>
            </div>
        `;
    });
    cameraListContainer.innerHTML = html;
}

// Toggle collapse/expand settings
function toggleCameraSettings(entityId) {
    const safeId = 'settings-' + entityId.replace(/\./g, '_');
    const el = document.getElementById(safeId);
    if (el) {
        el.classList.toggle('collapsed');
    }
}

// Remove camera from config list
function removeCameraFromConfig(entityId) {
    if (confirm(`Bạn có chắc muốn xóa camera ${entityId} khỏi cấu hình?`)) {
        configuredCameras = configuredCameras.filter(c => c !== entityId);
        delete cameraSettings[entityId];
        renderCameraList();
        updateManualTriggerDropdown();
    }
}

// Update local cameraSettings states
function updateCameraSetting(entityId, key, value) {
    if (!cameraSettings[entityId]) {
        cameraSettings[entityId] = {};
    }
    
    if (key === 'scan_interval') {
        const intVal = parseInt(value);
        if (isNaN(intVal) || intVal <= 0) {
            delete cameraSettings[entityId].scan_interval;
        } else {
            cameraSettings[entityId].scan_interval = intVal;
        }
    } else if (key === 'motion_threshold') {
        const floatVal = parseFloat(value);
        if (isNaN(floatVal) || floatVal <= 0.0) {
            delete cameraSettings[entityId].motion_threshold;
        } else {
            cameraSettings[entityId].motion_threshold = floatVal;
        }
    } else {
        const strVal = value.trim();
        if (!strVal) {
            delete cameraSettings[entityId][key];
        } else {
            cameraSettings[entityId][key] = strVal;
        }
    }
    
    // Clean up empty settings object
    if (Object.keys(cameraSettings[entityId]).length === 0) {
        delete cameraSettings[entityId];
    }
}
