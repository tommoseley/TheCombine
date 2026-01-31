/**
 * API client for The Combine backend
 * Wired to actual FastAPI endpoints
 */

const API_BASE = '/api/v1';

class ApiError extends Error {
    constructor(message, status, data) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.data = data;
    }
}

async function request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const config = {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
        ...options,
    };

    const response = await fetch(url, config);

    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new ApiError(
            data.detail || `Request failed: ${response.status}`,
            response.status,
            data
        );
    }

    // Handle 204 No Content
    if (response.status === 204) {
        return null;
    }

    return response.json();
}

export const api = {
    // Projects
    getProjects: (params = {}) => {
        const query = new URLSearchParams();
        if (params.search) query.set('search', params.search);
        if (params.includeArchived) query.set('include_archived', 'true');
        const qs = query.toString();
        return request(`/projects${qs ? '?' + qs : ''}`);
    },

    getProject: (projectId) => request(`/projects/${projectId}`),

    getProjectTree: (projectId) => request(`/projects/${projectId}/tree`),

    createProject: (data) => request('/projects', {
        method: 'POST',
        body: JSON.stringify(data),
    }),

    updateProject: (projectId, data) => request(`/projects/${projectId}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
    }),

    archiveProject: (projectId) => request(`/projects/${projectId}/archive`, {
        method: 'POST',
    }),

    unarchiveProject: (projectId) => request(`/projects/${projectId}/unarchive`, {
        method: 'POST',
    }),

    deleteProject: (projectId) => request(`/projects/${projectId}`, {
        method: 'DELETE',
    }),

    // Production line
    getProductionStatus: (projectId) =>
        request(`/production/status?project_id=${projectId}`),

    startProduction: (projectId, documentType = null) => {
        const query = new URLSearchParams({ project_id: projectId });
        if (documentType) query.set('document_type', documentType);
        return request(`/production/start?${query}`, { method: 'POST' });
    },

    // Interrupts (operator questions)
    getProjectInterrupts: (projectId) =>
        request(`/projects/${projectId}/interrupts`),

    resolveInterrupt: (interruptId, data) =>
        request(`/interrupts/${interruptId}/resolve`, {
            method: 'POST',
            body: JSON.stringify(data),
        }),

    // Document workflows
    startWorkflow: (projectId, documentType, initialContext = null) =>
        request('/document-workflows/start', {
            method: 'POST',
            body: JSON.stringify({
                project_id: projectId,
                document_type: documentType,
                initial_context: initialContext,
            }),
        }),

    submitWorkflowInput: (executionId, userInput, selectedOptionId = null) =>
        request(`/document-workflows/executions/${executionId}/input`, {
            method: 'POST',
            body: JSON.stringify({
                user_input: userInput,
                selected_option_id: selectedOptionId,
            }),
        }),

    getExecutionStatus: (executionId) =>
        request(`/document-workflows/executions/${executionId}`),

    getPgcAnswers: (executionId) =>
        request(`/document-workflows/executions/${executionId}/pgc-answers`),

    // Documents
    getDocument: (projectId, docTypeId) =>
        request(`/projects/${projectId}/documents/${docTypeId}`),

    // RenderModel (data-driven document display)
    getDocumentRenderModel: (projectId, docTypeId) =>
        request(`/projects/${projectId}/documents/${docTypeId}/render-model`),

    // Concierge Intake
    startIntake: () =>
        request('/intake/start', { method: 'POST' }),

    getIntakeState: (executionId) =>
        request(`/intake/${executionId}`),

    submitIntakeMessage: (executionId, content) =>
        request(`/intake/${executionId}/message`, {
            method: 'POST',
            body: JSON.stringify({ content }),
        }),

    updateIntakeField: (executionId, fieldKey, value) =>
        request(`/intake/${executionId}/field/${fieldKey}`, {
            method: 'PATCH',
            body: JSON.stringify({ value }),
        }),

    initializeIntake: (executionId) =>
        request(`/intake/${executionId}/initialize`, { method: 'POST' }),
};

/**
 * Create SSE connection for production events
 */
export function createProductionSSE(projectId) {
    const url = `${API_BASE}/production/events?project_id=${projectId}`;
    return new EventSource(url);
}

/**
 * Create SSE connection for intake generation events
 */
export function createIntakeSSE(executionId) {
    const url = `${API_BASE}/intake/${executionId}/events`;
    return new EventSource(url);
}

/**
 * Create SSE connection for execution progress
 */
export function createExecutionSSE(executionId) {
    const url = `/executions/${executionId}/stream`;
    return new EventSource(url);
}

export { ApiError };
