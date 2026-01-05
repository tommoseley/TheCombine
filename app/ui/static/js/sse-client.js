/**
 * Server-Sent Events (SSE) client for real-time execution updates
 * Calm Authority - The Combine
 * 
 * Lightweight alternative to WebSocket for one-way streaming.
 */

class ExecutionSSE {
    constructor(executionId, options = {}) {
        this.executionId = executionId;
        this.eventSource = null;
        this.connectionStatus = 'disconnected';
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = options.maxReconnectAttempts || 5;
        this.reconnectDelay = options.reconnectDelay || 1000;
        this.baseUrl = options.baseUrl || '/api/v1';
    }

    connect() {
        if (this.eventSource && this.eventSource.readyState !== EventSource.CLOSED) {
            return;
        }
        
        const url = `${this.baseUrl}/executions/${this.executionId}/stream`;
        
        try {
            this.eventSource = new EventSource(url);
        } catch (e) {
            console.error('SSE connection failed:', e);
            this.onConnectionError(e);
            return;
        }
        
        this.connectionStatus = 'connecting';
        
        // Handle connection open
        this.eventSource.onopen = () => {
            console.log('SSE connected');
            this.connectionStatus = 'connected';
            this.reconnectAttempts = 0;
            this.updateConnectionIndicator(true);
            this.onConnected();
        };
        
        // Handle generic messages (data-only)
        this.eventSource.onmessage = (event) => {
            this.handleMessage(event);
        };
        
        // Handle named events
        this.eventSource.addEventListener('connected', (e) => this.handleEvent('connected', e));
        this.eventSource.addEventListener('step_started', (e) => this.handleEvent('step_started', e));
        this.eventSource.addEventListener('step_completed', (e) => this.handleEvent('step_completed', e));
        this.eventSource.addEventListener('clarification_needed', (e) => this.handleEvent('clarification_needed', e));
        this.eventSource.addEventListener('execution_completed', (e) => this.handleEvent('execution_completed', e));
        this.eventSource.addEventListener('execution_failed', (e) => this.handleEvent('execution_failed', e));
        this.eventSource.addEventListener('execution_cancelled', (e) => this.handleEvent('execution_cancelled', e));
        
        // Handle errors
        this.eventSource.onerror = (error) => {
            console.error('SSE error:', error);
            this.connectionStatus = 'disconnected';
            this.updateConnectionIndicator(false);
            this.onDisconnected();
            
            // Close and attempt reconnect
            this.eventSource.close();
            this.attemptReconnect();
        };
    }

    handleMessage(event) {
        try {
            const data = JSON.parse(event.data);
            this.routeEvent(data.event_type || 'message', data);
        } catch (e) {
            // Not JSON, might be a comment or simple message
            console.log('SSE message:', event.data);
        }
    }

    handleEvent(eventType, event) {
        try {
            const data = JSON.parse(event.data);
            this.routeEvent(eventType, data);
        } catch (e) {
            console.error('Failed to parse SSE event:', e);
        }
    }

