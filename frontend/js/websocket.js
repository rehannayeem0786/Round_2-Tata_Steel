/**
 * WebSocket client — Handles real-time connection for sensor data
 * and alert notifications.
 */

let ws = null;
let wsReconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 10;
const RECONNECT_DELAY = 3000;

// Callback registrations
const wsCallbacks = {
    sensor_update: [],
    alert: [],
    pong: [],
};

/**
 * Register a callback for a specific WebSocket message type.
 */
function onWsMessage(type, callback) {
    if (wsCallbacks[type]) {
        wsCallbacks[type].push(callback);
    }
}

/**
 * Connect to the WebSocket server.
 */
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    try {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            wsReconnectAttempts = 0;
            updateConnectionStatus(true);
            console.log('🔌 WebSocket connected');

            // Start ping interval
            if (ws._pingInterval) clearInterval(ws._pingInterval);
            ws._pingInterval = setInterval(() => {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send('ping');
                }
            }, 30000);
        };

        ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                const type = message.type;

                if (wsCallbacks[type]) {
                    wsCallbacks[type].forEach(cb => cb(message.data));
                }
            } catch (e) {
                // Non-JSON message (e.g., pong text)
            }
        };

        ws.onclose = () => {
            updateConnectionStatus(false);
            if (ws && ws._pingInterval) clearInterval(ws._pingInterval);

            if (wsReconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                wsReconnectAttempts++;
                console.log(`🔄 Reconnecting (${wsReconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`);
                setTimeout(connectWebSocket, RECONNECT_DELAY);
            }
        };

        ws.onerror = (error) => {
            console.error('❌ WebSocket error:', error);
            updateConnectionStatus(false);
        };
    } catch (e) {
        console.error('❌ WebSocket connection failed:', e);
        updateConnectionStatus(false);
    }
}

/**
 * Update the connection status indicator in the sidebar.
 */
function updateConnectionStatus(connected) {
    const dot = document.getElementById('ws-status-dot');
    const text = document.getElementById('ws-status-text');

    if (connected) {
        dot.classList.add('connected');
        text.textContent = 'Live connected';
    } else {
        dot.classList.remove('connected');
        text.textContent = 'Reconnecting...';
    }
}

// Auto-connect on load
document.addEventListener('DOMContentLoaded', () => {
    connectWebSocket();
});
