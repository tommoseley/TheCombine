/**
 * Visual configuration for architecture workflow diagram nodes and edges.
 * Used by WorkflowBlockV2 and ArchWorkflowNode for document-embedded diagrams.
 */

export const ARCH_WORKFLOW_NODE_CONFIG = {
    action: {
        color: '#1d4ed8',          // Darker blue for text
        bgColor: '#eff6ff',        // Solid light blue background
        borderColor: '#3b82f6',
        label: 'Action',
    },
    gate: {
        color: '#b45309',          // Darker amber for text
        bgColor: '#fef3c7',        // Solid light amber background
        borderColor: '#f59e0b',
        label: 'Gate',
    },
    escalation: {
        color: '#b91c1c',          // Darker red for text
        bgColor: '#fee2e2',        // Solid light red background
        borderColor: '#ef4444',
        label: 'Escalation',
    },
    parallel_fork: {
        color: '#6d28d9',          // Darker purple for text
        bgColor: '#ede9fe',        // Solid light purple background
        borderColor: '#8b5cf6',
        label: 'Fork',
    },
    parallel_join: {
        color: '#6d28d9',
        bgColor: '#ede9fe',
        borderColor: '#8b5cf6',
        label: 'Join',
    },
    start: {
        color: '#047857',          // Darker green for text
        bgColor: '#d1fae5',        // Solid light green background
        borderColor: '#10b981',
        label: 'Start',
    },
    end: {
        color: '#374151',          // Darker gray for text
        bgColor: '#f3f4f6',        // Solid light gray background
        borderColor: '#6b7280',
        label: 'End',
    },
};

export const ARCH_WORKFLOW_EDGE_CONFIG = {
    normal: {
        stroke: '#64748b',
        strokeWidth: 2,
    },
    error: {
        stroke: '#ef4444',
        strokeWidth: 2,
        strokeDasharray: '6,3',
    },
    retry: {
        stroke: '#f97316',
        strokeWidth: 2,
        strokeDasharray: '6,3',
        animated: true,
    },
    parallel: {
        stroke: '#8b5cf6',
        strokeWidth: 2,
    },
};

export const ARCH_NODE_WIDTH = 160;
export const ARCH_NODE_HEIGHT = 80;