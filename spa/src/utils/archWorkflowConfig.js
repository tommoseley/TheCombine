/**
 * Visual configuration for architecture workflow diagram nodes and edges.
 * Used by WorkflowBlockV2 and ArchWorkflowNode for document-embedded diagrams.
 */

export const ARCH_WORKFLOW_NODE_CONFIG = {
    action: {
        color: '#3b82f6',
        bgColor: 'rgba(59, 130, 246, 0.12)',
        borderColor: 'rgba(59, 130, 246, 0.4)',
        label: 'Action',
    },
    gate: {
        color: '#f59e0b',
        bgColor: 'rgba(245, 158, 11, 0.12)',
        borderColor: 'rgba(245, 158, 11, 0.4)',
        label: 'Gate',
    },
    escalation: {
        color: '#ef4444',
        bgColor: 'rgba(239, 68, 68, 0.12)',
        borderColor: 'rgba(239, 68, 68, 0.4)',
        label: 'Escalation',
    },
    parallel_fork: {
        color: '#8b5cf6',
        bgColor: 'rgba(139, 92, 246, 0.12)',
        borderColor: 'rgba(139, 92, 246, 0.4)',
        label: 'Fork',
    },
    parallel_join: {
        color: '#8b5cf6',
        bgColor: 'rgba(139, 92, 246, 0.12)',
        borderColor: 'rgba(139, 92, 246, 0.4)',
        label: 'Join',
    },
    start: {
        color: '#10b981',
        bgColor: 'rgba(16, 185, 129, 0.12)',
        borderColor: 'rgba(16, 185, 129, 0.4)',
        label: 'Start',
    },
    end: {
        color: '#6b7280',
        bgColor: 'rgba(107, 114, 128, 0.12)',
        borderColor: 'rgba(107, 114, 128, 0.4)',
        label: 'End',
    },
};

export const ARCH_WORKFLOW_EDGE_CONFIG = {
    normal: {
        stroke: '#94a3b8',
        strokeWidth: 1.5,
    },
    error: {
        stroke: '#ef4444',
        strokeWidth: 1.5,
        strokeDasharray: '6,3',
    },
    retry: {
        stroke: '#f97316',
        strokeWidth: 1.5,
        strokeDasharray: '6,3',
        animated: true,
    },
    parallel: {
        stroke: '#8b5cf6',
        strokeWidth: 1.5,
    },
};

export const ARCH_NODE_WIDTH = 160;
export const ARCH_NODE_HEIGHT = 80;
