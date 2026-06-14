/**
 * Analytics module — OEE metrics, cost impact analysis,
 * sensor trend charts, predictive maintenance timeline,
 * and business intelligence for Tata Steel.
 */

// Chart instances (stored for cleanup on view switch)
let chartInstances = {};

let analyticsData = {
    oee: null,
    costSummary: null,
    predictiveTimeline: [],
    sensorTrends: {},
    equipmentList: [],
};

// ─── Chart Configuration ──────────────────────────────────────────────────

const CHART_COLORS = {
    primary: '#3b82f6',
    secondary: '#06b6d4',
    tertiary: '#8b5cf6',
    success: '#10b981',
    warning: '#f59e0b',
    critical: '#ef4444',
    info: '#60a5fa',
};

const CHART_TOOLTIP = {
    backgroundColor: 'rgba(17, 24, 39, 0.9)',
    titleColor: '#f1f5f9',
    bodyColor: '#94a3b8',
    borderColor: 'rgba(148, 163, 184, 0.12)',
    borderWidth: 1,
    bodyFont: { family: 'Inter', size: 12 },
    titleFont: { family: 'Inter', size: 13 },
    padding: 10,
    cornerRadius: 8,
};

// ─── Initialization ──────────────────────────────────────────────────

async function initAnalytics() {
    try {
        const equipment = await apiRequest('/api/dashboard/equipment');
        analyticsData.equipmentList = equipment.data || [];

        const select = document.getElementById('analytics-equipment-select');
        if (select) {
            select.innerHTML = '<option value="">Select Equipment...</option>';
            analyticsData.equipmentList.forEach(eq => {
                select.innerHTML += `<option value="${eq.id}">${eq.name} (${eq.id})</option>`;
            });
        }

        console.log('📈 Analytics initialized');
    } catch (error) {
        console.error('Analytics init error:', error);
    }
}

async function loadAnalytics() {
    await Promise.all([
        loadOEEData(),
        loadCostSummary(),
        loadPredictiveTimeline(),
        loadAnomalyDetection(),
    ]);
}

// ─── OEE Data ──────────────────────────────────────────────────────

async function loadOEEData() {
    try {
        const result = await apiRequest('/api/analytics/oee');
        analyticsData.oee = result.data;
        renderOEEGauges(result.data);
        renderEquipmentOEEChart(result.data);
    } catch (error) {
        console.error('Failed to load OEE:', error);
        document.getElementById('analytics-oee-grid').innerHTML =
            '<div class="empty-state"><div class="empty-state-icon">⚠️</div><div class="empty-state-text">Failed to load OEE data</div></div>';
    }
}

