/**
 * Chat module — Conversational AI interface with multi-turn
 * support, feedback buttons, agent execution trace, and
 * conversation history.
 */

let chatState = {
    conversationId: null,
    isProcessing: false,
    messageCount: 0,
    imageData: null,
};

// ─── Agentic "thinking" pipeline animation ───────────────────────────────────
const AGENT_THINKING_STAGES = [
    '🧭 Classifying intent...',
    '🔧 Detecting equipment...',
    '📚 Retrieving knowledge (RAG)...',
    '🧠 Running ML anomaly scan...',
    '🤖 Agents reasoning...',
    '✍️ Composing answer...',
];
let _thinkingTimer = null;

function startAgentThinking() {
    const el = document.getElementById('agent-thinking-status');
    if (!el) return;
    let i = 0;
    el.textContent = AGENT_THINKING_STAGES[0];
    el.classList.add('visible');
    clearInterval(_thinkingTimer);
    _thinkingTimer = setInterval(() => {
        // advance but hold on the last stage until the response arrives
        i = Math.min(i + 1, AGENT_THINKING_STAGES.length - 1);
        el.textContent = AGENT_THINKING_STAGES[i];
    }, 1100);
}

function stopAgentThinking() {
    clearInterval(_thinkingTimer);
    _thinkingTimer = null;
    const el = document.getElementById('agent-thinking-status');
    if (el) { el.classList.remove('visible'); el.textContent = ''; }
}

// Icon per agent / pipeline step for the execution trace
const AGENT_ICONS = {
    'Intent Classifier': '🧭',
    'Equipment Detector': '🔧',
    'RAG Engine': '📚',
    'Diagnostic Agent': '🔍',
    'Risk Agent': '🚦',
    'Recommendation Agent': '🛠️',
    'Cost Impact Agent': '💰',
    'Action Agent': '⚙️',
    'Reporting Agent': '📋',
    'Alerting Agent': '🚨',
    'Feedback Agent': '🔁',
    'General Assistant': '💬',
};
function agentIcon(name) {
    return AGENT_ICONS[name] || '▸';
}

// Speech Recognition Setup
let recognition = null;
let isRecording = false;

if ('webkitSpeechRecognition' in window) {
    recognition = new webkitSpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    
    recognition.onstart = function() {
        isRecording = true;
        const voiceBtn = document.getElementById('chat-voice-btn');
        if (voiceBtn) voiceBtn.classList.add('recording');
        const waveContainer = document.getElementById('voice-wave-container');
        if (waveContainer) waveContainer.style.display = 'flex';
        document.getElementById('chat-input').placeholder = "Listening...";
    };
    
    recognition.onresult = function(event) {
        let interimTranscript = '';
        let finalTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
                finalTranscript += event.results[i][0].transcript;
            } else {
                interimTranscript += event.results[i][0].transcript;
            }
        }
        
        const input = document.getElementById('chat-input');
        if (finalTranscript) {
            input.value = finalTranscript;
            sendMessage(); // Auto-send when final
        } else {
            input.value = interimTranscript;
        }
    };
    
    recognition.onerror = function(event) {
        console.error('Speech recognition error:', event.error);
        let errorMsg = 'Microphone error: ' + event.error;
        if (event.error === 'not-allowed') {
            errorMsg = 'Microphone blocked. Please allow mic access in your browser.';
        } else if (event.error === 'network') {
            errorMsg = 'Network error. Speech recognition requires internet.';
        }
        showToast(errorMsg, 'error');
        toggleVoiceMode(false);
    };
    
    recognition.onend = function() {
        isRecording = false;
        const voiceBtn = document.getElementById('chat-voice-btn');
        if (voiceBtn) voiceBtn.classList.remove('recording');
        const waveContainer = document.getElementById('voice-wave-container');
        if (waveContainer) waveContainer.style.display = 'none';
        document.getElementById('chat-input').placeholder = "Ask about equipment diagnostics, maintenance, risks...";
    };
}

function toggleVoiceMode(forceState) {
    if (!recognition) {
        showToast('Speech recognition is not supported in your browser.', 'error');
        return;
    }
    
    const shouldRecord = forceState !== undefined ? forceState : !isRecording;
    
    if (shouldRecord) {
        try {
            recognition.start();
            const voiceBtn = document.getElementById('chat-voice-btn');
            if (voiceBtn) voiceBtn.classList.add('recording');
        } catch (e) {
            console.error('Recognition already started');
        }
    } else {
        recognition.stop();
    }
}

