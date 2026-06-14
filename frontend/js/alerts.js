/**
 * Alerts module — Real-time alert feed with filtering,
 * acknowledgement, and resolution.
 */

let alertsData = {
    alerts: [],
    currentFilter: 'all',
};

/**
 * Initialize alerts view.
 */
async function initAlerts() {
    await loadAlerts();

    // Register for real-time alert updates
    onWsMessage('alert', handleNewAlert);
}

/**
 * Load alerts from the API.
 */
async function loadAlerts() {
    try {
        const result = await apiRequest('/api/alerts/active');
        alertsData.alerts = result.data;
        renderAlerts();
        updateAlertBadge();
    } catch (error) {
        console.error('Failed to load alerts:', error);
    }
}

/**
 * Render the alerts list.
 */
function renderAlerts() {
    const list = document.getElementById('alerts-list');
    let filtered = alertsData.alerts;

    if (alertsData.currentFilter !== 'all') {
        filtered = filtered.filter(a => a.severity === alertsData.currentFilter);
    }

    if (filtered.length === 0) {
        list.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">✅</div>
                <div class="empty-state-text">
                    ${alertsData.currentFilter === 'all' 
                        ? 'No active alerts. All systems nominal.' 
                        : `No ${alertsData.currentFilter} alerts.`}
                </div>
            </div>
        `;
        return;
    }

    list.innerHTML = filtered.map(alert => {
        const severityIcons = {
            critical: '🔴',
            high: '🟠',
            medium: '🟡',
            low: '🟢',
        };

        return `
            <div class="alert-card severity-${alert.severity}" id="alert-${alert.id}">
                <div class="alert-severity-icon">${severityIcons[alert.severity] || '⚪'}</div>
                <div class="alert-content">
                    <div class="alert-title">${alert.title}</div>
                    <div class="alert-message">${alert.message}</div>
                    <div class="alert-footer">
                        <span class="alert-equipment">${alert.equipment_name || alert.equipment_id}</span>
                        <span>•</span>
                        <span>${formatTime(alert.timestamp)}</span>
                        <div class="alert-actions">
                            ${!alert.acknowledged ? `<button class="alert-action-btn" onclick="acknowledgeAlert(${alert.id})">Acknowledge</button>` : ''}
                            <button class="alert-action-btn resolve" onclick="resolveAlert(${alert.id})">Resolve</button>
                            <button class="alert-action-btn" onclick="diagnoseAlert('${alert.equipment_name || alert.equipment_id}', '${alert.title.replace(/'/g, "\\'")}')">🔍 Diagnose</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Filter alerts by severity.
 */
function filterAlerts(severity, btnEl) {
    alertsData.currentFilter = severity;

    // Update button states
    document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
    btnEl.classList.add('active');

    renderAlerts();
}

/**
 * Acknowledge an alert.
 */
async function acknowledgeAlert(alertId) {
    try {
        await apiRequest(`/api/alerts/${alertId}`, {
            method: 'POST',
            body: JSON.stringify({ action: 'acknowledge' }),
        });

        showToast('Alert acknowledged', 'success');
        await loadAlerts();
    } catch (error) {
        showToast('Failed to acknowledge alert', 'error');
    }
}

/**
 * Resolve an alert.
 */
async function resolveAlert(alertId) {
    try {
        await apiRequest(`/api/alerts/${alertId}`, {
            method: 'POST',
            body: JSON.stringify({ action: 'resolve' }),
        });

        // Animate removal
        const card = document.getElementById(`alert-${alertId}`);
        if (card) {
            card.style.transition = 'all 0.3s ease';
            card.style.opacity = '0';
            card.style.transform = 'translateX(100px)';
            setTimeout(() => {
                loadAlerts();
            }, 300);
        } else {
            await loadAlerts();
        }

        showToast('Alert resolved', 'success');
    } catch (error) {
        showToast('Failed to resolve alert', 'error');
    }
}

/**
 * Navigate to chat to diagnose an alert.
 */
function diagnoseAlert(equipmentName, alertTitle) {
    switchView('chat');
    const input = document.getElementById('chat-input');
    input.value = `Diagnose this alert: "${alertTitle}" on ${equipmentName}. What is the root cause and what should we do?`;
    input.focus();
}

/**
 * Handle a new real-time alert.
 */
function handleNewAlert(alertData) {
    // Add to alerts array
    alertsData.alerts.unshift(alertData);
    renderAlerts();
    updateAlertBadge();

    // Show toast notification
    const severityEmoji = { critical: '🔴', high: '🟠', medium: '🟡', low: '🟢' };
    showToast(
        `${severityEmoji[alertData.severity] || '⚪'} ${alertData.title}`,
        alertData.severity === 'critical' ? 'error' : 'warning'
    );
}

/**
 * Update the alert count badge in the sidebar.
 */
function updateAlertBadge() {
    const badge = document.getElementById('alert-count-badge');
    const count = alertsData.alerts.filter(a => !a.resolved).length;

    if (count > 0) {
        badge.textContent = count;
        badge.style.display = 'inline-flex';
    } else {
        badge.style.display = 'none';
    }
}