function renderOEEGauges(data) {
    const plantOee = data.plant_oee;

    // Update gauge value displays
    document.getElementById('gauge-availability').textContent = plantOee.plant_availability + '%';
    document.getElementById('gauge-performance').textContent = plantOee.plant_performance + '%';
    document.getElementById('gauge-quality').textContent = plantOee.plant_quality + '%';
    document.getElementById('gauge-oee').textContent = plantOee.plant_oee + '%';

    // OEE rating color
    const ratingColors = {
        'World-Class': '#10b981',
        'Good': '#3b82f6',
        'Average': '#f59e0b',
        'Below Average': '#ef4444',
    };
    const ratingColor = ratingColors[plantOee.oee_rating] || '#64748b';

    // Render OEE summary cards
    const oeeGrid = document.getElementById('analytics-oee-grid');
    oeeGrid.innerHTML = `
        <div class="stat-card">
            <div class="stat-card-label">Plant OEE</div>
            <div class="stat-card-value" style="color: ${ratingColor}; font-size: 2em;">${plantOee.plant_oee}%</div>
            <div class="stat-card-footer">${plantOee.oee_rating}</div>
        </div>
        <div class="stat-card">
            <div class="stat-card-label">Availability</div>
            <div class="stat-card-value" style="color: var(--status-operational)">${plantOee.plant_availability}%</div>
            <div class="stat-card-footer">Operating time ratio</div>
        </div>
        <div class="stat-card">
            <div class="stat-card-label">Performance</div>
            <div class="stat-card-value" style="color: var(--accent-secondary)">${plantOee.plant_performance}%</div>
            <div class="stat-card-footer">Speed efficiency</div>
        </div>
        <div class="stat-card">
            <div class="stat-card-label">Quality</div>
            <div class="stat-card-value" style="color: var(--accent-tertiary)">${plantOee.plant_quality}%</div>
            <div class="stat-card-footer">Product quality rate</div>
        </div>
        <div class="stat-card">
            <div class="stat-card-label">Equipment Count</div>
            <div class="stat-card-value">${plantOee.equipment_count}</div>
            <div class="stat-card-footer">Across all zones</div>
        </div>
        <div class="stat-card">
            <div class="stat-card-label">Tata Steel Target</div>
            <div class="stat-card-value" style="color: var(--status-operational)">85%</div>
            <div class="stat-card-footer">World-class benchmark</div>
        </div>
    `;

    // Render doughnut gauge charts
    renderDoughnutGauge('chart-availability', plantOee.plant_availability, '#10b981');
    renderDoughnutGauge('chart-performance', plantOee.plant_performance, '#06b6d4');
    renderDoughnutGauge('chart-quality', plantOee.plant_quality, '#8b5cf6');
    renderDoughnutGauge('chart-oee', plantOee.plant_oee, ratingColor);
}

function renderDoughnutGauge(canvasId, value, color) {
    const existing = chartInstances[canvasId];
    if (existing) existing.destroy();

    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    const valueNum = parseFloat(value);

    chartInstances[canvasId] = new Chart(canvas.getContext('2d'), {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [valueNum, 100 - valueNum],
                backgroundColor: [color, 'rgba(148, 163, 184, 0.08)'],
                borderWidth: 0,
                cutout: '78%',
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            rotation: -90,
            circumference: 180,
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false },
            },
            animation: { animateRotate: true, duration: 800 },
        }
    });
}

function renderEquipmentOEEChart(data) {
    const equipmentOee = data.equipment_oee || [];

    const existing = chartInstances['chart-equipment-oee'];
    if (existing) existing.destroy();

    const canvas = document.getElementById('chart-equipment-oee');
    if (!canvas) return;

    const labels = equipmentOee.map(eq => eq.equipment_name.split('#')[0].trim().split(' ').slice(0, 2).join(' '));
    const oeeValues = equipmentOee.map(eq => eq.oee);
    const availValues = equipmentOee.map(eq => eq.availability);
    const perfValues = equipmentOee.map(eq => eq.performance);
    const qualityValues = equipmentOee.map(eq => eq.quality);

    chartInstances['chart-equipment-oee'] = new Chart(canvas.getContext('2d'), {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                { label: 'OEE %', data: oeeValues, backgroundColor: '#3b82f699', borderColor: '#3b82f6', borderWidth: 1, borderRadius: 4 },
                { label: 'Availability %', data: availValues, backgroundColor: '#10b98199', borderColor: '#10b981', borderWidth: 1, borderRadius: 4 },
                { label: 'Performance %', data: perfValues, backgroundColor: '#06b6d499', borderColor: '#06b6d4', borderWidth: 1, borderRadius: 4 },
                { label: 'Quality %', data: qualityValues, backgroundColor: '#8b5cf699', borderColor: '#8b5cf6', borderWidth: 1, borderRadius: 4 },
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top', labels: { boxWidth: 12, padding: 12, font: { size: 11 } } },
                tooltip: CHART_TOOLTIP,
            },
            scales: {
                y: { beginAtZero: true, max: 100, grid: { color: 'rgba(148, 163, 184, 0.06)' } },
                x: { grid: { display: false } },
            },
        }
    });
}

// ─── Cost Summary ──────────────────────────────────────────────────────

