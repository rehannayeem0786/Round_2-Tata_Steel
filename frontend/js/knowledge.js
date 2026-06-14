/**
 * Knowledge base module — Document search, upload,
 * and knowledge base management.
 */

/**
 * Initialize the knowledge view.
 */
async function initKnowledge() {
    await loadKnowledgeStats();
}

/**
 * Load knowledge base statistics.
 */
async function loadKnowledgeStats() {
    try {
        const result = await apiRequest('/api/knowledge/stats');
        renderKnowledgeStats(result.data);
    } catch (error) {
        console.error('Failed to load knowledge stats:', error);
    }
}

/**
 * Render knowledge base statistics.
 */
function renderKnowledgeStats(stats) {
    const container = document.getElementById('knowledge-stats');

    const collectionNames = {
        'equipment_manuals': '📖 Equipment Manuals',
        'standard_operating_procedures': '📋 SOPs',
        'maintenance_records': '🔧 Maintenance Records',
        'failure_reports': '📊 Failure Reports',
        'uploaded_documents': '📄 Uploaded Documents',
    };

    let totalChunks = 0;
    let html = '';

    for (const [name, data] of Object.entries(stats)) {
        totalChunks += data.count;
        const displayName = collectionNames[name] || name;
        html += `
            <div class="knowledge-stat">
                <div class="knowledge-stat-value">${data.count}</div>
                <div class="knowledge-stat-label">${displayName}</div>
            </div>
        `;
    }

    // Add total
    html = `
        <div class="knowledge-stat">
            <div class="knowledge-stat-value">${totalChunks}</div>
            <div class="knowledge-stat-label">📚 Total Knowledge Chunks</div>
        </div>
    ` + html;

    container.innerHTML = html;
}

/**
 * Search the knowledge base.
 */
async function searchKnowledge() {
    const input = document.getElementById('knowledge-search-input');
    const query = input.value.trim();

    if (!query) {
        showToast('Enter a search query', 'warning');
        return;
    }

    const container = document.getElementById('knowledge-results');
    container.innerHTML = '<div class="empty-state"><div class="loading-spinner"></div></div>';

    try {
        const result = await apiRequest(`/api/knowledge/search?q=${encodeURIComponent(query)}&n=10`);
        renderKnowledgeResults(result.data);
    } catch (error) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">❌</div><div class="empty-state-text">Search failed. Please try again.</div></div>';
        showToast('Search failed: ' + error.message, 'error');
    }
}

/**
 * Render knowledge search results.
 */
function renderKnowledgeResults(results) {
    const container = document.getElementById('knowledge-results');

    if (!results || results.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🔍</div>
                <div class="empty-state-text">No results found. Try a different search query.</div>
            </div>
        `;
        return;
    }

    container.innerHTML = results.map((r, i) => `
        <div class="knowledge-result-card">
            <div class="knowledge-result-header">
                <span class="knowledge-result-source">${r.source}</span>
                <span class="knowledge-result-relevance">${Math.round(r.relevance * 100)}% match</span>
            </div>
            <div class="knowledge-result-category">${r.category} — ${r.collection}</div>
            <div class="knowledge-result-text">${r.text}</div>
        </div>
    `).join('');
}

/**
 * Upload a document to the knowledge base.
 */
async function uploadDocument(inputEl) {
    const file = inputEl.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('category', 'uploaded');

    try {
        const response = await fetch('/api/knowledge/upload', {
            method: 'POST',
            body: formData,
        });

        const result = await response.json();

        if (result.success) {
            showToast(`✅ ${result.data.message}`, 'success');
            await loadKnowledgeStats();
        } else {
            showToast('Upload failed: ' + (result.detail || 'Unknown error'), 'error');
        }
    } catch (error) {
        showToast('Upload failed: ' + error.message, 'error');
    }

    // Reset input
    inputEl.value = '';
}
