/**
 * Admin API client for The Combine Admin Workbench
 * Per ADR-044 WS-044-03: Workspace-scoped configuration editing
 */

const ADMIN_BASE = '/api/v1/admin';

class AdminApiError extends Error {
    constructor(message, status, data) {
        super(message);
        this.name = 'AdminApiError';
        this.status = status;
        this.data = data;
        this.errorCode = data?.error_code;
    }
}

/**
 * Get CSRF token from cookies
 */
function getCsrfToken() {
    const match = document.cookie.match(/(?:^|;\s*)csrf=([^;]*)/);
    return match ? decodeURIComponent(match[1]) : null;
}

async function request(endpoint, options = {}) {
    const url = `${ADMIN_BASE}${endpoint}`;
    const config = {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
        credentials: 'same-origin',
        ...options,
    };

    // Add CSRF token for mutations
    if (options.method && options.method !== 'GET') {
        const csrfToken = getCsrfToken();
        if (csrfToken) {
            config.headers['X-CSRF-Token'] = csrfToken;
        }
    }

    const response = await fetch(url, config);

    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        const message = data.detail?.message || data.detail || `Request failed: ${response.status}`;
        throw new AdminApiError(message, response.status, data.detail || data);
    }

    // Handle 204 No Content
    if (response.status === 204) {
        return null;
    }

    return response.json();
}