async function loadCostSummary() {
    try {
        const result = await apiRequest('/api/analytics/cost-summary');
        analyticsData.costSummary = result.data;
        renderCostImpactChart(result.data);
    } catch (error) {
        console.error('Failed to load cost summary:', error);
    }
}

function renderCostImpactChart(data) {
    const existing = chartInstances['chart-cost-impact'];
    if (existing) existing.destroy();

    const canvas = document.getElementById('chart-cost-impact');
    if (!canvas) return;

    const risk = data.annual_downtime_risk;
    const maint = data.maintenance_costs;
    const roi = data.roi;

    // Convert to lakhs (1 lakh = 100,000)
    const criticalL = Math.round(risk.critical / 100000);
    const warningL = Math.round(risk.warning / 100000);
    const operationalL = Math.round(risk.operational / 100000);
    const totalL = Math.round(risk.total / 100000);
    const annualMaintL = Math.round(maint.estimated_annual_cost / 100000);
    const netSavingsL = Math.round(roi.net_savings / 100000);

    chartInstances['chart-cost-impact'] = new Chart(canvas.getContext('2d'), {
        type: 'bar',
        data: {
            labels: ['Critical Risk', 'Warning Risk', 'Operational Risk', 'Total Risk', 'Annual Maint.', 'Net Savings'],
            datasets: [{
                label: '₹ Lakhs',
                data: [criticalL, warningL, operationalL, totalL, annualMaintL, netSavingsL],
                backgroundColor: ['#ef444499', '#f59e0b99', '#60a5fa99', '#3b82f699', '#06b6d499', '#10b98199'],
                borderColor: ['#ef4444', '#f59e0b', '#60a5fa', '#3b82f6', '#06b6d4', '#10b981'],
                borderWidth: 1,
                borderRadius: 6,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    ...CHART_TOOLTIP,
                    callbacks: { label: ctx => '₹ ' + ctx.raw + ' Lakhs' },
                },
            },
            scales: {
                y: { beginAtZero: true, grid: { color: 'rgba(148, 163, 184, 0.06)' } },
                x: { grid: { display: false } },
            },
        }
    });
}

// ─── Predictive Timeline ──────────────────────────────────────────────────

async function loadPredictiveTimeline() {
    try {
        const result = await apiRequest('/api/analytics/predictive-timeline');
        analyticsData.predictiveTimeline = result.data;
        renderPredictiveTimeline(result.data);
    } catch (error) {
        console.error('Failed to load predictive timeline:', error);
        document.getElementById('analytics-timeline').innerHTML =
            '<div class="empty-state"><div class="empty-state-icon">⚠️</div><div class="empty-state-text">Failed to load timeline</div></div>';
    }
}

function renderPredictiveTimeline(timeline) {
    const container = document.getElementById('analytics-timeline');

    if (!timeline || timeline.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">✅</div><div class="empty-state-text">No maintenance timeline items</div></div>';
        return;
    }

    const urgencyIcons = { IMMEDIATE: '🔴', URGENT: '🟠', PLANNED: '🔵', MONITOR: '🟢' };

    container.innerHTML = timeline.map(item => {
        const icon = urgencyIcons[item.urgency] || '⚪';
        const rulDisplay = item.min_rul_hours < 900
            ? (item.min_rul_hours < 168 ? Math.round(item.min_rul_hours / 24) + ' days' : Math.round(item.min_rul_hours / 168) + ' weeks')
            : 'Stable';

        const metricsHtml = item.metrics_rul
            ? Object.entries(item.metrics_rul).map(([m, rul]) =>
                `<span class="timeline-metric-tag">${m}: ${rul < 900 ? Math.round(rul) + 'h' : 'Stable'}</span>`
            ).join('')
            : '';

        return `
            <div class="timeline-item" style="border-left: 3px solid ${item.color};" onclick="askAboutEquipment('${item.equipment_id}', '${item.equipment_name}')">
                <div class="timeline-icon">${icon}</div>
                <div class="timeline-content">
                    <div class="timeline-header">
                        <strong>${item.equipment_name}</strong>
                        <span class="timeline-urgency-badge" style="background: ${item.color};">${item.urgency}</span>
                    </div>
                    <div class="timeline-details">
                        <span>RUL: ${rulDisplay}</span>
                        <span>Status: ${item.status}</span>
                        <span>Criticality: ${item.criticality}</span>
                    </div>
                    <div class="timeline-metrics">${metricsHtml}</div>
                    <div class="timeline-action">${item.recommended_action}</div>
                </div>
            </div>
        `;
    }).join('');
}

