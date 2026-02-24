import { useState, useEffect } from 'react';
import { api } from '../../api/client';

/**
 * Execution detail view - shows execution status, transcript, and QA coverage.
 * Consumes:
 *   GET /api/v1/executions/{id}
 *   GET /api/v1/executions/{id}/transcript
 *   GET /api/v1/executions/{id}/qa-coverage
 */
export default function ExecutionDetail({ executionId, onBack }) {
    const [execution, setExecution] = useState(null);
    const [transcript, setTranscript] = useState(null);
    const [qaCoverage, setQaCoverage] = useState(null);
    const [loading, setLoading] = useState(true);
    const [activeSection, setActiveSection] = useState('overview');

    useEffect(() => {
        loadData();
    }, [executionId]);

    async function loadData() {
        setLoading(true);
        try {
            // Try both execution APIs — exec- prefixed IDs are document-workflow
            // executions (plan_executor), others are old-style workflow executions.
            const [execRes, docExecRes, transcriptRes, qaRes] = await Promise.allSettled([
                api.getExecution(executionId),
                api.getDocumentWorkflowExecution(executionId),
                api.getExecutionTranscript(executionId),
                api.getExecutionQACoverage(executionId),
            ]);

            // Prefer document-workflow execution data (has richer fields)
            if (docExecRes.status === 'fulfilled' && docExecRes.value) {
                const dw = docExecRes.value;
                setExecution({
                    execution_id: dw.execution_id,
                    workflow_id: dw.workflow_id,
                    project_id: dw.project_id,
                    status: dw.status,
                    current_step_id: dw.current_node_id,
                    document_type: dw.document_type,
                    started_at: dw.created_at,
                    completed_at: dw.updated_at,
                    produced_documents: dw.produced_documents,
                });
            } else if (execRes.status === 'fulfilled' && execRes.value) {
                setExecution(execRes.value);
            }

            if (transcriptRes.status === 'fulfilled') setTranscript(transcriptRes.value);
            if (qaRes.status === 'fulfilled') setQaCoverage(qaRes.value);
        } catch (err) {
            console.error('Failed to load execution detail:', err);
        } finally {
            setLoading(false);
        }
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full">
                <p style={{ color: 'var(--text-muted)' }}>Loading execution...</p>
            </div>
        );
    }

    const sections = [
        { id: 'overview', label: 'Overview' },
        { id: 'transcript', label: `Transcript${transcript ? ` (${transcript.total_runs || 0})` : ''}` },
        { id: 'qa', label: 'QA Coverage' },
    ];

    return (
        <div className="h-full flex flex-col">
            {/* Back button + header */}
            <div className="flex items-center gap-3 p-4 border-b flex-shrink-0"
                 style={{ borderColor: 'var(--border-panel)' }}>
                <button
                    onClick={onBack}
                    className="text-xs px-2 py-1 rounded hover:opacity-80 transition-opacity"
                    style={{ color: 'var(--text-muted)', border: '1px solid var(--border-panel)' }}
                >
                    Back
                </button>
                <span className="font-mono text-sm" style={{ color: 'var(--text-primary)' }}>
                    {executionId}
                </span>
                {execution?.status && (
                    <span className="text-xs px-1.5 py-0.5 rounded"
                          style={{ background: statusColor(execution.status), color: 'white' }}>
                        {execution.status}
                    </span>
                )}
            </div>

            {/* Section tabs */}
            <div className="flex border-b px-4 flex-shrink-0"
                 style={{ borderColor: 'var(--border-panel)' }}>
                {sections.map(s => (
                    <button
                        key={s.id}
                        onClick={() => setActiveSection(s.id)}
                        className="px-3 py-2 text-xs transition-colors relative"
                        style={{
                            color: activeSection === s.id ? 'var(--text-primary)' : 'var(--text-muted)',
                            fontWeight: activeSection === s.id ? 600 : 400,
                        }}
                    >
                        {s.label}
                        {activeSection === s.id && (
                            <div className="absolute bottom-0 left-0 right-0 h-0.5"
                                 style={{ background: 'var(--accent-primary)' }} />
                        )}
                    </button>
                ))}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-auto p-4">
                {activeSection === 'overview' && <OverviewSection execution={execution} transcript={transcript} />}
                {activeSection === 'transcript' && <TranscriptSection transcript={transcript} />}
                {activeSection === 'qa' && <QACoverageSection qaCoverage={qaCoverage} />}
            </div>
        </div>
    );
}

