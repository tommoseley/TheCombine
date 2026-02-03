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
        request(`/workspaces/${workspaceId}/artifacts/${artifactId}`),

    /**
     * Write artifact content (auto-save)
     * @param {string} workspaceId
     * @param {string} artifactId
     * @param {string} content
     * @returns {Promise<Object>} Write result with tier1 validation
     */
    writeArtifact: (workspaceId, artifactId, content) =>
        request(`/workspaces/${workspaceId}/artifacts/${artifactId}`, {
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
        request(`/workspaces/${workspaceId}/preview/${artifactId}?mode=${mode}`),

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
     * List all roles
     * @returns {Promise<Object>} Roles list
     */
    getRoles: () => request('/workbench/roles'),

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
     * Get active releases
     * @returns {Promise<Object>} Active release pointers
     */
    getActiveReleases: () => request('/workbench/active-releases'),

    /**
     * Invalidate cache
     */
    invalidateCache: () => request('/workbench/cache/invalidate', { method: 'POST' }),
};

export { AdminApiError };