// ─── ML Anomaly Detection ────────────────────────────────────────────────────

async function loadAnomalyDetection() {
    const grid = document.getElementById('anomaly-grid');
    if (!grid) return;
    grid.innerHTML = '<div class="empty-state"><div class="loading-spinner"></div><div class="empty-state-text">Running ML anomaly scan...</div></div>';

    try {
        const result = await apiRequest('/api/analytics/anomaly-detection');
        renderAnomalyDetection(result.data || []);
    } catch (error) {
        console.error('Failed to load anomaly detection:', error);
        grid.innerHTML = '<div class="empty-state"><div class="empty-state-icon">⚠️</div><div class="empty-state-text">Failed to run ML anomaly detection</div></div>';
    }
}

function renderAnomalyDetection(reports) {
    const grid = document.getElementById('anomaly-grid');
    if (!grid) return;

    if (reports.length && reports[0].engine) {
        const badge = document.getElementById('ml-engine-badge');
        if (badge) badge.textContent = reports[0].engine;
    }

    const stateColor = { 'Anomalous': '#ef4444', 'Degrading': '#f59e0b', 'Healthy': '#10b981' };

    grid.innerHTML = reports.map(r => {
        const color = stateColor[r.health_state] || '#64748b';
        const scorePct = Math.round((r.overall_anomaly_score || 0) * 100);
        const topMetrics = (r.metrics || []).slice(0, 4).map(m => {
            const mColor = m.classification === 'anomaly' ? '#ef4444'
                : (m.classification === 'early_warning' ? '#f59e0b' : '#10b981');
            const trendIcon = m.trend === 'rising' ? '↑' : (m.trend === 'falling' ? '↓' : '→');
            return `
                <div class="anomaly-metric-row">
                    <span class="anomaly-metric-name">${m.metric.replace(/_/g, ' ')}</span>
                    <span class="anomaly-metric-bar"><span class="anomaly-metric-fill" style="width:${Math.round(m.anomaly_score * 100)}%; background:${mColor};"></span></span>
                    <span class="anomaly-metric-score" style="color:${mColor};">${m.anomaly_score.toFixed(2)} ${trendIcon}</span>
                </div>`;
        }).join('');

        return `
            <div class="anomaly-card" style="border-top: 3px solid ${color};" onclick="askAboutEquipment('${r.equipment_id}', '${r.equipment_name}')">
                <div class="anomaly-card-header">
                    <div>
                        <div class="anomaly-card-title">${r.equipment_name}</div>
                        <div class="anomaly-card-sub">${r.equipment_id} · ${r.equipment_type}</div>
                    </div>
                    <div class="anomaly-state-badge" style="background:${color}1a; color:${color}; border:1px solid ${color}55;">${r.health_state}</div>
                </div>
                <div class="anomaly-score-row">
                    <span class="anomaly-score-label">Anomaly Score</span>
                    <span class="anomaly-score-value" style="color:${color};">${scorePct}%</span>
                </div>
                <div class="anomaly-metrics">${topMetrics}</div>
            </div>`;
    }).join('');
}

// ─── Sensor Trends ──────────────────────────────────────────────────────────

