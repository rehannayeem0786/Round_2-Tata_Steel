/**
 * Main application controller — View routing, initialization,
 * and global state management.
 */

const viewTitles = {
    dashboard: { title: 'Plant Dashboard', subtitle: 'Real-time equipment monitoring' },
    chat: { title: 'AI Maintenance Assistant', subtitle: 'Multi-agent diagnostic & advisory system' },
    alerts: { title: 'Alert Center', subtitle: 'Real-time anomaly alerts & notifications' },
    knowledge: { title: 'Knowledge Base', subtitle: 'Equipment manuals, SOPs, and maintenance records' },
    logbook: { title: 'Digital Logbook', subtitle: 'Automated maintenance records and reports' },
    analytics: { title: 'OEE & Analytics', subtitle: 'Overall Equipment Effectiveness, cost impact & predictive timeline' },
};

// Global state
window.currentUserRole = 'engineer';

function changeUserRole() {
    const select = document.getElementById('user-role-select');
    window.currentUserRole = select.value;
    showToast(`Role changed to ${select.options[select.selectedIndex].text}`, 'info');

    // Dynamically refresh active views based on new role privileges
    const activeNav = document.querySelector('.nav-item.active');
    if (activeNav) {
        const activeView = activeNav.getAttribute('data-view');
        if (activeView === 'dashboard') {
            loadDashboardStats();
            loadEquipment();
        } else if (activeView === 'analytics') {
            if (typeof loadAnalytics === 'function') loadAnalytics();
        }
    }

    // Pass role as context to AI Chat if possible
    if (typeof sendSystemMessage === 'function') {
        sendSystemMessage(`User role changed to ${window.currentUserRole}`);
    }
}

/**
 * Switch between views.
 */
function switchView(viewName) {
    // Update active view
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    const targetView = document.getElementById(`view-${viewName}`);
    if (targetView) targetView.classList.add('active');

    // Update nav
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    const navItem = document.getElementById(`nav-${viewName}`);
    if (navItem) navItem.classList.add('active');

    // Update header
    const viewInfo = viewTitles[viewName] || { title: viewName, subtitle: '' };
    document.getElementById('view-title').textContent = viewInfo.title;
    document.getElementById('view-subtitle').textContent = viewInfo.subtitle;

    // View-specific initialization
    if (viewName === 'alerts') {
        loadAlerts();
    } else if (viewName === 'knowledge') {
        loadKnowledgeStats();
    } else if (viewName === 'dashboard') {
        loadDashboardStats();
        loadEquipment();
    } else if (viewName === 'logbook') {
        if (typeof loadLogbook === 'function') loadLogbook();
    } else if (viewName === 'analytics') {
        if (typeof loadAnalytics === 'function') loadAnalytics();
    }
}

/**
 * Check AI service status.
 */
async function checkAIStatus() {
    try {
        const result = await apiRequest('/api/health');
        const badge = document.getElementById('ai-status-badge');
        const text = document.getElementById('ai-status-text');

        if (result.ai_enabled) {
            badge.classList.remove('offline');
            text.textContent = 'AI Active';
        } else {
            badge.classList.add('offline');
            text.textContent = 'AI Fallback Mode';
        }
    } catch (error) {
        const badge = document.getElementById('ai-status-badge');
        const text = document.getElementById('ai-status-text');
        badge.classList.add('offline');
        text.textContent = 'Server Offline';
    }
}

/**
 * Initialize the application.
 */
async function initApp() {
    // Set up navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            const view = item.getAttribute('data-view');
            if (view) switchView(view);
        });
    });

    // Initialize all modules
    await Promise.all([
        checkAIStatus(),
        initDashboard(),
        initAlerts(),
        initKnowledge(),
        initAnalytics(),
    ]);

    console.log('🏭 Intelligent Maintenance Wizard initialized');
}

// Start the app when DOM is ready
document.addEventListener('DOMContentLoaded', initApp);