function OverviewSection({ execution, transcript }) {
    if (!execution) return <p style={{ color: 'var(--text-muted)' }}>No execution data available.</p>;

    return (
        <div className="space-y-4 max-w-2xl">
            <div className="grid grid-cols-2 gap-4">
                <Field label="Execution ID" value={execution.execution_id} mono />
                <Field label="Workflow" value={execution.workflow_id} />
                <Field label="Project" value={execution.project_id} />
                <Field label="Status" value={execution.status} />
                <Field label="Started" value={formatDate(execution.started_at)} />
                <Field label="Completed" value={formatDate(execution.completed_at)} />
                <Field label="Current Step" value={execution.current_step_id || '-'} />
                <Field label="Completed Steps" value={execution.completed_steps?.length || 0} />
            </div>

            {transcript && (
                <div className="mt-6 p-3 rounded" style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-panel)' }}>
                    <h3 className="text-xs font-medium mb-2" style={{ color: 'var(--text-muted)' }}>Cost Summary</h3>
                    <div className="grid grid-cols-3 gap-4">
                        <Field label="Total Runs" value={transcript.total_runs || 0} />
                        <Field label="Total Tokens" value={(transcript.total_tokens || 0).toLocaleString()} />
                        <Field label="Total Cost" value={`$${(transcript.total_cost || 0).toFixed(4)}`} />
                    </div>
                </div>
            )}
        </div>
    );
}