async function loadSensorTrends() {
    const equipmentId = document.getElementById('analytics-equipment-select').value;
    if (!equipmentId) {
        document.getElementById('analytics-trends-grid').innerHTML =
            '<div class="empty-state"><div class="empty-state-icon">📉</div><div class="empty-state-text">Select an equipment to view sensor trends</div></div>';
        return;
    }

    const grid = document.getElementById('analytics-trends-grid');
    grid.innerHTML = '<div class="empty-state"><div class="loading-spinner"></div></div>';

    try {
        const result = await apiRequest('/api/analytics/sensor-trends/' + equipmentId + '?hours=24');
        analyticsData.sensorTrends = result.data.trends;
        renderSensorTrends(result.data.trends);
    } catch (error) {
        grid.innerHTML = '<div class="empty-state"><div class="empty-state-icon">❌</div><div class="empty-state-text">Failed to load sensor trends</div></div>';
    }
}

function renderSensorTrends(trends) {
    const grid = document.getElementById('analytics-trends-grid');

    // Destroy existing trend charts
    Object.keys(chartInstances).forEach(key => {
        if (key.startsWith('chart-trend-')) {
            chartInstances[key].destroy();
            delete chartInstances[key];
        }
    });

    if (!trends || Object.keys(trends).length === 0) {
        grid.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📉</div><div class="empty-state-text">No sensor data available</div></div>';
        return;
    }

    grid.innerHTML = '';

    Object.entries(trends).forEach(([metric, data]) => {
        const card = document.createElement('div');
        card.className = 'analytics-trend-card';

        const title = document.createElement('h3');
        title.className = 'analytics-trend-title';
        title.textContent = metric.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) + ' (' + data.unit + ')';
        card.appendChild(title);

        const chartContainer = document.createElement('div');
        chartContainer.className = 'analytics-trend-chart-container';
        const canvas = document.createElement('canvas');
        canvas.id = 'chart-trend-' + metric;
        chartContainer.appendChild(canvas);
        card.appendChild(chartContainer);
        grid.appendChild(card);

        // Prepare data
        const labels = data.data_points.map(p => {
            const d = new Date(p.timestamp);
            return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
        });
        const values = data.data_points.map(p => p.value);

        // Build datasets
        const datasets = [{
            label: metric.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
            data: values,
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            borderWidth: 2,
            pointRadius: 1,
            pointHoverRadius: 4,
            fill: true,
            tension: 0.3,
        }];

        // Add threshold lines
        if (data.thresholds) {
            const t = data.thresholds;
            if (t.normal !== undefined) {
                datasets.push({
                    label: 'Normal (' + t.normal + ')',
                    data: Array(labels.length).fill(t.normal),
                    borderColor: '#10b98180',
                    borderWidth: 1,
                    borderDash: [5, 5],
                    pointRadius: 0,
                    fill: false,
                });
            }
            if (t.warn !== undefined) {
                datasets.push({
                    label: 'Warning (' + t.warn + ')',
                    data: Array(labels.length).fill(t.warn),
                    borderColor: '#f59e0b80',
                    borderWidth: 1,
                    borderDash: [5, 5],
                    pointRadius: 0,
                    fill: false,
                });
            }
            if (t.critical !== undefined) {
                datasets.push({
                    label: 'Critical (' + t.critical + ')',
                    data: Array(labels.length).fill(t.critical),
                    borderColor: '#ef444480',
                    borderWidth: 1,
                    borderDash: [5, 5],
                    pointRadius: 0,
                    fill: false,
                });
            }
        }

        chartInstances['chart-trend-' + metric] = new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: { labels: labels, datasets: datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'nearest', intersect: false },
                plugins: {
                    legend: { position: 'bottom', labels: { boxWidth: 10, padding: 8, font: { size: 10 } } },
                    tooltip: CHART_TOOLTIP,
                },
                scales: {
                    y: { grid: { color: 'rgba(148, 163, 184, 0.06)' } },
                    x: { grid: { display: false }, ticks: { maxTicksLimit: 12 } },
                },
                animation: { duration: 500 },
            }
        });
    });
}

// ─── Export Report ──────────────────────────────────────────────────────────

