import { useState, useEffect, useMemo } from 'react';
import { api } from '../../api/client';

/**
 * Execution list - unified view of workflow and document workflow executions.
 * Consumes GET /api/v1/executions, GET /api/v1/document-workflows/executions,
 * and GET /api/v1/projects (for UUID-to-project-code resolution).
 */
export default function ExecutionList({ onSelectExecution }) {
    const [executions, setExecutions] = useState([]);
    const [docExecutions, setDocExecutions] = useState([]);
    const [projectMap, setProjectMap] = useState({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [statusFilter, setStatusFilter] = useState('all');
    const [sourceFilter, setSourceFilter] = useState('all');
    const [docTypeFilter, setDocTypeFilter] = useState('all');
    const [searchQuery, setSearchQuery] = useState('');
    const [sortKey, setSortKey] = useState('startedAt');
    const [sortDir, setSortDir] = useState('desc');

    useEffect(() => {
        loadExecutions();
    }, []);

    async function loadExecutions() {
        setLoading(true);
        setError(null);
        try {
            const [execRes, docRes, projRes] = await Promise.allSettled([
                api.getExecutions(),
                api.getDocumentWorkflowExecutions(),
                api.getProjects(),
            ]);

            if (execRes.status === 'fulfilled') {
                setExecutions(execRes.value.executions || []);
            }
            if (docRes.status === 'fulfilled') {
                setDocExecutions(docRes.value || []);
            }
            // Build UUID -> project_id code lookup
            // API returns { projects: [{ id: "uuid", project_id: "LIR-001", ... }] }
            if (projRes.status === 'fulfilled') {
                const projects = projRes.value?.projects || projRes.value || [];
                const map = {};
                for (const p of Array.isArray(projects) ? projects : []) {
                    const code = p.project_id || p.projectId;
                    if (p.id && code) {
                        map[p.id] = code;
                    }
                }
                setProjectMap(map);
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    // Merge and normalize both execution types
    const allExecutions = useMemo(() => [
        ...executions.map(e => ({
            id: e.execution_id,
            type: 'workflow',
            workflowId: e.workflow_id,
            projectId: e.project_id,
            projectCode: projectMap[e.project_id] || '--',
            documentType: e.document_type || e.workflow_id || '--',
            status: e.status,
            startedAt: e.started_at,
            label: e.workflow_id,
        })),
        ...docExecutions.map(e => ({
            id: e.execution_id,
            type: 'document',
            workflowId: e.workflow_id,
            projectId: e.project_id,
            projectCode: projectMap[e.project_id] || '--',
            documentType: e.document_type || e.workflow_id || '--',
            status: e.status,
            startedAt: e.created_at || e.updated_at,
            label: e.document_type || e.workflow_id,
        })),
    ], [executions, docExecutions, projectMap]);

    // Distinct document types for filter dropdown
    const documentTypes = useMemo(() =>
        [...new Set(allExecutions.map(e => e.documentType).filter(Boolean).filter(v => v !== '--'))].sort(),
        [allExecutions]
    );

    const statuses = useMemo(() =>
        [...new Set(allExecutions.map(e => e.status?.toLowerCase()).filter(Boolean))],
        [allExecutions]
    );

    // Apply filters + search
    const filtered = useMemo(() => {
        const query = searchQuery.toLowerCase().trim();
        return allExecutions.filter(e => {
            if (statusFilter !== 'all' && e.status?.toLowerCase() !== statusFilter) return false;
            if (sourceFilter !== 'all' && e.type !== sourceFilter) return false;
            if (docTypeFilter !== 'all' && e.documentType !== docTypeFilter) return false;
            if (query) {
                const matchesId = e.id?.toLowerCase().includes(query);
                const matchesProject = e.projectCode?.toLowerCase().includes(query);
                if (!matchesId && !matchesProject) return false;
            }
            return true;
        });
    }, [allExecutions, statusFilter, sourceFilter, docTypeFilter, searchQuery]);

    // Apply sorting
    const sorted = useMemo(() => {
        const copy = [...filtered];
        copy.sort((a, b) => {
            let aVal = a[sortKey];
            let bVal = b[sortKey];
            // Handle nulls
            if (aVal == null && bVal == null) return 0;
            if (aVal == null) return 1;
            if (bVal == null) return -1;
            // Date comparison
            if (sortKey === 'startedAt') {
                aVal = new Date(aVal).getTime();
                bVal = new Date(bVal).getTime();
            }
            // String comparison
            if (typeof aVal === 'string' && typeof bVal === 'string') {
                const cmp = aVal.localeCompare(bVal);
                return sortDir === 'asc' ? cmp : -cmp;
            }
            // Numeric comparison
            const cmp = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
            return sortDir === 'asc' ? cmp : -cmp;
        });
        return copy;
    }, [filtered, sortKey, sortDir]);

    function handleSort(key) {
        if (sortKey === key) {
            setSortDir(prev => prev === 'asc' ? 'desc' : 'asc');
        } else {
            setSortKey(key);
            setSortDir('asc');
        }
    }

    function SortIndicator({ columnKey }) {
        if (sortKey !== columnKey) return null;
        return (
            <span className="ml-1">
                {sortDir === 'asc' ? '\u25B2' : '\u25BC'}
            </span>
        );
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full">
                <p style={{ color: 'var(--text-muted)' }}>Loading executions...</p>
            </div>
        );
    }

    const columns = [
        { key: 'id', label: 'Execution ID', minWidth: '200px' },
        { key: 'projectCode', label: 'Project' },
        { key: 'type', label: 'Source' },
        { key: 'documentType', label: 'Document Type' },
        { key: 'status', label: 'Status' },
        { key: 'startedAt', label: 'Started' },
    ];

    return (
        <div className="h-full flex flex-col">
            {/* Filters + Search */}
            <div className="flex items-center gap-4 p-4 border-b flex-shrink-0 flex-wrap"
                 style={{ borderColor: 'var(--border-panel)' }}>
                {/* Search */}
                <div className="flex items-center gap-2">
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={e => setSearchQuery(e.target.value)}
                        placeholder="Search by ID or project..."
                        className="text-xs px-2 py-1 rounded"
                        style={{
                            background: 'var(--bg-panel)',
                            color: 'var(--text-primary)',
                            border: '1px solid var(--border-panel)',
                            width: '200px',
                        }}
                    />
                </div>
                {/* Status filter */}
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
                {/* Source filter */}
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
                {/* Document type filter */}
                <div className="flex items-center gap-2">
                    <label className="text-xs" style={{ color: 'var(--text-muted)' }}>Type:</label>
                    <select
                        value={docTypeFilter}
                        onChange={e => setDocTypeFilter(e.target.value)}
                        className="text-xs px-2 py-1 rounded"
                        style={{
                            background: 'var(--bg-panel)',
                            color: 'var(--text-primary)',
                            border: '1px solid var(--border-panel)'
                        }}
                    >
                        <option value="all">All</option>
                        {documentTypes.map(dt => (
                            <option key={dt} value={dt}>{dt}</option>
                        ))}
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
                    {sorted.length} execution{sorted.length !== 1 ? 's' : ''}
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
                            {columns.map(col => (
                                <th
                                    key={col.key}
                                    onClick={() => handleSort(col.key)}
                                    className="text-left p-3 font-medium text-xs cursor-pointer hover:opacity-80 select-none"
                                    style={{
                                        color: 'var(--text-muted)',
                                        minWidth: col.minWidth || undefined,
                                    }}
                                >
                                    {col.label}
                                    <SortIndicator columnKey={col.key} />
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {sorted.map(exec => (
                            <tr
                                key={exec.id}
                                onClick={() => onSelectExecution(exec.id)}
                                className="border-b cursor-pointer hover:bg-white/5 transition-colors"
                                style={{ borderColor: 'var(--border-panel)' }}
                            >
                                <td className="p-3 font-mono text-xs" style={{ minWidth: '200px' }}>
                                    {exec.id}
                                </td>
                                <td className="p-3 font-mono text-xs">
                                    {exec.projectCode}
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
                                <td className="p-3 text-xs">{exec.documentType}</td>
                                <td className="p-3">
                                    <StatusBadge status={exec.status} />
                                </td>
                                <td className="p-3 text-xs" style={{ color: 'var(--text-muted)' }}>
                                    {exec.startedAt ? formatDate(exec.startedAt) : '-'}
                                </td>
                            </tr>
                        ))}
                        {sorted.length === 0 && (
                            <tr>
                                <td colSpan={columns.length} className="p-8 text-center" style={{ color: 'var(--text-muted)' }}>
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