/**
 * Send a message from the chat input.
 */
async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();

    if (!message || chatState.isProcessing) return;

    // Hide welcome if visible
    const welcome = document.getElementById('chat-welcome');
    if (welcome) welcome.style.display = 'none';

    // Add user message
    addMessageToChat('user', message, { image: chatState.imageData });
    
    // Store image data for payload and clear preview
    const payloadImageData = chatState.imageData;
    removeImagePreview();

    input.value = '';
    input.style.height = 'auto';

    // Show typing indicator
    setTypingIndicator(true);
    chatState.isProcessing = true;
    updateSendButton();

    try {
        const result = await apiRequest('/api/chat', {
            method: 'POST',
            body: JSON.stringify({
                message: message,
                conversation_id: chatState.conversationId,
                user_role: document.getElementById('user-role-select').value,
                image_data: payloadImageData
            }),
        });

        setTypingIndicator(false);

        if (result.success && result.data) {
            chatState.conversationId = result.data.conversation_id;

            // Add assistant message with metadata + execution trace
            addMessageToChat('assistant', result.data.response, {
                agents: result.data.agents_used,
                intent: result.data.intent,
                sources: result.data.sources,
                conversationId: result.data.conversation_id,
                messageIndex: result.data.message_index,
                executionTrace: result.data.execution_trace,
                totalTimeMs: result.data.total_time_ms,
            });
            
            // Refresh conversation history
            loadConversationHistory();
        }
    } catch (error) {
        setTypingIndicator(false);
        addMessageToChat('assistant', '⚠️ Sorry, I encountered an error processing your request. Please try again or check if the server is running.', {
            agents: ['Error Handler'],
        });
        showToast('Failed to get response: ' + error.message, 'error');
    }

    chatState.isProcessing = false;
    updateSendButton();
}

/**
 * Send a quick action message.
 */
function sendQuickMessage(message) {
    const input = document.getElementById('chat-input');
    input.value = message;
    sendMessage();
}

/**
 * Add a message to the chat display.
 */
function addMessageToChat(role, content, meta = {}) {
    const container = document.getElementById('chat-messages');
    const indicator = document.getElementById('typing-indicator');

    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    chatState.messageCount++;

    const avatarEmoji = role === 'user' ? '👤' : '🤖';

    let metaHtml = '';
    let imageHtml = '';
    let traceHtml = '';
    let sourcesHtml = '';
    
    if (meta.image) {
        imageHtml = `<br><img src="${meta.image}" style="max-height: 150px; border-radius: var(--radius-sm); margin-top: 10px;">`;
    }

    if (role === 'assistant') {
        const agentTags = (meta.agents || []).map(a => `<span class="agent-tag">${agentIcon(a)} ${a}</span>`).join('');

        // Build execution trace HTML
        if (meta.executionTrace && meta.executionTrace.length > 0) {
            const traceSteps = meta.executionTrace.map(step => `
                <div class="agent-trace-step">
                    <div class="agent-trace-step-dot done">${step.step}</div>
                    <div class="agent-trace-step-content">
                        <div class="agent-trace-step-name">${agentIcon(step.agent)} ${step.agent}</div>
                        <div class="agent-trace-step-action">${escapeHtml(step.action || '')}</div>
                    </div>
                    <div class="agent-trace-step-time">${step.time_ms}ms</div>
                </div>
            `).join('');

            const intentBadge = meta.intent
                ? `<span class="agent-trace-intent">intent: ${escapeHtml(meta.intent)}</span>` : '';

            traceHtml = `
                <div class="agent-trace">
                    <div class="agent-trace-header" onclick="this.parentElement.classList.toggle('collapsed')">
                        <div class="agent-trace-title">
                            <span>⚡</span> Agent Pipeline (${meta.executionTrace.length} steps) ${intentBadge}
                        </div>
                        <div class="agent-trace-time">${meta.totalTimeMs || 0}ms total</div>
                    </div>
                    <div class="agent-trace-steps">
                        ${traceSteps}
                    </div>
                </div>
            `;
        }

        // Build source citations (explainability — grounded in knowledge base)
        if (meta.sources && meta.sources.length > 0) {
            const chips = meta.sources.map(s => {
                const rel = s.relevance != null ? Math.round(s.relevance * 100) + '%' : '';
                const name = (s.source || 'document').replace(/_/g, ' ');
                return `<span class="source-chip" title="${escapeHtml(s.category || '')} · relevance ${rel}">📄 ${escapeHtml(name)}${rel ? ` <em>${rel}</em>` : ''}</span>`;
            }).join('');
            sourcesHtml = `
                <div class="message-sources">
                    <span class="message-sources-label">Grounded in:</span>
                    ${chips}
                </div>`;
        }

        metaHtml = `
            <div class="message-meta">
                <div class="message-agents">${agentTags}</div>
                <div class="message-feedback">
                    <button class="feedback-btn" onclick="playAudioForMessage(this)" title="Read Aloud">🔊</button>
                    <button class="feedback-btn" onclick="submitFeedback('${meta.conversationId}', ${meta.messageIndex}, 'positive', this)" title="Helpful">👍</button>
                    <button class="feedback-btn" onclick="submitFeedback('${meta.conversationId}', ${meta.messageIndex}, 'negative', this)" title="Not helpful">👎</button>
                </div>
            </div>
            ${traceHtml}
            ${sourcesHtml}
        `;
    }

    msgDiv.innerHTML = `
        <div class="message-avatar">${avatarEmoji}</div>
        <div class="message-content">
            <div class="message-bubble">${role === 'assistant' ? markdownToHtml(content) : escapeHtml(content)}${imageHtml}</div>
            ${metaHtml}
        </div>
    `;

    if (indicator) {
        container.insertBefore(msgDiv, indicator);
    } else {
        container.appendChild(msgDiv);
    }

    container.scrollTop = container.scrollHeight;
    
}