    routeEvent(eventType, data) {
        switch (eventType) {
            case 'connected':
                console.log('Subscribed to execution events');
                break;
            case 'step_started':
                this.showToast(`Step started: ${data.step_id || data.data?.step_id}`, 'info');
                this.onStepStarted(data);
                break;
            case 'step_completed':
                this.showToast(`Step completed: ${data.step_id || data.data?.step_id}`, 'success');
                this.onStepCompleted(data);
                break;
            case 'clarification_needed':
                this.showToast('Clarification needed', 'warning');
                this.onClarificationNeeded(data);
                break;
            case 'execution_completed':
                this.showToast('Execution completed!', 'success');
                this.onCompleted(data);
                break;
            case 'execution_failed':
                this.showToast('Execution failed', 'error');
                this.onFailed(data);
                break;
            case 'execution_cancelled':
                this.showToast('Execution cancelled', 'warning');
                this.onCancelled(data);
                break;
            default:
                console.log('SSE event:', eventType, data);
        }
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
            console.log(`SSE reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            
            this.connectionStatus = 'reconnecting';
            this.showReconnectMessage(delay);
            
            setTimeout(() => this.connect(), delay);
        } else {
            this.connectionStatus = 'failed';
            this.onReconnectFailed();
        }
    }

    updateConnectionIndicator(connected) {
        const indicator = document.getElementById('sse-connection-indicator');
        if (indicator) {
            indicator.className = connected ? 'sse-indicator connected' : 'sse-indicator disconnected';
            indicator.title = connected ? 'Live updates active' : 'Live updates disconnected';
        }
    }

    showReconnectMessage(delay) {
        const container = document.getElementById('sse-reconnect-message');
        if (container) {
            container.textContent = `Connection lost. Reconnecting in ${Math.round(delay/1000)}s...`;
            container.style.display = 'block';
        }
    }

    hideReconnectMessage() {
        const container = document.getElementById('sse-reconnect-message');
        if (container) {
            container.style.display = 'none';
        }
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        
        container.appendChild(toast);
        
        // Animate in
        setTimeout(() => toast.classList.add('show'), 10);
        
        // Remove after 4 seconds
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    // Override these in your page
    onConnected() {
        this.hideReconnectMessage();
    }
    onDisconnected() {}
    onConnectionError(error) {}
    onReconnectFailed() {
        const container = document.getElementById('sse-reconnect-message');
        if (container) {
            container.textContent = 'Unable to connect. Please refresh the page.';
            container.style.display = 'block';
        }
    }
    onStepStarted(data) {}
    onStepCompleted(data) {}
    onClarificationNeeded(data) {}
    onCompleted(data) {}
    onFailed(data) {}
    onCancelled(data) {}

    close() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
        this.connectionStatus = 'disconnected';
    }

    /**
     * Get connection status
     */
    getStatus() {
        return this.connectionStatus;
    }
}

/**
 * Progress tracker that updates UI based on SSE events
 */
class ExecutionProgressTracker {
    constructor(executionId, options = {}) {
        this.executionId = executionId;
        this.sse = new ExecutionSSE(executionId, options);
        this.elapsedTimer = null;
        this.startTime = Date.now();
        
        this.setupEventHandlers();
    }

    setupEventHandlers() {
        this.sse.onConnected = () => {
            this.startElapsedTimer();
        };
        
        this.sse.onStepStarted = (data) => {
            this.refreshProgress();
            this.updateCurrentStep(data.step_id || data.data?.step_id);
        };
        
        this.sse.onStepCompleted = (data) => {
            this.refreshProgress();
            this.refreshStatus();
        };
        
        this.sse.onClarificationNeeded = (data) => {
            location.reload();
        };
        
        this.sse.onCompleted = (data) => {
            this.stopElapsedTimer();
            location.reload();
        };
        
        this.sse.onFailed = (data) => {
            this.stopElapsedTimer();
            location.reload();
        };
        
        this.sse.onCancelled = (data) => {
            this.stopElapsedTimer();
            location.reload();
        };
    }

    connect() {
        this.sse.connect();
    }

    close() {
        this.stopElapsedTimer();
        this.sse.close();
    }

    refreshProgress() {
        const progress = document.getElementById('step-progress');
        if (progress && typeof htmx !== 'undefined') {
            htmx.trigger(progress, 'refresh');
        }
    }

    refreshStatus() {
        const status = document.getElementById('execution-status');
        if (status && typeof htmx !== 'undefined') {
            htmx.trigger(status, 'refresh');
        }
    }

    updateCurrentStep(stepId) {
        const currentStepEl = document.getElementById('current-step-name');
        if (currentStepEl && stepId) {
            currentStepEl.textContent = stepId;
        }
    }

    startElapsedTimer() {
        this.startTime = Date.now();
        const elapsedEl = document.getElementById('execution-elapsed');
        
        if (elapsedEl) {
            this.elapsedTimer = setInterval(() => {
                const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
                const mins = Math.floor(elapsed / 60);
                const secs = elapsed % 60;
                elapsedEl.textContent = `${mins}:${secs.toString().padStart(2, '0')}`;
            }, 1000);
        }
    }

    stopElapsedTimer() {
        if (this.elapsedTimer) {
            clearInterval(this.elapsedTimer);
            this.elapsedTimer = null;
        }
    }
}

// Auto-initialize if execution detail page (prefer SSE over WebSocket)
document.addEventListener('DOMContentLoaded', function() {
    const execDetail = document.querySelector('.execution-detail[data-execution-id][data-use-sse]');
    if (execDetail) {
        const execId = execDetail.dataset.executionId;
        const tracker = new ExecutionProgressTracker(execId);
        tracker.connect();
        
        // Store reference for cleanup
        window._executionTracker = tracker;
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (window._executionTracker) {
        window._executionTracker.close();
    }
});

// Export for use
window.ExecutionSSE = ExecutionSSE;
window.ExecutionProgressTracker = ExecutionProgressTracker;