function exportAnalyticsReport() {
    showToast('Generating report for print/PDF...', 'info');

    const plantOee = analyticsData.oee ? analyticsData.oee.plant_oee : {};
    const cost = analyticsData.costSummary || {};
    const timeline = analyticsData.predictiveTimeline || [];

    const w = window.open('', '_blank');
    w.document.write(`<!DOCTYPE html><html><head><title>Tata Steel — Maintenance Analytics Report</title>
<style>
body{font-family:Inter,sans-serif;background:#0a0e1a;color:#f1f5f9;padding:20px}
h1{color:#3b82f6;border-bottom:2px solid #3b82f6;padding-bottom:10px}
h2{color:#06b6d4;margin-top:20px}
table{width:100%;border-collapse:collapse;margin:15px 0}
th,td{border:1px solid #1a2035;padding:8px;text-align:left}
th{background:#111827;color:#f1f5f9}
.metric{font-weight:bold;color:#3b82f6}
.good{color:#10b981}.warning{color:#f59e0b}.critical{color:#ef4444}
.section{margin:20px 0;padding:15px;background:#111827;border-radius:8px}
.tl{margin:10px 0;padding:10px;border-left:3px solid #3b82f6}
</style></head><body>
<h1>🏭 Tata Steel — Intelligent Maintenance Wizard Analytics Report</h1>
<p>Generated: ${new Date().toLocaleString()}</p>
<div class="section"><h2>📊 Overall Equipment Effectiveness (OEE)</h2>
<p>Plant OEE: <strong>${plantOee.plant_oee || 'N/A'}%</strong> (${plantOee.oee_rating || 'N/A'})</p>
<table><tr><th>Equipment</th><th>OEE</th><th>Availability</th><th>Performance</th><th>Quality</th></tr>
${(analyticsData.oee ? analyticsData.oee.equipment_oee : []).map(eq =>
        `<tr><td>${eq.equipment_name}</td><td class="metric">${eq.oee}%</td><td>${eq.availability}%</td><td>${eq.performance}%</td><td>${eq.quality}%</td></tr>`
    ).join('')}</table></div>
<div class="section"><h2>💰 Cost Impact Analysis</h2>
<table><tr><th>Category</th><th>Annual Cost (₹)</th></tr>
<tr><td>Critical Downtime Risk</td><td class="critical">₹${Math.round((cost.annual_downtime_risk ? cost.annual_downtime_risk.critical : 0) / 100000).toLocaleString()} Lakhs</td></tr>
<tr><td>Warning Downtime Risk</td><td class="warning">₹${Math.round((cost.annual_downtime_risk ? cost.annual_downtime_risk.warning : 0) / 100000).toLocaleString()} Lakhs</td></tr>
<tr><td>Total Annual Risk</td><td class="metric">₹${Math.round((cost.annual_downtime_risk ? cost.annual_downtime_risk.total : 0) / 100000).toLocaleString()} Lakhs</td></tr>
<tr><td>Annual Maintenance Cost</td><td>₹${Math.round((cost.maintenance_costs ? cost.maintenance_costs.estimated_annual_cost : 0) / 100000).toLocaleString()} Lakhs</td></tr>
<tr><td>Preventive ROI</td><td class="good">${cost.roi ? cost.roi.preventive_roi : 0}:1</td></tr>
<tr><td>Net Savings</td><td class="good">₹${Math.round((cost.roi ? cost.roi.net_savings : 0) / 100000).toLocaleString()} Lakhs</td></tr>
</table></div>
<div class="section"><h2>🔮 Predictive Maintenance Timeline</h2>
${timeline.map(item => `<div class="tl" style="border-left-color:${item.color}">
<strong>${item.urgency} ${item.equipment_name}</strong> — RUL: ${item.min_rul_hours}h
<p>Status: ${item.status} | Action: ${item.recommended_action}</p></div>`).join('')}</div>
<script>window.onload=function(){window.print()}</script></body></html>`);
    w.document.close();

    showToast('Report generated! Use Ctrl+P to save as PDF.', 'success');
}