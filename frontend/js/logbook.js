/**
 * Digital Logbook module — Fetches and renders maintenance logs
 */

async function loadLogbook() {
    const listContainer = document.getElementById('logbook-list');
    if (!listContainer) return;
    
    listContainer.innerHTML = '<div class="chat-welcome" style="padding: 40px 20px;"><h2>Loading Logbook...</h2></div>';
    
    try {
        const response = await apiRequest('/api/dashboard/maintenance');
        if (response && response.success && response.data) {
            renderLogbook(response.data);
        }
    } catch (error) {
        listContainer.innerHTML = `<div class="chat-welcome" style="padding: 40px 20px;"><h2>Error loading logbook: ${error.message}</h2></div>`;
    }
}

function renderLogbook(logs) {
    const listContainer = document.getElementById('logbook-list');
    if (!listContainer) return;

    if (!logs || logs.length === 0) {
        listContainer.innerHTML = `
            <div class="chat-welcome" style="padding: 40px 20px;">
                <span class="chat-welcome-icon">📖</span>
                <h2>Logbook Empty</h2>
                <p>No maintenance logs have been generated yet.</p>
            </div>
        `;
        return;
    }

    // Keep a reference for export.
    window._logbookData = logs;

    const isAI = (by) => by && /AI|System|Automation|Scenario/i.test(by);

    const items = logs.map(log => {
        const date = new Date(log.date).toLocaleString();
        const ai = isAI(log.performed_by);
        const dotColor = ai ? 'var(--accent-primary)' : 'var(--status-operational)';
        const tag = ai
            ? '<span style="background: rgba(0,87,183,0.18); color: var(--tata-blue-light, #1a6fd1); padding: 2px 8px; border-radius: 6px; font-size: 10px; font-weight: 700;">🤖 AI-GENERATED</span>'
            : '<span style="background: rgba(16,185,129,0.15); color: #10b981; padding: 2px 8px; border-radius: 6px; font-size: 10px; font-weight: 700;">👤 MANUAL</span>';

        return `
            <div style="position: relative; padding-left: 34px; padding-bottom: 18px;">
                <span style="position: absolute; left: 8px; top: 6px; width: 12px; height: 12px; border-radius: 50%; background: ${dotColor}; box-shadow: 0 0 0 4px rgba(255,255,255,0.04); z-index: 2;"></span>
                <span style="position: absolute; left: 13px; top: 6px; bottom: -6px; width: 2px; background: var(--border-default);"></span>
                <div style="background: var(--bg-card); border: 1px solid ${ai ? 'rgba(0,87,183,0.35)' : 'var(--border-default)'}; border-radius: var(--radius-md); padding: 16px; box-shadow: var(--shadow-sm); backdrop-filter: blur(12px);">
                    <div style="display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-bottom: 10px;">
                        <strong style="font-size: 1.05em; color: var(--text-primary);">${log.equipment_name} (${log.equipment_id})</strong>
                        <span style="color: var(--text-tertiary); font-size: 0.85em;">${date}</span>
                    </div>
                    <div style="margin-bottom: 10px; display: flex; gap: 8px; flex-wrap: wrap; align-items: center;">
                        ${tag}
                        <span style="background: var(--bg-input); padding: 3px 8px; border-radius: var(--radius-sm); font-size: 0.8em;">Type: ${log.type}</span>
                        <span style="background: var(--bg-input); padding: 3px 8px; border-radius: var(--radius-sm); font-size: 0.8em;">By: ${log.performed_by || 'Unknown'}</span>
                    </div>
                    <p style="color: var(--text-secondary); margin-bottom: 10px;">${log.description}</p>
                    <div style="display: flex; gap: 15px; font-size: 0.85em; color: var(--text-tertiary); flex-wrap: wrap;">
                        <span><strong>Outcome:</strong> ${log.outcome || 'N/A'}</span>
                        <span><strong>Duration:</strong> ${log.duration_hours || '0'} hrs</span>
                        <span><strong>Parts:</strong> ${log.parts_replaced || 'None'}</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    listContainer.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px;">
            <span style="color: var(--text-secondary); font-size: 13px;">${logs.length} maintenance ${logs.length === 1 ? 'entry' : 'entries'}</span>
            <button onclick="exportLogbook()" style="background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary)); color: white; border: none; padding: 8px 16px; border-radius: var(--radius-sm); font-family: var(--font-sans); font-size: 13px; cursor: pointer; display: flex; align-items: center; gap: 6px;">
                📄 Export Logbook
            </button>
        </div>
        <div class="logbook-timeline">${items}</div>
    `;
}

/**
 * Export the current logbook entries as a downloadable text file.
 */
function exportLogbook() {
    const logs = window._logbookData || [];
    if (!logs.length) return;

    let txt = 'TATA STEEL — INTELLIGENT MAINTENANCE WIZARD\n';
    txt += 'DIGITAL MAINTENANCE LOGBOOK EXPORT\n';
    txt += `Generated: ${new Date().toLocaleString()}\n`;
    txt += '='.repeat(60) + '\n\n';

    logs.forEach((log, i) => {
        txt += `#${i + 1} — ${log.equipment_name} (${log.equipment_id})\n`;
        txt += `Date: ${new Date(log.date).toLocaleString()}\n`;
        txt += `Type: ${log.type} | By: ${log.performed_by || 'Unknown'}\n`;
        txt += `Description: ${log.description}\n`;
        txt += `Outcome: ${log.outcome || 'N/A'} | Duration: ${log.duration_hours || 0} hrs | Parts: ${log.parts_replaced || 'None'}\n`;
        txt += '-'.repeat(60) + '\n';
    });

    const blob = new Blob([txt], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `maintenance_logbook_${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    if (typeof showToast === 'function') showToast('Logbook exported', 'success');
}

// Hook into app initialization
document.addEventListener('DOMContentLoaded', () => {
    // We'll also attach it to the switchView logic in app.js
    const navLogbook = document.getElementById('nav-logbook');
    if (navLogbook) {
        navLogbook.addEventListener('click', () => {
            // switchView is defined in app.js
            if(typeof switchView === 'function') {
                switchView('logbook');
            }
        });
    }
});