/**
 * Manually play audio for a specific message
 */
function playAudioForMessage(btn) {
    if (!('speechSynthesis' in window)) {
        showToast('Speech synthesis not supported in this browser.', 'error');
        return;
    }
    
    // Get the text from the message bubble next to it
    const bubble = btn.closest('.message-content').querySelector('.message-bubble');
    const text = bubble.innerText;
    
    window.speechSynthesis.cancel();
    
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.05;
    
    const ttsBtn = document.getElementById('chat-tts-stop-btn');
    const pauseIcon = document.getElementById('tts-icon-pause');
    const playIcon = document.getElementById('tts-icon-play');
    
    utterance.onstart = function() {
        if (ttsBtn) {
            ttsBtn.style.display = 'flex';
            ttsBtn.title = "Pause Audio";
            if (pauseIcon) pauseIcon.style.display = 'block';
            if (playIcon) playIcon.style.display = 'none';
        }
    };
    
    utterance.onend = function() {
        if (ttsBtn) ttsBtn.style.display = 'none';
    };
    
    utterance.onerror = function() {
        if (ttsBtn) ttsBtn.style.display = 'none';
    };
    
    if (ttsBtn) {
        ttsBtn.onclick = function() {
            if (window.speechSynthesis.paused) {
                window.speechSynthesis.resume();
                ttsBtn.title = "Pause Audio";
                if (pauseIcon) pauseIcon.style.display = 'block';
                if (playIcon) playIcon.style.display = 'none';
            } else {
                window.speechSynthesis.pause();
                ttsBtn.title = "Resume Audio";
                if (pauseIcon) pauseIcon.style.display = 'none';
                if (playIcon) playIcon.style.display = 'block';
            }
        };
    }
    
    window.speechSynthesis.speak(utterance);
}

function escapeHtml(text) {
    return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>');
}

/**
 * Toggle typing indicator visibility.
 */
function setTypingIndicator(visible) {
    const indicator = document.getElementById('typing-indicator');
    indicator.classList.toggle('visible', visible);

    if (visible) {
        startAgentThinking();
        const container = document.getElementById('chat-messages');
        container.scrollTop = container.scrollHeight;
    } else {
        stopAgentThinking();
    }
}

/**
 * Update send button state.
 */
function updateSendButton() {
    const btn = document.getElementById('chat-send-btn');
    btn.disabled = chatState.isProcessing;
}

