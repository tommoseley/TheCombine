/**
 * Thread Status Monitor - ADR-035
 * Monitors active LLM threads and shows generation status.
 * Persists across navigation via localStorage and server polling.
 */

const ThreadMonitor = {
    pollInterval: 2500,
    activePolls: new Map(),
    storageKey: 'combine_active_builds',
    
    async init(projectId, docTypeId = null, options = {}) {
        if (!projectId) return;
        
        const {
            onActiveThread = null,
            onProgress = null,
            onComplete = null,
            onError = null,
            containerSelector = '#thread-status-container',
        } = options;
        
        // Check localStorage first
        const localBuild = this.getLocalBuild(projectId, docTypeId);
        if (localBuild && localBuild.threadId) {
            await this.checkTrackedBuild(localBuild, options, containerSelector);
            return;
        }
        
        // Check server for active threads
        try {
            const response = await fetch(`/api/commands/projects/${projectId}/threads?active=true`);
            if (!response.ok) return;
            
            const data = await response.json();
            let threads = data.threads || [];
            
            if (docTypeId) {
                threads = threads.filter(t => {
                    const targetDoc = t.target_ref?.doc_type;
                    return targetDoc === docTypeId || targetDoc === docTypeId.replace(/_/g, '');
                });
            }
            
            if (threads.length === 0) return;
            
            const thread = threads[0];
            if (onActiveThread) onActiveThread(thread);
            else this.showDefaultStatus(containerSelector, thread);
            
            this.startPolling(thread.thread_id, {
                projectId, docTypeId,
                onProgress: onProgress || ((t) => this.updateDefaultStatus(containerSelector, t)),
                onComplete: onComplete || ((t) => this.handleDefaultComplete(containerSelector, t)),
                onError,
            });
        } catch (error) {
            console.error('ThreadMonitor init error:', error);
            if (onError) onError(error);
        }
    },

    
    async checkTrackedBuild(localBuild, options, containerSelector) {
        const { threadId, projectId, docTypeId, startedAt } = localBuild;
        
        if (Date.now() - startedAt > 10 * 60 * 1000) {
            this.clearLocalBuild(projectId, docTypeId);
            return;
        }
        
        try {
            const response = await fetch(`/api/commands/threads/${threadId}`);
            if (!response.ok) {
                this.clearLocalBuild(projectId, docTypeId);
                return;
            }
            
            const thread = await response.json();
            
            if (thread.status === 'complete' || thread.status === 'failed' || thread.status === 'canceled') {
                this.clearLocalBuild(projectId, docTypeId);
                if (options.onComplete) options.onComplete(thread);
                else this.handleDefaultComplete(containerSelector, thread);
                return;
            }
            
            if (options.onActiveThread) options.onActiveThread(thread);
            else this.showDefaultStatus(containerSelector, thread);
            
            this.startPolling(threadId, {
                projectId, docTypeId,
                onProgress: options.onProgress || ((t) => this.updateDefaultStatus(containerSelector, t)),
                onComplete: options.onComplete || ((t) => this.handleDefaultComplete(containerSelector, t)),
                onError: options.onError,
            });
        } catch (error) {
            console.error('ThreadMonitor checkTrackedBuild error:', error);
            this.clearLocalBuild(projectId, docTypeId);
        }
    },
    
    trackBuild(projectId, docTypeId, threadId) {
        const key = `${projectId}:${docTypeId || 'default'}`;
        const builds = this.getAllLocalBuilds();
        builds[key] = { threadId, projectId, docTypeId, startedAt: Date.now() };
        localStorage.setItem(this.storageKey, JSON.stringify(builds));
    },
    
    getLocalBuild(projectId, docTypeId) {
        const key = `${projectId}:${docTypeId || 'default'}`;
        return this.getAllLocalBuilds()[key] || null;
    },
    
    clearLocalBuild(projectId, docTypeId) {
        const key = `${projectId}:${docTypeId || 'default'}`;
        const builds = this.getAllLocalBuilds();
        delete builds[key];
        localStorage.setItem(this.storageKey, JSON.stringify(builds));
    },
    
    getAllLocalBuilds() {
        try { return JSON.parse(localStorage.getItem(this.storageKey) || '{}'); }
        catch { return {}; }
    },

    
    startPolling(threadId, callbacks) {
        if (this.activePolls.has(threadId)) return;
        
        const poll = async () => {
            try {
                const response = await fetch(`/api/commands/threads/${threadId}`);
                if (!response.ok) return;
                
                const thread = await response.json();
                
                if (thread.status === 'complete' || thread.status === 'failed' || thread.status === 'canceled') {
                    this.stopPolling(threadId);
                    if (callbacks.projectId) this.clearLocalBuild(callbacks.projectId, callbacks.docTypeId);
                    if (callbacks.onComplete) callbacks.onComplete(thread);
                    return;
                }
                
                if (callbacks.onProgress) callbacks.onProgress(thread);
            } catch (error) {
                console.error('ThreadMonitor poll error:', error);
                if (callbacks.onError) callbacks.onError(error);
            }
        };
        
        poll();
        const handle = setInterval(poll, this.pollInterval);
        this.activePolls.set(threadId, handle);
    },
    
    stopPolling(threadId) {
        const handle = this.activePolls.get(threadId);
        if (handle) {
            clearInterval(handle);
            this.activePolls.delete(threadId);
        }
    },
    
    stopAll() {
        for (const [, handle] of this.activePolls) clearInterval(handle);
        this.activePolls.clear();
    },

    
    showDefaultStatus(selector, thread) {
        const container = document.querySelector(selector);
        if (!container) return;
        
        const kindLabel = this.getKindLabel(thread.kind);
        const targetLabel = this.getTargetLabel(thread.target_ref);
        
        container.innerHTML = `
            <div class="bg-violet-50 dark:bg-violet-900/20 border border-violet-200 dark:border-violet-800 rounded-lg p-4">
                <div class="flex items-center gap-3">
                    <svg class="animate-spin h-5 w-5 text-violet-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <div>
                        <p class="font-medium text-violet-900 dark:text-violet-100">${kindLabel}</p>
                        <p class="text-sm text-violet-600 dark:text-violet-400">${targetLabel}</p>
                    </div>
                </div>
            </div>
        `;
        container.classList.remove('hidden');
    },
    
    updateDefaultStatus(selector, thread) {},
    
    handleDefaultComplete(selector, thread) {
        const container = document.querySelector(selector);
        if (container) {
            const isSuccess = thread.status === 'complete';
            const colorClass = isSuccess ? 'green' : 'red';
            const icon = isSuccess ? 'check-circle' : 'x-circle';
            const msg = isSuccess ? 'Generation complete!' : `Generation ${thread.status}`;
            
            container.innerHTML = `
                <div class="bg-${colorClass}-50 dark:bg-${colorClass}-900/20 border border-${colorClass}-200 dark:border-${colorClass}-800 rounded-lg p-4">
                    <div class="flex items-center gap-3">
                        <i data-lucide="${icon}" class="w-5 h-5 text-${colorClass}-600"></i>
                        <p class="font-medium text-${colorClass}-900 dark:text-${colorClass}-100">${msg}</p>
                    </div>
                </div>
            `;
            if (typeof lucide !== 'undefined') lucide.createIcons();
        }
        
        setTimeout(() => {
            htmx.ajax('GET', window.location.pathname, {target: '#main-content', swap: 'innerHTML'});
            htmx.ajax('GET', '/projects/tree', {target: '#project-tree-root', swap: 'innerHTML'});
        }, 1000);
    },
    
    getKindLabel(kind) {
        const labels = {
            'story_generate_epic': 'Generating Stories',
            'story_generate_all': 'Generating All Stories',
            'document_build': 'Generating Document',
        };
        return labels[kind] || 'Generating...';
    },
    
    getTargetLabel(targetRef) {
        if (!targetRef) return '';
        if (targetRef.epic_id) return `Epic: ${targetRef.epic_id}`;
        if (targetRef.doc_type) return `Document: ${targetRef.doc_type}`;
        return '';
    },
};

window.addEventListener('beforeunload', () => ThreadMonitor.stopAll());
window.ThreadMonitor = ThreadMonitor;
