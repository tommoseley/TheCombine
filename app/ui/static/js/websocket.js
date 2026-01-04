/**
 * WebSocket client for real-time execution updates
 * Calm Authority - The Combine
 */

class ExecutionWebSocket {
    constructor(executionId) {
        this.executionId = executionId;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.connectionStatus = 'disconnected';
    }

    connect() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            return;
        }
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${window.location.host}/api/v1/ws/executions/${this.executionId}`;
        
        try {
            this.ws = new WebSocket(url);
        } catch (e) {
            console.error('WebSocket creation failed:', e);
            this.onConnectionError(e);
            return;
        }
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.connectionStatus = 'connected';
            this.reconnectAttempts = 0;
            this.updateConnectionIndicator(true);
            this.onConnected();
        };
        
        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleEvent(data);
            } catch (e) {
                console.error('Failed to parse WebSocket message:', e);
            }
        };
        
        this.ws.onclose = (event) => {
            console.log('WebSocket disconnected', event.code, event.reason);
            this.connectionStatus = 'disconnected';
            this.updateConnectionIndicator(false);
            this.onDisconnected();
            
            // Don't reconnect if closed cleanly or execution is done
            if (event.code !== 1000 && event.code !== 1001) {
                this.attemptReconnect();
            }
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.onConnectionError(error);
        };
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
            console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            
            this.connectionStatus = 'reconnecting';
            this.showReconnectMessage(delay);
            
            setTimeout(() => this.connect(), delay);
        } else {
            this.connectionStatus = 'failed';
            this.onReconnectFailed();
        }
    }

    handleEvent(data) {
        switch (data.event_type) {
            case 'connected':
                console.log('Subscribed to execution events');
                break;
            case 'ping':
                // Keepalive, ignore
                break;
            case 'step_started':
                this.showToast(`Step started: ${data.step_id}`, 'info');
                this.onStepStarted(data);
                break;
            case 'step_completed':
                this.showToast(`Step completed: ${data.step_id}`, 'success');
                this.onStepCompleted(data);
                break;
            case 'waiting_acceptance':
                this.showToast('Document ready for review', 'warning');
                this.onWaitingAcceptance(data);
                break;
            case 'waiting_clarification':
                this.showToast('Clarification needed', 'warning');
                this.onWaitingClarification(data);
                break;
            case 'completed':
                this.showToast('Execution completed!', 'success');
                this.onCompleted(data);
                break;
            case 'failed':
                this.showToast('Execution failed', 'error');
                this.onFailed(data);
                break;
            default:
                console.log('Unknown event:', data);
        }
    }

    updateConnectionIndicator(connected) {
        const indicator = document.getElementById('ws-connection-indicator');
        if (indicator) {
            indicator.className = connected ? 'ws-indicator connected' : 'ws-indicator disconnected';
            indicator.title = connected ? 'Live updates active' : 'Live updates disconnected';
        }
    }

    showReconnectMessage(delay) {
        const container = document.getElementById('ws-reconnect-message');
        if (container) {
            container.textContent = `Connection lost. Reconnecting in ${Math.round(delay/1000)}s...`;
            container.style.display = 'block';
        }
    }

    hideReconnectMessage() {
        const container = document.getElementById('ws-reconnect-message');
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
        const container = document.getElementById('ws-reconnect-message');
        if (container) {
            container.textContent = 'Unable to connect. Please refresh the page.';
            container.style.display = 'block';
        }
    }
    onStepStarted(data) {}
    onStepCompleted(data) {}
    onWaitingAcceptance(data) {}
    onWaitingClarification(data) {}
    onCompleted(data) {}
    onFailed(data) {}

    close() {
        if (this.ws) {
            this.ws.close(1000, 'Client closing');
            this.ws = null;
        }
    }
}

// Auto-initialize if execution detail page
document.addEventListener('DOMContentLoaded', function() {
    const execDetail = document.querySelector('.execution-detail[data-execution-id]');
    if (execDetail) {
        const execId = execDetail.dataset.executionId;
        const ws = new ExecutionWebSocket(execId);
        
        ws.onStepStarted = function(data) {
            // Refresh step progress
            const progress = document.getElementById('step-progress');
            if (progress && typeof htmx !== 'undefined') {
                htmx.trigger(progress, 'refresh');
            }
        };
        
        ws.onStepCompleted = function(data) {
            // Refresh step progress and status
            const progress = document.getElementById('step-progress');
            const status = document.getElementById('execution-status');
            if (typeof htmx !== 'undefined') {
                if (progress) htmx.trigger(progress, 'refresh');
                if (status) htmx.trigger(status, 'refresh');
            }
        };
        
        ws.onWaitingAcceptance = function(data) {
            location.reload();
        };
        
        ws.onWaitingClarification = function(data) {
            location.reload();
        };
        
        ws.onCompleted = function(data) {
            location.reload();
        };
        
        ws.onFailed = function(data) {
            location.reload();
        };
        
        ws.connect();
        
        // Store reference for cleanup
        window._executionWs = ws;
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (window._executionWs) {
        window._executionWs.close();
    }
});

// Export for use
window.ExecutionWebSocket = ExecutionWebSocket;