export const adminApi = {
    // =========================================================================
    // Workspace Lifecycle
    // =========================================================================

    /**
     * Get current workspace for authenticated user
     * @returns {Promise<Object|null>} Workspace state or null if none exists
     */
    getCurrentWorkspace: async () => {
        try {
            return await request('/workspaces/current');
        } catch (err) {
            if (err.status === 404 && err.errorCode === 'NO_WORKSPACE') {
                return null;
            }
            throw err;
        }
    },

    /**
     * Create a new workspace
     * @returns {Promise<Object>} Created workspace info
     */
    createWorkspace: () => request('/workspaces', { method: 'POST' }),

    /**
     * Get workspace state
     * @param {string} workspaceId
     * @returns {Promise<Object>} Workspace state
     */
    getWorkspaceState: (workspaceId) => request(`/workspaces/${workspaceId}/state`),

    /**
     * Close workspace
     * @param {string} workspaceId
     * @param {boolean} force - Close even if dirty
     */
    closeWorkspace: (workspaceId, force = false) =>
        request(`/workspaces/${workspaceId}?force=${force}`, { method: 'DELETE' }),

    // =========================================================================
    // Artifact Operations
    // =========================================================================

    /**
     * Get artifact content
     * @param {string} workspaceId
     * @param {string} artifactId - Format: scope:name:version:kind
     * @returns {Promise<Object>} Artifact content
     */
    getArtifact: (workspaceId, artifactId) =>
        request(`/workspaces/${workspaceId}/artifacts/${encodeURIComponent(artifactId)}`),

    /**
     * Write artifact content (auto-save)
     * @param {string} workspaceId
     * @param {string} artifactId
     * @param {string} content
     * @returns {Promise<Object>} Write result with tier1 validation
     */
    writeArtifact: (workspaceId, artifactId, content) =>
        request(`/workspaces/${workspaceId}/artifacts/${encodeURIComponent(artifactId)}`, {
            method: 'PUT',
            body: JSON.stringify({ content }),
        }),

    /**
     * Get artifact preview (resolved prompt)
     * @param {string} workspaceId
     * @param {string} artifactId
     * @param {string} mode - Preview mode (default: 'execution')
     * @returns {Promise<Object>} Preview with resolved prompt and provenance
     */
    getPreview: (workspaceId, artifactId, mode = 'execution') =>
        request(`/workspaces/${workspaceId}/preview/${encodeURIComponent(artifactId)}?mode=${mode}`),

    /**
     * Get diff for workspace changes
     * @param {string} workspaceId
     * @param {string} artifactId - Optional specific artifact
     * @returns {Promise<Object>} Diff with old/new content
     */
    getDiff: (workspaceId, artifactId = null) => {
        const qs = artifactId ? `?artifact_id=${encodeURIComponent(artifactId)}` : '';
        return request(`/workspaces/${workspaceId}/diff${qs}`);
    },

    // =========================================================================
    // Commit Operations
    // =========================================================================

    /**
     * Commit all changes in workspace
     * @param {string} workspaceId
     * @param {string} message - Commit message
     * @returns {Promise<Object>} Commit result
     */
    commit: (workspaceId, message) =>
        request(`/workspaces/${workspaceId}/commit`, {
            method: 'POST',
            body: JSON.stringify({ message }),
        }),

    /**
     * Discard all uncommitted changes
     * @param {string} workspaceId
     */
    discard: (workspaceId) =>
        request(`/workspaces/${workspaceId}/discard`, { method: 'POST' }),

    // =========================================================================
    // Workbench API (Read-only)
    // =========================================================================

    /**
     * List all document types
     * @returns {Promise<Object>} Document types list
     */
    getDocumentTypes: () => request('/workbench/document-types'),

    /**
     * Get document type details
     * @param {string} docTypeId
     * @param {string} version - Optional specific version
     * @returns {Promise<Object>} Document type details
     */
    getDocumentType: (docTypeId, version = null) => {
        const qs = version ? `?version=${version}` : '';
        return request(`/workbench/document-types/${docTypeId}${qs}`);
    },

    /**
     * Get document type versions
     * @param {string} docTypeId
     * @returns {Promise<Object>} Versions list with active version
     */
    getDocumentTypeVersions: (docTypeId) =>
        request(`/workbench/document-types/${docTypeId}/versions`),

    /**
     * List all prompt fragments
     * @returns {Promise<Object>} Prompt fragments list
     */
    getPromptFragments: () => request('/workbench/prompt-fragments'),

    /**
     * List all roles
     * @returns {Promise<Object>} Roles list
     */
    getRoles: () => request('/workbench/roles'),

    /**
     * List all templates
     * @returns {Promise<Object>} Templates list
     */
    getTemplates: () => request('/workbench/templates'),

    /**
     * List all standalone schemas
     * @returns {Promise<Object>} Schemas list
     */
    getSchemas: () => request('/workbench/schemas'),

    /**
     * Get standalone schema details
     * @param {string} schemaId
     * @param {string} version
     * @returns {Promise<Object>} Schema details with content
     */
    getSchema: (schemaId, version = null) => {
        const qs = version ? `?version=${version}` : '';
        return request(`/workbench/schemas/${schemaId}${qs}`);
    },

    /**
     * Get role details
     * @param {string} roleId
     * @param {string} version
     * @returns {Promise<Object>} Role details with content
     */
    getRole: (roleId, version = null) => {
        const qs = version ? `?version=${version}` : '';
        return request(`/workbench/roles/${roleId}${qs}`);
    },

    /**
     * Get template details
     * @param {string} templateId
     * @param {string} version
     * @returns {Promise<Object>} Template details with content
     */
    getTemplate: (templateId, version = null) => {
        const qs = version ? `?version=${version}` : '';
        return request(`/workbench/templates/${templateId}${qs}`);
    },

    /**
     * List all workflow plans (graph-based, document production)
     * @returns {Promise<Object>} Workflow plans list
     */
    getWorkflows: () => request('/workbench/workflows'),

    /**
     * List orchestration workflows (step-based, project orchestration)
     * @returns {Promise<Object>} Orchestration workflow list
     */
    getOrchestrationWorkflows: () => request('/workbench/orchestration-workflows'),

    /**
     * Get workflow plan details
     * @param {string} workflowId
     * @param {string} version - Optional specific version
     * @returns {Promise<Object>} Workflow plan with full definition
     */
    getWorkflow: (workflowId, version = null) => {
        const qs = version ? `?version=${version}` : '';
        return request(`/workbench/workflows/${workflowId}${qs}`);
    },

    // =========================================================================
    // Orchestration Workflow Lifecycle
    // =========================================================================

    /**
     * Create a new orchestration workflow
     * @param {string} workspaceId
     * @param {Object} data - { workflow_id, name?, version? }
     * @returns {Promise<Object>} Created workflow info
     */
    createOrchestrationWorkflow: (workspaceId, data) =>
        request(`/workspaces/${workspaceId}/orchestration-workflows`, {
            method: 'POST',
            body: JSON.stringify(data),
        }),

    /**
     * Delete an orchestration workflow
     * @param {string} workspaceId
     * @param {string} workflowId
     */
    deleteOrchestrationWorkflow: (workspaceId, workflowId) =>
        request(`/workspaces/${workspaceId}/orchestration-workflows/${workflowId}`, {
            method: 'DELETE',
        }),

    // =========================================================================
    // Document Type Lifecycle
    // =========================================================================

    /**
     * Create a new document type (DCW)
     * @param {string} workspaceId
     * @param {Object} data - { doc_type_id, display_name?, version?, scope?, role_ref? }
     * @returns {Promise<Object>} Created document type info
     */
    createDocumentType: (workspaceId, data) =>
        request(`/workspaces/${workspaceId}/document-types`, {
            method: 'POST',
            body: JSON.stringify(data),
        }),

    /**
     * Delete a document type
     * @param {string} workspaceId
     * @param {string} docTypeId
     */
    deleteDocumentType: (workspaceId, docTypeId) =>
        request(`/workspaces/${workspaceId}/document-types/${docTypeId}`, {
            method: 'DELETE',
        }),

    // =========================================================================
    // DCW Workflow Lifecycle
    // =========================================================================

    /**
     * Create a DCW workflow for an existing document type
     * @param {string} workspaceId
     * @param {Object} data - { doc_type_id, version? }
     * @returns {Promise<Object>} Created workflow info
     */
    createDcwWorkflow: (workspaceId, data) =>
        request(`/workspaces/${workspaceId}/dcw-workflows`, {
            method: 'POST',
            body: JSON.stringify(data),
        }),

    // =========================================================================
    // Role Prompt Lifecycle
    // =========================================================================

    /**
     * Create a new role prompt
     * @param {string} workspaceId
     * @param {Object} data - { role_id, name?, version? }
     * @returns {Promise<Object>} Created role prompt info
     */
    createRolePrompt: (workspaceId, data) =>
        request(`/workspaces/${workspaceId}/role-prompts`, {
            method: 'POST',
            body: JSON.stringify(data),
        }),

    // =========================================================================
    // Template Lifecycle
    // =========================================================================

    /**
     * Create a new template
     * @param {string} workspaceId
     * @param {Object} data - { template_id, name?, purpose?, version? }
     * @returns {Promise<Object>} Created template info
     */
    createTemplate: (workspaceId, data) =>
        request(`/workspaces/${workspaceId}/templates`, {
            method: 'POST',
            body: JSON.stringify(data),
        }),

    // =========================================================================
    // Standalone Schema Lifecycle
    // =========================================================================

    /**
     * Create a new standalone schema
     * @param {string} workspaceId
     * @param {Object} data - { schema_id, title?, version? }
     * @returns {Promise<Object>} Created schema info
     */
    createStandaloneSchema: (workspaceId, data) =>
        request(`/workspaces/${workspaceId}/schemas`, {
            method: 'POST',
            body: JSON.stringify(data),
        }),

    /**
     * Get active releases
     * @returns {Promise<Object>} Active release pointers
     */
    getActiveReleases: () => request('/workbench/active-releases'),

    /**
     * Invalidate config cache to pick up workflow/doc type changes without restart
     */
    invalidateCache: () => request('/workbench/invalidate-cache', { method: 'POST' }),

    // =========================================================================
    // Mechanical Operations (ADR-047)
    // =========================================================================

    /**
     * List all mechanical operation types from registry
     * @returns {Promise<Object>} Operation types list
     */
    getMechanicalOpTypes: () => request('/workbench/mechanical-ops/types'),

    /**
     * Get mechanical operation type details
     * @param {string} typeId
     * @returns {Promise<Object>} Type details with config schema
     */
    getMechanicalOpType: (typeId) => request(`/workbench/mechanical-ops/types/${typeId}`),

    /**
     * List all mechanical operation categories
     * @returns {Promise<Object>} Categories list
     */
    getMechanicalOpCategories: () => request('/workbench/mechanical-ops/categories'),

    /**
     * List all mechanical operation instances
     * @returns {Promise<Object>} Operations list
     */
    getMechanicalOps: () => request('/workbench/mechanical-ops'),

    /**
     * Get mechanical operation instance details
     * @param {string} opId
     * @param {string} version
     * @returns {Promise<Object>} Operation details with config
     */
    getMechanicalOp: (opId, version = null) => {
        const qs = version ? `?version=${version}` : '';
        return request(`/workbench/mechanical-ops/${opId}${qs}`);
    },
};

export { AdminApiError };
