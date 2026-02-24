import { useEffect } from 'react';

/**
 * WorkflowAuditDrawer - Modal drawer showing raw workflow definition JSON.
 *
 * Per WS-WORKFLOW-STUDIO-001 Phase 3
 * Per WS-INSTANCE-ID-001 Phase 4 - optional spawnedDocuments prop
 */
export default function WorkflowAuditDrawer({ workflow, onClose, spawnedDocuments }) {
    // Close on Escape
    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.key === 'Escape') onClose();
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [onClose]);

    // Support both DocDef mode (block.data) and raw content mode (rawItem)
    const rawData = workflow?.block?.data || workflow?.rawItem || {};

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-end"
            style={{ background: 'rgba(0,0,0,0.4)' }}
            onClick={(e) => e.target === e.currentTarget && onClose()}
        >
            <div
                className="h-full w-full max-w-2xl flex flex-col shadow-2xl"
                style={{ background: '#ffffff' }}
            >
                {/* Header */}
                <div
                    className="flex items-center justify-between px-4 py-3 border-b"
                    style={{ background: '#f8fafc', borderColor: '#e2e8f0' }}
                >
                    <div>
                        <h3 className="text-base font-semibold" style={{ color: '#1e293b' }}>
                            Workflow Audit
                        </h3>
                        <p className="text-sm" style={{ color: '#64748b' }}>
                            {workflow.name}
                        </p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1.5 rounded hover:bg-gray-200 transition-colors"
                    >
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M18 6L6 18M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Content */}
                <div
                    className="flex-1 overflow-auto p-4"
                    style={{ background: '#f8fafc' }}
                    onWheel={(e) => e.stopPropagation()}
                >
                    {/* Summary stats */}
                    <div className="mb-4 flex gap-4">
                        <StatBadge label="Nodes" value={rawData.nodes?.length || rawData.steps?.length || 0} />
                        <StatBadge label="Edges" value={rawData.edges?.length || 0} />
                        {rawData.trigger && <StatBadge label="Trigger" value={rawData.trigger} isText />}
                    </div>

                    {/* Nodes table */}
                    {(rawData.nodes || rawData.steps) && (
                        <div className="mb-4">
                            <h4 className="text-sm font-semibold mb-2" style={{ color: '#475569' }}>
                                {rawData.nodes ? 'Nodes' : 'Steps'}
                            </h4>
                            <div
                                className="rounded border overflow-hidden"
                                style={{ borderColor: '#e2e8f0' }}
                            >
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr style={{ background: '#f1f5f9' }}>
                                            <th className="px-3 py-2 text-left font-medium" style={{ color: '#64748b' }}>ID</th>
                                            <th className="px-3 py-2 text-left font-medium" style={{ color: '#64748b' }}>Type</th>
                                            <th className="px-3 py-2 text-left font-medium" style={{ color: '#64748b' }}>Station</th>
                                            <th className="px-3 py-2 text-left font-medium" style={{ color: '#64748b' }}>Label</th>
                                            <th className="px-3 py-2 text-left font-medium" style={{ color: '#64748b' }}>Actor</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {(rawData.nodes || rawData.steps).map((node, i) => (
                                            <tr key={node.node_id || i} style={{ borderTop: '1px solid #e2e8f0' }}>
                                                <td className="px-3 py-2 font-mono text-xs" style={{ color: '#6366f1' }}>
                                                    {node.node_id || `step_${i + 1}`}
                                                </td>
                                                <td className="px-3 py-2">
                                                    <TypeBadge type={node.type || 'action'} />
                                                </td>
                                                <td className="px-3 py-2">
                                                    {node.station ? (
                                                        <span
                                                            className="px-1.5 py-0.5 text-xs font-medium rounded"
                                                            style={{ background: '#f0fdf4', color: '#166534' }}
                                                        >
                                                            {node.station.label}
                                                        </span>
                                                    ) : '-'}
                                                </td>
                                                <td className="px-3 py-2" style={{ color: '#1e293b' }}>
                                                    {node.label || node.action || '-'}
                                                </td>
                                                <td className="px-3 py-2" style={{ color: '#64748b' }}>
                                                    {node.actor || '-'}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {/* Edges table */}
                    {rawData.edges && rawData.edges.length > 0 && (
                        <div className="mb-4">
                            <h4 className="text-sm font-semibold mb-2" style={{ color: '#475569' }}>Edges</h4>
                            <div
                                className="rounded border overflow-hidden"
                                style={{ borderColor: '#e2e8f0' }}
                            >
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr style={{ background: '#f1f5f9' }}>
                                            <th className="px-3 py-2 text-left font-medium" style={{ color: '#64748b' }}>From</th>
                                            <th className="px-3 py-2 text-left font-medium" style={{ color: '#64748b' }}>To</th>
                                            <th className="px-3 py-2 text-left font-medium" style={{ color: '#64748b' }}>Type</th>
                                            <th className="px-3 py-2 text-left font-medium" style={{ color: '#64748b' }}>Label</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {rawData.edges.map((edge, i) => (
                                            <tr key={edge.edge_id || i} style={{ borderTop: '1px solid #e2e8f0' }}>
                                                <td className="px-3 py-2 font-mono text-xs" style={{ color: '#6366f1' }}>
                                                    {edge.from_node_id}
                                                </td>
                                                <td className="px-3 py-2 font-mono text-xs" style={{ color: '#6366f1' }}>
                                                    {edge.to_node_id}
                                                </td>
                                                <td className="px-3 py-2">
                                                    <EdgeTypeBadge type={edge.type || 'normal'} />
                                                </td>
                                                <td className="px-3 py-2" style={{ color: '#64748b' }}>
                                                    {edge.label || '-'}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {/* Spawned Documents (WS-INSTANCE-ID-001) */}
                    {spawnedDocuments && spawnedDocuments.length > 0 && (
                        <div className="mb-4">
                            <h4 className="text-sm font-semibold mb-2" style={{ color: '#475569' }}>
                                Spawned Documents
                            </h4>
                            <div
                                className="rounded border overflow-hidden"
                                style={{ borderColor: '#e2e8f0' }}
                            >
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr style={{ background: '#f1f5f9' }}>
                                            <th className="px-3 py-2 text-left font-medium" style={{ color: '#64748b' }}>Idempotency Key</th>
                                            <th className="px-3 py-2 text-left font-medium" style={{ color: '#64748b' }}>Type</th>
                                            <th className="px-3 py-2 text-left font-medium" style={{ color: '#64748b' }}>Title</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {spawnedDocuments.map((doc, i) => (
                                            <tr key={doc.instance_id || i} style={{ borderTop: '1px solid #e2e8f0' }}>
                                                <td className="px-3 py-2 font-mono text-xs" style={{ color: '#6366f1' }}>
                                                    {doc.instance_id || '-'}
                                                </td>
                                                <td className="px-3 py-2">
                                                    <TypeBadge type={doc.doc_type_id || 'epic'} />
                                                </td>
                                                <td className="px-3 py-2" style={{ color: '#1e293b' }}>
                                                    {doc.title || doc.name || '-'}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {/* Raw JSON */}
                    <details className="rounded border" style={{ borderColor: '#e2e8f0' }}>
                        <summary
                            className="px-3 py-2 cursor-pointer text-sm font-medium"
                            style={{ background: '#f1f5f9', color: '#64748b' }}
                        >
                            Raw JSON
                        </summary>
                        <div className="p-3 overflow-auto" style={{ background: '#ffffff' }}>
                            <pre
                                className="text-xs font-mono whitespace-pre-wrap"
                                style={{ color: '#374151', lineHeight: 1.5 }}
                            >
                                {JSON.stringify(rawData, null, 2)}
                            </pre>
                        </div>
                    </details>
                </div>
            </div>
        </div>
    );
}

function StatBadge({ label, value, isText = false }) {
    return (
        <div
            className="px-3 py-1.5 rounded"
            style={{ background: '#e0e7ff', color: '#4338ca' }}
        >
            <span className="text-xs font-medium">{label}: </span>
            <span className={`text-sm font-semibold ${isText ? '' : 'tabular-nums'}`}>{value}</span>
        </div>
    );
}

function TypeBadge({ type }) {
    const colors = {
        start: { bg: '#dcfce7', color: '#166534' },
        end: { bg: '#fee2e2', color: '#991b1b' },
        action: { bg: '#dbeafe', color: '#1e40af' },
        gate: { bg: '#fef3c7', color: '#92400e' },
        decision: { bg: '#fef3c7', color: '#92400e' },
        error: { bg: '#fee2e2', color: '#991b1b' },
    };
    const c = colors[type] || colors.action;
    return (
        <span
            className="px-1.5 py-0.5 text-xs font-medium rounded"
            style={{ background: c.bg, color: c.color }}
        >
            {type}
        </span>
    );
}

function EdgeTypeBadge({ type }) {
    const colors = {
        normal: { bg: '#f1f5f9', color: '#64748b' },
        error: { bg: '#fee2e2', color: '#991b1b' },
        retry: { bg: '#fef3c7', color: '#92400e' },
        conditional: { bg: '#e0e7ff', color: '#4338ca' },
    };
    const c = colors[type] || colors.normal;
    return (
        <span
            className="px-1.5 py-0.5 text-xs font-medium rounded"
            style={{ background: c.bg, color: c.color }}
        >
            {type}
        </span>
    );
}