function TranscriptSection({ transcript }) {
    const [expandedRuns, setExpandedRuns] = useState({});

    if (!transcript || !transcript.transcript?.length) {
        return <p style={{ color: 'var(--text-muted)' }}>No transcript data available.</p>;
    }

    const toggleRun = (i) => {
        setExpandedRuns(prev => ({ ...prev, [i]: !prev[i] }));
    };

    return (
        <div className="space-y-3">
            <div className="flex items-center gap-4 mb-4">
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                    {transcript.total_runs} run{transcript.total_runs !== 1 ? 's' : ''} |
                    {' '}{(transcript.total_tokens || 0).toLocaleString()} tokens |
                    {' '}${(transcript.total_cost || 0).toFixed(4)}
                </span>
            </div>
            {transcript.transcript.map((entry, i) => (
                <div key={i} className="rounded text-xs" style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-panel)' }}>
                    {/* Header row — click to expand */}
                    <button
                        onClick={() => toggleRun(i)}
                        className="w-full text-left p-3 hover:opacity-80 transition-opacity"
                    >
                        <div className="flex items-center gap-3 mb-2">
                            <span style={{ color: 'var(--text-muted)', fontSize: '10px' }}>
                                {expandedRuns[i] ? '\u25BC' : '\u25B6'}
                            </span>
                            <span className="font-mono font-medium" style={{ color: 'var(--text-primary)' }}>
                                #{entry.run_number}
                            </span>
                            <span style={{ color: 'var(--text-muted)' }}>{entry.role}</span>
                            {entry.node_id && (
                                <span className="font-mono" style={{ color: 'var(--text-muted)' }}>
                                    {entry.node_id}
                                </span>
                            )}
                            {entry.task_ref && (
                                <span className="font-mono" style={{ color: 'var(--text-muted)', opacity: 0.7 }}>
                                    {entry.task_ref}
                                </span>
                            )}
                            <span className="ml-auto" style={{ color: 'var(--text-muted)' }}>
                                {entry.model}
                            </span>
                        </div>
                        <div className="flex items-center gap-4" style={{ color: 'var(--text-muted)' }}>
                            <span className="px-1.5 py-0.5 rounded" style={{ background: statusColor(entry.status), color: 'white' }}>
                                {entry.status}
                            </span>
                            {entry.duration && <span>{entry.duration}</span>}
                            <span>{(typeof entry.tokens === 'number' ? entry.tokens : entry.tokens?.total || 0).toLocaleString()} tokens</span>
                            <span>${(entry.cost || 0).toFixed(4)}</span>
                        </div>
                    </button>

                    {/* Expanded content: inputs + outputs */}
                    {expandedRuns[i] && (
                        <div className="border-t px-3 pb-3" style={{ borderColor: 'var(--border-panel)' }}>
                            {/* Inputs */}
                            {entry.inputs?.length > 0 && (
                                <div className="mt-3">
                                    <div className="text-xs font-medium mb-2" style={{ color: 'var(--text-muted)' }}>
                                        Inputs ({entry.inputs.length})
                                    </div>
                                    {entry.inputs.map((inp, j) => (
                                        <TranscriptBlock key={j} label={inp.kind} content={inp.content} size={inp.size} />
                                    ))}
                                </div>
                            )}
                            {/* Outputs */}
                            {entry.outputs?.length > 0 && (
                                <div className="mt-3">
                                    <div className="text-xs font-medium mb-2" style={{ color: 'var(--text-muted)' }}>
                                        Outputs ({entry.outputs.length})
                                    </div>
                                    {entry.outputs.map((out, j) => (
                                        <TranscriptBlock
                                            key={j}
                                            label={out.kind}
                                            content={out.content}
                                            size={out.size}
                                            parseStatus={out.parse_status}
                                            validationStatus={out.validation_status}
                                        />
                                    ))}
                                </div>
                            )}
                            {(!entry.inputs?.length && !entry.outputs?.length) && (
                                <p className="mt-3" style={{ color: 'var(--text-muted)' }}>No input/output content recorded.</p>
                            )}
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
}

function TranscriptBlock({ label, content, size, parseStatus, validationStatus }) {
    const [collapsed, setCollapsed] = useState(false);
    const hasContent = content && content.length > 0;
    const isLong = hasContent && content.length > 500;

    return (
        <div className="mb-2 rounded" style={{ border: '1px solid var(--border-panel)' }}>
            <div
                className="flex items-center gap-2 px-2 py-1.5"
                style={{ background: 'var(--bg-canvas)' }}
            >
                <span className="font-mono font-medium text-xs" style={{ color: 'var(--accent-primary)' }}>
                    {label || 'content'}
                </span>
                {size > 0 && (
                    <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                        {size > 1024 ? `${(size / 1024).toFixed(1)} KB` : `${size} B`}
                    </span>
                )}
                {parseStatus && (
                    <span className="text-xs px-1 rounded" style={{
                        background: parseStatus === 'ok' ? 'var(--state-complete, #10b981)' : 'var(--state-error, #ef4444)',
                        color: 'white',
                    }}>
                        {parseStatus}
                    </span>
                )}
                {validationStatus && (
                    <span className="text-xs px-1 rounded" style={{
                        background: validationStatus === 'valid' ? 'var(--state-complete, #10b981)' : 'var(--state-error, #ef4444)',
                        color: 'white',
                    }}>
                        {validationStatus}
                    </span>
                )}
                {isLong && (
                    <button
                        onClick={() => setCollapsed(!collapsed)}
                        className="ml-auto text-xs hover:opacity-80"
                        style={{ color: 'var(--accent-primary)' }}
                    >
                        {collapsed ? 'Expand' : 'Collapse'}
                    </button>
                )}
            </div>
            {hasContent && (
                <pre
                    className="p-2 text-xs overflow-x-auto"
                    style={{
                        color: 'var(--text-primary)',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        maxHeight: collapsed ? '200px' : 'none',
                        overflow: collapsed ? 'hidden' : 'visible',
                        borderTop: '1px solid var(--border-panel)',
                    }}
                >
                    {content}
                </pre>
            )}
            {!hasContent && (
                <p className="px-2 py-1 text-xs" style={{ color: 'var(--text-muted)' }}>(empty)</p>
            )}
        </div>
    );
}

function QACoverageSection({ qaCoverage }) {
    if (!qaCoverage) {
        return <p style={{ color: 'var(--text-muted)' }}>No QA coverage data available.</p>;
    }

    const summary = qaCoverage.summary || {};
    const nodes = qaCoverage.qa_nodes || [];

    return (
        <div className="space-y-4">
            {/* Summary */}
            <div className="grid grid-cols-4 gap-4">
                <Field label="Passed" value={summary.passed || 0} />
                <Field label="Failed" value={summary.failed || 0} />
                <Field label="Errors" value={summary.errors || 0} />
                <Field label="Warnings" value={summary.warnings || 0} />
            </div>

            {/* Node details */}
            {nodes.length > 0 && (
                <div className="space-y-2 mt-4">
                    <h3 className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>QA Nodes</h3>
                    {nodes.map((node, i) => (
                        <div key={i} className="p-3 rounded text-xs"
                             style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-panel)' }}>
                            <div className="font-mono font-medium mb-1" style={{ color: 'var(--text-primary)' }}>
                                {node.node_id || `Node ${i + 1}`}
                            </div>
                            {node.findings?.length > 0 && (
                                <ul className="list-disc list-inside" style={{ color: 'var(--text-muted)' }}>
                                    {node.findings.map((f, j) => (
                                        <li key={j}>{typeof f === 'string' ? f : JSON.stringify(f)}</li>
                                    ))}
                                </ul>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

function Field({ label, value, mono }) {
    return (
        <div>
            <div className="text-xs mb-0.5" style={{ color: 'var(--text-muted)' }}>{label}</div>
            <div className={`text-sm ${mono ? 'font-mono' : ''}`} style={{ color: 'var(--text-primary)' }}>
                {value || '-'}
            </div>
        </div>
    );
}

function statusColor(status) {
    const s = (status || '').toLowerCase();
    if (s.includes('complete') || s === 'done' || s === 'success') return 'var(--state-complete, #10b981)';
    if (s.includes('running') || s.includes('active') || s.includes('progress')) return 'var(--state-active, #f59e0b)';
    if (s.includes('fail') || s.includes('error')) return 'var(--state-error, #ef4444)';
    return 'var(--state-pending, #6b7280)';
}

function formatDate(isoString) {
    if (!isoString) return '-';
    try {
        const d = new Date(isoString);
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
            + ' ' + d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    } catch {
        return isoString;
    }
}