/**
 * Handle keyboard shortcuts in chat input.
 */
function handleChatKeydown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }

    // Auto-resize textarea
    const textarea = event.target;
    setTimeout(() => {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }, 0);
}

/**
 * Submit feedback on a message.
 */
async function submitFeedback(conversationId, messageIndex, rating, buttonEl) {
    if (!conversationId) return;

    try {
        await apiRequest('/api/chat/feedback', {
            method: 'POST',
            body: JSON.stringify({
                conversation_id: conversationId,
                message_index: messageIndex,
                rating: rating,
            }),
        });

        // Update button states
        const parent = buttonEl.parentElement;
        parent.querySelectorAll('.feedback-btn').forEach(btn => {
            btn.classList.remove('active-positive', 'active-negative');
        });

        buttonEl.classList.add(rating === 'positive' ? 'active-positive' : 'active-negative');
        showToast('Thanks for your feedback!', 'success');
    } catch (error) {
        showToast('Failed to submit feedback', 'error');
    }
}

function handleImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function(e) {
        chatState.imageData = e.target.result;
        document.getElementById('chat-preview-img').src = e.target.result;
        document.getElementById('chat-image-preview').style.display = 'block';
    };
    reader.readAsDataURL(file);
    event.target.value = '';
}

function removeImagePreview() {
    chatState.imageData = null;
    document.getElementById('chat-image-preview').style.display = 'none';
    document.getElementById('chat-preview-img').src = '';
}

/* ═══ Conversation History ═══ */

async function loadConversationHistory() {
    try {
        const result = await apiRequest('/api/chat/conversations');
        if (!result.success) return;
        
        const list = document.getElementById('chat-history-list');
        if (!list) return;
        
        const conversations = result.data || [];
        
        if (conversations.length === 0) {
            list.innerHTML = '<div style="padding: 16px; text-align: center; color: var(--text-muted); font-size: 12px;">No conversations yet</div>';
            return;
        }
        
        list.innerHTML = conversations.slice(0, 20).map(conv => {
            const isActive = conv.id === chatState.conversationId;
            const title = conv.title || 'Untitled';
            const date = new Date(conv.updated_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
            
            return `
                <div class="chat-history-item ${isActive ? 'active' : ''}" onclick="loadConversation('${conv.id}')">
                    <div class="chat-history-item-title">${escapeHtml(title.substring(0, 50))}</div>
                    <div class="chat-history-item-date">${date}</div>
                </div>
            `;
        }).join('');
    } catch (e) {
        console.error('Failed to load conversation history:', e);
    }
}

async function loadConversation(conversationId) {
    try {
        const result = await apiRequest(`/api/chat/conversations/${conversationId}`);
        if (!result.success || !result.data) return;
        
        chatState.conversationId = conversationId;
        
        // Clear chat messages
        const container = document.getElementById('chat-messages');
        const indicator = document.getElementById('typing-indicator');
        const welcome = document.getElementById('chat-welcome');
        
        // Keep only indicator and welcome
        while (container.firstChild) {
            container.removeChild(container.firstChild);
        }
        container.appendChild(indicator);
        if (welcome) welcome.style.display = 'none';
        
        // Replay messages
        const messages = result.data.messages || [];
        for (const msg of messages) {
            if (msg.role === 'user') {
                addMessageToChat('user', msg.content);
            } else if (msg.role === 'assistant') {
                addMessageToChat('assistant', msg.content, {
                    agents: msg.agents || [],
                    intent: msg.intent,
                });
            }
        }
        
        // Update active state in sidebar
        loadConversationHistory();
    } catch (e) {
        showToast('Failed to load conversation', 'error');
    }
}

function startNewConversation() {
    chatState.conversationId = null;
    chatState.messageCount = 0;
    
    const container = document.getElementById('chat-messages');
    const welcome = document.getElementById('chat-welcome');
    const indicator = document.getElementById('typing-indicator');
    
    while (container.firstChild) {
        container.removeChild(container.firstChild);
    }
    
    if (welcome) {
        welcome.style.display = '';
        container.appendChild(welcome);
    }
    container.appendChild(indicator);
    
    loadConversationHistory();
}

// Load conversation history on page load
document.addEventListener('DOMContentLoaded', () => {
    loadConversationHistory();
});
