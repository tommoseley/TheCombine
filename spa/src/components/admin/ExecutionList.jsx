import { useState, useEffect } from 'react';
import { api } from '../../api/client';

/**
 * Execution list - unified view of workflow and document workflow executions.
 * Consumes GET /api/v1/executions and GET /api/v1/document-workflows/executions.
 */
export default function ExecutionList({ onSelectExecution }) {
    const [executions, setExecutions] = useState([]);
    const [docExecutions, setDocExecutions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [statusFilter, setStatusFilter] = useState('all');
    const [sourceFilter, setSourceFilter] = useState('all');

    useEffect(() => {
        loadExecutions();
    }, []);

    async function loadExecutions() {
        setLoading(true);
        setError(null);
        try {
            const [execRes, docRes] = await Promise.allSettled([
                api.getExecutions(),
                api.getDocumentWorkflowExecutions(),
            ]);

            if (execRes.status === 'fulfilled') {
                setExecutions(execRes.value.executions || []);
            }
            if (docRes.status === 'fulfilled') {
                setDocExecutions(docRes.value || []);
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    // Merge and normalize both execution types
    const allExecutions = [
        ...executions.map(e => ({
            id: e.execution_id,
            type: 'workflow',
            workflowId: e.workflow_id,
            projectId: e.project_id,
            status: e.status,
            startedAt: e.started_at,
            label: e.workflow_id,
        })),
        ...docExecutions.map(e => ({
            id: e.execution_id,
            type: 'document',
            workflowId: e.workflow_id,
            projectId: e.project_id,
            documentType: e.document_type,
            status: e.status,
            startedAt: e.created_at || e.updated_at,
            label: e.document_type || e.workflow_id,
        })),
    ].sort((a, b) => {
        if (!a.startedAt) return 1;
        if (!b.startedAt) return -1;
        return new Date(b.startedAt) - new Date(a.startedAt);
    });

    // Apply filters
    const filtered = allExecutions.filter(e => {
        if (statusFilter !== 'all' && e.status?.toLowerCase() !== statusFilter) return false;
        if (sourceFilter !== 'all' && e.type !== sourceFilter) return false;
        return true;
    });

    const statuses = [...new Set(allExecutions.map(e => e.status?.toLowerCase()).filter(Boolean))];

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full">
                <p style={{ color: 'var(--text-muted)' }}>Loading executions...</p>
            </div>
        );
    }

    return (
        <div className="h-full flex flex-col">
            {/* Filters */}
            <div className="flex items-center gap-4 p-4 border-b flex-shrink-0"
                 style={{ borderColor: 'var(--border-panel)' }}>
                <div className="flex items-center gap-2">
                    <label className="text-xs" style={{ color: 'var(--text-muted)' }}>Status:</label>
                    <select
                        value={statusFilter}
                        onChange={e => setStatusFilter(e.target.value)}
                        className="text-xs px-2 py-1 rounded"
                        style={{
                            background: 'var(--bg-panel)',
                            color: 'var(--text-primary)',
                            border: '1px solid var(--border-panel)'
                        }}
                    >
                        <option value="all">All</option>
                        {statuses.map(s => (
                            <option key={s} value={s}>{s}</option>
                        ))}
                    </select>
                </div>
                <div className="flex items-center gap-2">
                    <label className="text-xs" style={{ color: 'var(--text-muted)' }}>Source:</label>
                    <select
                        value={sourceFilter}
                        onChange={e => setSourceFilter(e.target.value)}
                        className="text-xs px-2 py-1 rounded"
                        style={{
                            background: 'var(--bg-panel)',
                            color: 'var(--text-primary)',
                            border: '1px solid var(--border-panel)'
                        }}
                    >
                        <option value="all">All</option>
                        <option value="workflow">Workflows</option>
                        <option value="document">Documents</option>
                    </select>
                </div>
                <button
                    onClick={loadExecutions}
                    className="text-xs px-3 py-1 rounded hover:opacity-80 transition-opacity ml-auto"
                    style={{ color: 'var(--text-muted)', border: '1px solid var(--border-panel)' }}
                >
                    Refresh
                </button>
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                    {filtered.length} execution{filtered.length !== 1 ? 's' : ''}
                </span>
            </div>

            {error && (
                <div className="p-3 m-4 rounded text-sm" style={{ background: 'var(--bg-error, #fecaca)', color: '#991b1b' }}>
                    {error}
                </div>
            )}

            {/* Execution table */}
            <div className="flex-1 overflow-auto">
                <table className="w-full text-sm" style={{ color: 'var(--text-primary)' }}>
                    <thead>
                        <tr className="border-b" style={{ borderColor: 'var(--border-panel)' }}>
                            <th className="text-left p-3 font-medium text-xs" style={{ color: 'var(--text-muted)' }}>ID</th>
                            <th className="text-left p-3 font-medium text-xs" style={{ color: 'var(--text-muted)' }}>Type</th>
                            <th className="text-left p-3 font-medium text-xs" style={{ color: 'var(--text-muted)' }}>Workflow / Document</th>
                            <th className="text-left p-3 font-medium text-xs" style={{ color: 'var(--text-muted)' }}>Status</th>
                            <th className="text-left p-3 font-medium text-xs" style={{ color: 'var(--text-muted)' }}>Started</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filtered.map(exec => (
                            <tr
                                key={exec.id}
                                onClick={() => onSelectExecution(exec.id)}
                                className="border-b cursor-pointer hover:bg-white/5 transition-colors"
                                style={{ borderColor: 'var(--border-panel)' }}
                            >
                                <td className="p-3 font-mono text-xs">
                                    {exec.id?.substring(0, 8)}...
                                </td>
                                <td className="p-3">
                                    <span className="text-xs px-1.5 py-0.5 rounded"
                                          style={{
                                              background: exec.type === 'workflow'
                                                  ? 'var(--accent-primary, #3b82f6)' : 'var(--accent-secondary, #8b5cf6)',
                                              color: 'white',
                                              opacity: 0.8
                                          }}>
                                        {exec.type}
                                    </span>
                                </td>
                                <td className="p-3 text-xs">{exec.label}</td>
                                <td className="p-3">
                                    <StatusBadge status={exec.status} />
                                </td>
                                <td className="p-3 text-xs" style={{ color: 'var(--text-muted)' }}>
                                    {exec.startedAt ? formatDate(exec.startedAt) : '-'}
                                </td>
                            </tr>
                        ))}
                        {filtered.length === 0 && (
                            <tr>
                                <td colSpan={5} className="p-8 text-center" style={{ color: 'var(--text-muted)' }}>
                                    No executions found.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

function StatusBadge({ status }) {
    const s = (status || '').toLowerCase();
    let bg = 'var(--text-muted)';
    if (s.includes('complete') || s === 'done') bg = 'var(--state-complete, #10b981)';
    else if (s.includes('running') || s.includes('active') || s.includes('progress')) bg = 'var(--state-active, #f59e0b)';
    else if (s.includes('fail') || s.includes('error')) bg = 'var(--state-error, #ef4444)';
    else if (s.includes('wait') || s.includes('pending')) bg = 'var(--state-pending, #6b7280)';
    else if (s.includes('cancel')) bg = 'var(--text-muted)';

    return (
        <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: bg, color: 'white' }}>
            {status || 'unknown'}
        </span>
    );
}

function formatDate(isoString) {
    try {
        const d = new Date(isoString);
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
            + ' ' + d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    } catch {
        return isoString;
    }
}
