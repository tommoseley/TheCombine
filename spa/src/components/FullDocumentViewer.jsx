import { useState, useEffect } from 'react';
import { api } from '../api/client';
import RenderModelViewer from './RenderModelViewer';
import TechnicalArchitectureViewer from './viewers/TechnicalArchitectureViewer';

/**
 * Full-screen document viewer modal - Data-Driven
 *
 * Fetches RenderModel from API and renders using the data-driven
 * RenderModelViewer component. Falls back to raw JSON display
 * if RenderModel is not available.
 */
export default function FullDocumentViewer({ projectId, projectCode, docTypeId, instanceId, onClose }) {
    const [renderModel, setRenderModel] = useState(null);
    const [rawContent, setRawContent] = useState(null);
    const [docMetadata, setDocMetadata] = useState({});
    const [docTitle, setDocTitle] = useState(null);
    const [pgcContext, setPgcContext] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        async function fetchDocument() {
            try {
                setLoading(true);
                setError(null);

                // Fetch PGC context in parallel (non-blocking)
                api.getDocumentPgc(projectId, docTypeId, instanceId)
                    .then(pgc => { if (pgc?.has_pgc) setPgcContext(pgc); })
                    .catch(() => {}); // PGC is optional

                // Try to fetch RenderModel first (data-driven display)
                try {
                    const rm = await api.getDocumentRenderModel(projectId, docTypeId, instanceId);
                    // Always preserve metadata and title from render model response
                    if (rm?.metadata) setDocMetadata(rm.metadata);
                    if (rm?.title) setDocTitle(rm.title);

                    if (rm && rm.sections && rm.sections.length > 0) {
                        setRenderModel(rm);
                        setRawContent(null);
                        return;
                    }
                    // If RenderModel has fallback flag, use raw content
                    if (rm?.metadata?.fallback && rm.raw_content) {
                        setRenderModel(null);
                        setRawContent(rm.raw_content);
                        return;
                    }
                } catch (rmErr) {
                    console.log('RenderModel not available, falling back to raw document:', rmErr.message);
                }

                // Fall back to raw document content
                const doc = await api.getDocument(projectId, docTypeId, instanceId);
                setRenderModel(null);
                setRawContent(doc?.content || null);
            } catch (err) {
                setError(err.message);
                console.error('Failed to fetch document:', err);
            } finally {
                setLoading(false);
            }
        }
        fetchDocument();
    }, [projectId, docTypeId, instanceId]);

    // Close on Escape key
    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.key === 'Escape') onClose();
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [onClose]);

    // Loading state
    if (loading) {
        return (
            <div
                className="fixed inset-0 z-[9999] flex items-center justify-center"
                style={{ background: 'rgba(0,0,0,0.8)' }}
            >
                <div style={{ color: 'white', fontSize: 14 }}>Loading...</div>
            </div>
        );
    }

    // Extract metadata for header and admin link
    // Use docMetadata (persisted from render model response) which survives fallback paths
    const metadata = renderModel?.metadata || docMetadata;
    const executionId = metadata.execution_id;
    const adminUrl = executionId ? `/admin?execution=${executionId}` : '/admin';

    // Route Technical Architecture documents to specialized viewer
    const isTechnicalArchitecture = docTypeId === 'technical_architecture';

    if (isTechnicalArchitecture && renderModel) {
        return (
            <div
                className="fixed inset-0 z-[9999] flex items-center justify-center"
                style={{ background: 'rgba(0,0,0,0.8)' }}
                onClick={(e) => e.target === e.currentTarget && onClose()}
            >
                <div
                    className="relative w-full max-w-6xl h-[90vh] overflow-hidden rounded-lg shadow-2xl flex flex-col"
                    style={{ background: '#ffffff' }}
                >
                    {/* Close button */}
                    <button
                        onClick={onClose}
                        className="absolute top-2 right-3 z-10 p-1.5 rounded-lg hover:bg-gray-200 transition-colors"
                        style={{ background: 'rgba(255,255,255,0.9)' }}
                    >
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M18 6L6 18M6 6l12 12" />
                        </svg>
                    </button>
                    <TechnicalArchitectureViewer
                        renderModel={renderModel}
                        projectId={projectId}
                        projectCode={projectCode}
                        docTypeId={docTypeId}
                        executionId={executionId}
                        pgcContext={pgcContext}
                        onClose={onClose}
                    />
                </div>
            </div>
        );
    }

    return (
        <div
            className="fixed inset-0 z-[9999] flex items-center justify-center"
            style={{ background: 'rgba(0,0,0,0.8)' }}
            onClick={(e) => e.target === e.currentTarget && onClose()}
        >
            <div
                className="relative w-full max-w-4xl max-h-[90vh] overflow-hidden rounded-lg shadow-2xl"
                style={{ background: '#ffffff' }}
            >
                {/* Document Header */}
                <DocumentHeader
                    title={renderModel?.title || docTitle}
                    projectCode={projectCode}
                    adminUrl={adminUrl}
                    executionId={executionId}
                    metadata={metadata}
                    onClose={onClose}
                />

                {/* Spawned children panel */}
                {metadata?.spawned_children?.count > 0 && (
                    <SpawnedChildrenPanel children={metadata.spawned_children} />
                )}

                {/* Content */}
                <div
                    className="overflow-y-auto p-6"
                    style={{ maxHeight: metadata?.spawned_children?.count > 0 ? 'calc(90vh - 130px)' : 'calc(90vh - 80px)' }}
                    onWheel={(e) => e.stopPropagation()}
                >
                    {error && (
                        <div className="text-center py-12">
                            <p className="text-red-500">{error}</p>
                        </div>
                    )}

                    {renderModel && (
                        <RenderModelViewer renderModel={renderModel} variant="full" hideHeader={true} />
                    )}

                    {rawContent && !renderModel && (
                        <RawContentViewer content={rawContent} docTypeId={docTypeId} />
                    )}

                    {!renderModel && !rawContent && !error && (
                        <div className="text-center py-12">
                            <p className="text-gray-500">No content available</p>
                        </div>
                    )}

                    {/* PGC Context section - shown for any document that went through PGC */}
                    {pgcContext && pgcContext.clarifications?.length > 0 && (
                        <PgcContextSection pgcContext={pgcContext} />
                    )}
                </div>
            </div>
        </div>
    );
}

/**
 * Document header with title, project badge, metadata, and close button.
 * Used by both generic and specialized document viewers.
 */
function DocumentHeader({ title, projectCode, adminUrl, executionId, metadata, onClose }) {
    const displayTitle = (() => {
        if (!title) return 'Document';
        const colonIndex = title.indexOf(': ');
        return colonIndex > -1 ? title.slice(colonIndex + 2) : title;
    })();

    const docType = metadata?.document_type_name
        || (metadata?.document_type
            ? metadata.document_type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
            : null);

    const formatDate = (iso) => {
        if (!iso) return null;
        try {
            const d = new Date(iso);
            return d.toLocaleDateString('en-US', {
                year: 'numeric', month: 'short', day: 'numeric',
                hour: '2-digit', minute: '2-digit',
            });
        } catch { return null; }
    };

    const generatedDate = formatDate(metadata?.created_at);
    const updatedDate = formatDate(metadata?.updated_at);
    const version = metadata?.version;
    const lifecycleState = metadata?.lifecycle_state;

    return (
        <div
            className="sticky top-0 px-6 py-4 border-b"
            style={{ background: '#f8fafc', borderColor: '#e2e8f0' }}
        >
            <div className="flex items-start justify-between">
                <div style={{ flex: 1, minWidth: 0 }}>
                    {/* Top line: badges */}
                    <div className="flex items-center gap-2 flex-wrap" style={{ marginBottom: 6 }}>
                        {projectCode && (
                            <a
                                href={adminUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                title={executionId ? `View execution ${executionId}` : 'Open Admin Executions'}
                                style={{
                                    padding: '2px 8px',
                                    background: '#10b981',
                                    color: 'white',
                                    fontSize: 11,
                                    fontWeight: 600,
                                    borderRadius: 4,
                                    letterSpacing: '0.05em',
                                    textDecoration: 'none',
                                    cursor: 'pointer',
                                }}
                            >
                                {projectCode}
                            </a>
                        )}
                        {docType && (
                            <span style={{
                                padding: '2px 8px',
                                background: '#eef2ff',
                                color: '#4f46e5',
                                fontSize: 11,
                                fontWeight: 600,
                                borderRadius: 4,
                            }}>
                                {docType}
                            </span>
                        )}
                        {lifecycleState && (
                            <span style={{
                                padding: '2px 8px',
                                background: lifecycleState === 'complete' ? '#dcfce7' : '#fef3c7',
                                color: lifecycleState === 'complete' ? '#166534' : '#92400e',
                                fontSize: 11,
                                fontWeight: 600,
                                borderRadius: 4,
                            }}>
                                {lifecycleState}
                            </span>
                        )}
                        {version && version > 1 && (
                            <span style={{
                                padding: '2px 8px',
                                background: '#f3f4f6',
                                color: '#6b7280',
                                fontSize: 11,
                                fontWeight: 600,
                                borderRadius: 4,
                            }}>
                                v{version}
                            </span>
                        )}
                    </div>
                    {/* Title */}
                    <h2 style={{
                        margin: 0,
                        fontSize: 20,
                        fontWeight: 700,
                        color: '#111827',
                        lineHeight: 1.3,
                    }}>
                        {displayTitle}
                    </h2>
                    {/* Date line */}
                    {generatedDate && (
                        <div style={{ marginTop: 4, fontSize: 12, color: '#9ca3af' }}>
                            Generated {generatedDate}
                            {updatedDate && updatedDate !== generatedDate && (
                                <span> &middot; Updated {updatedDate}</span>
                            )}
                        </div>
                    )}
                </div>
                <button
                    onClick={onClose}
                    className="p-2 rounded-lg hover:bg-gray-200 transition-colors"
                    style={{ flexShrink: 0, marginLeft: 12 }}
                >
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M18 6L6 18M6 6l12 12" />
                    </svg>
                </button>
            </div>
        </div>
    );
}

/**
 * Spawned children panel - shows "This plan produced N Epic documents" with chips.
 */
function SpawnedChildrenPanel({ children }) {
    const { count, items } = children;
    return (
        <div
            className="flex items-center gap-3 flex-wrap px-6 py-3"
            style={{ background: '#f0fdf4', borderBottom: '1px solid #bbf7d0' }}
        >
            <span style={{ fontSize: 13, color: '#166534', fontWeight: 600 }}>
                This plan produced {count} Epic document{count !== 1 ? 's' : ''}
            </span>
            <div className="flex items-center gap-1.5 flex-wrap">
                {items.map((item) => (
                    <span
                        key={item.epic_id}
                        title={item.title || item.name}
                        style={{
                            padding: '2px 8px',
                            background: '#dcfce7',
                            color: '#15803d',
                            fontSize: 11,
                            fontWeight: 500,
                            borderRadius: 4,
                            whiteSpace: 'nowrap',
                        }}
                    >
                        {item.name || item.epic_id}
                    </span>
                ))}
            </div>
        </div>
    );
}

/**
 * Raw content viewer - renders structured content intelligently.
 * Detects arrays of objects and renders fields; falls back to JSON for unknown shapes.
 */
function RawContentViewer({ content, docTypeId }) {
    if (!content) {
        return <p className="text-gray-500">No content available</p>;
    }

    const title = content.project_name || content.title || content.name;

    // Section configuration: map known keys to display config
    const SECTION_CONFIG = {
        preliminary_summary: { title: 'Summary', icon: 'S', color: '#7c3aed', render: 'summary' },
        stakeholder_questions: { title: 'Stakeholder Questions', icon: '?', color: '#dc2626', render: 'questions' },
        unknowns: { title: 'Unknowns to Resolve', icon: '?', color: '#d97706' },
        early_decision_points: { title: 'Early Decision Points', icon: 'D', color: '#7c3aed' },
        risks: { title: 'Risks', icon: '!', color: '#dc2626' },
        known_constraints: { title: 'Known Constraints', icon: 'C', color: '#6b7280' },
        assumptions: { title: 'Assumptions', icon: 'A', color: '#d97706' },
        mvp_guardrails: { title: 'MVP Guardrails', icon: 'G', color: '#059669' },
        recommendations_for_pm: { title: 'Recommendations for PM', icon: 'R', color: '#2563eb' },
        pgc_clarifications: { title: 'PGC Clarifications', icon: 'Q', color: '#7c3aed', render: 'clarifications' },
    };

    // Keys to skip in structured rendering (handled specially or metadata)
    const SKIP_KEYS = new Set(['project_name', 'title', 'name', 'meta', 'description', 'summary']);

    // Check if content has structured sections we can render
    const structuredKeys = Object.keys(content).filter(
        k => !SKIP_KEYS.has(k) && (Array.isArray(content[k]) || (typeof content[k] === 'object' && content[k] !== null))
    );
    const hasStructuredContent = structuredKeys.length > 0;

    if (!hasStructuredContent) {
        return <FallbackJsonViewer content={content} docTypeId={docTypeId} title={title} />;
    }

    return (
        <div className="space-y-6">
            {/* Title */}
            {title && (
                <div style={{ borderBottom: '2px solid #7c3aed', paddingBottom: 12 }}>
                    <h2 className="text-2xl font-bold text-gray-900">{title}</h2>
                    <span className="text-xs font-mono text-gray-400">{docTypeId}</span>
                </div>
            )}

            {/* Render each section in config order, then any remaining */}
            {Object.entries(SECTION_CONFIG).map(([key, cfg]) => {
                const data = content[key];
                if (!data) return null;

                if (cfg.render === 'summary' && typeof data === 'object' && !Array.isArray(data)) {
                    return <SummarySection key={key} data={data} config={cfg} />;
                }
                if (cfg.render === 'questions' && Array.isArray(data)) {
                    return <QuestionsSection key={key} data={data} config={cfg} />;
                }
                if (cfg.render === 'clarifications' && Array.isArray(data)) {
                    return <ClarificationsSection key={key} data={data} config={cfg} />;
                }
                if (Array.isArray(data)) {
                    return <ArraySection key={key} data={data} config={cfg} />;
                }
                return null;
            })}

            {/* Render any remaining keys not in config */}
            {structuredKeys
                .filter(k => !SECTION_CONFIG[k])
                .map(key => {
                    const data = content[key];
                    if (Array.isArray(data)) {
                        return (
                            <ArraySection
                                key={key}
                                data={data}
                                config={{ title: formatLabel(key), icon: '#', color: '#6b7280' }}
                            />
                        );
                    }
                    if (typeof data === 'object' && data !== null) {
                        return (
                            <ObjectSection
                                key={key}
                                data={data}
                                label={formatLabel(key)}
                            />
                        );
                    }
                    return null;
                })}

            {/* Collapsible Raw JSON */}
            <details style={{ borderRadius: 8, border: '1px solid #e2e8f0' }}>
                <summary
                    style={{
                        padding: '12px 16px',
                        cursor: 'pointer',
                        fontSize: 13,
                        fontWeight: 600,
                        color: '#6b7280',
                        background: '#f8fafc',
                        borderRadius: 8,
                    }}
                >
                    Raw Data (JSON)
                </summary>
                <div style={{ padding: 16, overflow: 'auto' }}>
                    <pre style={{ margin: 0, fontSize: 11, color: '#374151', whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontFamily: 'monospace', lineHeight: 1.5 }}>
                        {JSON.stringify(content, null, 2)}
                    </pre>
                </div>
            </details>
        </div>
    );
}

/** Summary section (preliminary_summary) */
function SummarySection({ data, config }) {
    const fields = [
        { key: 'problem_understanding', label: 'Problem Understanding' },
        { key: 'architectural_intent', label: 'Architectural Intent' },
        { key: 'proposed_system_shape', label: 'Proposed System Shape' },
    ];
    return (
        <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8 }}>
            <SectionHeader config={config} />
            <div style={{ padding: 16 }} className="space-y-3">
                {fields.map(f => data[f.key] ? (
                    <div key={f.key} style={{ borderLeft: `3px solid ${config.color}`, paddingLeft: 12 }}>
                        <div style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>{f.label}</div>
                        <p style={{ fontSize: 14, color: '#1f2937', margin: 0, lineHeight: 1.6 }}>{data[f.key]}</p>
                    </div>
                ) : null)}
                {/* Render any other fields */}
                {Object.entries(data)
                    .filter(([k]) => !fields.some(f => f.key === k))
                    .map(([k, v]) => typeof v === 'string' ? (
                        <div key={k} style={{ borderLeft: `3px solid ${config.color}`, paddingLeft: 12 }}>
                            <div style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>{formatLabel(k)}</div>
                            <p style={{ fontSize: 14, color: '#1f2937', margin: 0, lineHeight: 1.6 }}>{v}</p>
                        </div>
                    ) : null)}
            </div>
        </div>
    );
}

/** Questions section (stakeholder_questions) */
function QuestionsSection({ data, config }) {
    const blocking = data.filter(q => q.blocking);
    const nonBlocking = data.filter(q => !q.blocking);

    return (
        <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8 }}>
            <SectionHeader config={config} count={data.length} />
            <div style={{ padding: 16 }} className="space-y-3">
                {blocking.length > 0 && (
                    <div style={{ marginBottom: 8 }}>
                        <div style={{ fontSize: 11, fontWeight: 700, color: '#dc2626', marginBottom: 8, textTransform: 'uppercase' }}>Blocking</div>
                        {blocking.map((q, i) => (
                            <QuestionItem key={q.id || i} q={q} borderColor="#dc2626" />
                        ))}
                    </div>
                )}
                {nonBlocking.length > 0 && (
                    <div>
                        {blocking.length > 0 && <div style={{ fontSize: 11, fontWeight: 700, color: '#6b7280', marginBottom: 8, textTransform: 'uppercase' }}>Non-blocking</div>}
                        {nonBlocking.map((q, i) => (
                            <QuestionItem key={q.id || i} q={q} borderColor="#d1d5db" />
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

function QuestionItem({ q, borderColor }) {
    return (
        <div style={{ borderLeft: `3px solid ${borderColor}`, paddingLeft: 12, marginBottom: 8 }}>
            <div className="flex items-center gap-2" style={{ marginBottom: 2 }}>
                {q.id && <span style={{ fontFamily: 'monospace', fontSize: 11, color: '#9ca3af' }}>{q.id}</span>}
                {q.directed_to && <span style={{ fontSize: 11, padding: '1px 6px', background: '#f3f4f6', borderRadius: 4, color: '#6b7280' }}>{q.directed_to.replace(/_/g, ' ')}</span>}
            </div>
            <p style={{ fontSize: 14, color: '#1f2937', margin: 0, fontWeight: 500 }}>{q.question || q.text || extractText(q)}</p>
            {q.notes && <p style={{ fontSize: 12, color: '#6b7280', margin: '4px 0 0' }}>{q.notes}</p>}
        </div>
    );
}

/** PGC Clarifications section (for clarifications embedded in document content) */
function ClarificationsSection({ data, config }) {
    const kindColors = {
        exclusion: { bg: '#fee2e2', color: '#991b1b' },
        requirement: { bg: '#dbeafe', color: '#1e40af' },
        selection: { bg: '#f3f4f6', color: '#4b5563' },
        preference: { bg: '#f0fdf4', color: '#166534' },
    };
    return (
        <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8 }}>
            <SectionHeader config={config} count={data.length} />
            <div style={{ padding: 16 }} className="space-y-3">
                {data.map((c, i) => {
                    const kc = kindColors[c.constraint_kind] || kindColors.selection;
                    return (
                        <div key={c.question_id || i} style={{ borderLeft: `3px solid ${config.color}`, paddingLeft: 12, marginBottom: 8 }}>
                            <div className="flex items-center gap-2" style={{ marginBottom: 2, flexWrap: 'wrap' }}>
                                {c.question_id && <span style={{ fontFamily: 'monospace', fontSize: 11, color: '#9ca3af' }}>{c.question_id}</span>}
                                {c.binding && <span style={{ fontSize: 10, padding: '1px 5px', background: '#dbeafe', color: '#1e40af', borderRadius: 4, fontWeight: 600 }}>BINDING</span>}
                                {c.constraint_kind && <span style={{ fontSize: 10, padding: '1px 5px', background: kc.bg, color: kc.color, borderRadius: 4 }}>{c.constraint_kind}</span>}
                                {c.binding_source && <span style={{ fontSize: 10, color: '#9ca3af' }}>via {c.binding_source}</span>}
                            </div>
                            <p style={{ fontSize: 14, color: '#1f2937', margin: '2px 0', fontWeight: 500 }}>{c.question}</p>
                            {c.why_it_matters && (
                                <p style={{ fontSize: 12, color: '#6b7280', margin: '4px 0', fontStyle: 'italic' }}>{c.why_it_matters}</p>
                            )}
                            {c.answer && (
                                <div style={{ marginTop: 4, display: 'flex', alignItems: 'baseline', gap: 6 }}>
                                    <span style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Answer:</span>
                                    <span style={{ fontSize: 13, color: '#059669', fontWeight: 500 }}>{c.answer}</span>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

/** PGC Context section - questions, rationale, and operator answers */
function PgcContextSection({ pgcContext }) {
    const { clarifications } = pgcContext;
    const binding = clarifications.filter(c => c.binding);
    const informational = clarifications.filter(c => !c.binding);

    return (
        <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, marginTop: 24 }}>
            <div className="flex items-center gap-2" style={{ padding: '12px 16px', borderBottom: '1px solid #e2e8f0' }}>
                <span style={{
                    width: 24, height: 24, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 12, fontWeight: 700, background: '#7c3aed15', color: '#7c3aed',
                }}>Q</span>
                <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: '#1f2937' }}>Pre-Generation Clarifications</h3>
                <span style={{ marginLeft: 'auto', fontSize: 12, color: '#9ca3af' }}>{clarifications.length}</span>
            </div>
            <div style={{ padding: 16 }} className="space-y-4">
                {binding.length > 0 && (
                    <div>
                        <div style={{ fontSize: 11, fontWeight: 700, color: '#1e40af', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                            Binding Constraints ({binding.length})
                        </div>
                        {binding.map((c, i) => (
                            <PgcClarificationItem key={c.question_id || i} item={c} />
                        ))}
                    </div>
                )}
                {informational.length > 0 && (
                    <div>
                        {binding.length > 0 && (
                            <div style={{ fontSize: 11, fontWeight: 700, color: '#6b7280', marginBottom: 8, marginTop: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                Informational ({informational.length})
                            </div>
                        )}
                        {informational.map((c, i) => (
                            <PgcClarificationItem key={c.question_id || i} item={c} />
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

/** Single PGC clarification item with question, rationale, answer, and binding metadata */
function PgcClarificationItem({ item }) {
    const kindColors = {
        exclusion: { bg: '#fee2e2', color: '#991b1b' },
        requirement: { bg: '#dbeafe', color: '#1e40af' },
        selection: { bg: '#f3f4f6', color: '#4b5563' },
        preference: { bg: '#f0fdf4', color: '#166534' },
    };
    const kc = kindColors[item.constraint_kind] || kindColors.selection;

    return (
        <div style={{ borderLeft: `3px solid ${item.binding ? '#3b82f6' : '#d1d5db'}`, paddingLeft: 12, marginBottom: 12 }}>
            <div className="flex items-center gap-2" style={{ marginBottom: 2, flexWrap: 'wrap' }}>
                {item.question_id && (
                    <span style={{ fontFamily: 'monospace', fontSize: 11, color: '#9ca3af' }}>{item.question_id}</span>
                )}
                {item.binding && (
                    <span style={{ fontSize: 10, padding: '1px 5px', background: '#dbeafe', color: '#1e40af', borderRadius: 4, fontWeight: 600 }}>BINDING</span>
                )}
                {item.constraint_kind && (
                    <span style={{ fontSize: 10, padding: '1px 5px', background: kc.bg, color: kc.color, borderRadius: 4 }}>{item.constraint_kind}</span>
                )}
                {item.binding_source && (
                    <span style={{ fontSize: 10, color: '#9ca3af' }}>via {item.binding_source}</span>
                )}
            </div>
            <p style={{ fontSize: 14, color: '#1f2937', margin: '2px 0', fontWeight: 500 }}>{item.question}</p>
            {item.why_it_matters && (
                <p style={{ fontSize: 12, color: '#6b7280', margin: '4px 0', fontStyle: 'italic' }}>
                    {item.why_it_matters}
                </p>
            )}
            {item.answer && (
                <div style={{ marginTop: 4, display: 'flex', alignItems: 'baseline', gap: 6 }}>
                    <span style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Answer:</span>
                    <span style={{ fontSize: 13, color: '#059669', fontWeight: 500 }}>{item.answer}</span>
                </div>
            )}
        </div>
    );
}

/** Generic array section - renders items with smart field extraction */
function ArraySection({ data, config }) {
    if (!data || data.length === 0) return null;
    return (
        <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8 }}>
            <SectionHeader config={config} count={data.length} />
            <div style={{ padding: 16 }}>
                <ul style={{ margin: 0, padding: 0, listStyle: 'none' }} className="space-y-2">
                    {data.map((item, i) => (
                        <li key={typeof item === 'object' ? (item.id || i) : i} className="flex items-start gap-2" style={{ fontSize: 14, color: '#374151' }}>
                            <span style={{ color: config.color, marginTop: 2, flexShrink: 0, fontSize: 12 }}>{config.icon === '!' ? '\u25B2' : '\u2022'}</span>
                            <div style={{ flex: 1 }}>
                                {typeof item === 'string' ? (
                                    <span>{item}</span>
                                ) : typeof item === 'object' && item !== null ? (
                                    <StructuredItem item={item} />
                                ) : (
                                    <span>{String(item)}</span>
                                )}
                            </div>
                        </li>
                    ))}
                </ul>
            </div>
        </div>
    );
}

/** Render a single structured item (object) with smart field extraction */
function StructuredItem({ item }) {
    // Extract the primary text field
    const textKeys = ['constraint', 'assumption', 'guardrail', 'recommendation', 'description', 'question', 'text', 'statement', 'name', 'title'];
    const textKey = textKeys.find(k => item[k] && typeof item[k] === 'string');
    const text = textKey ? item[textKey] : null;

    // Extract known metadata fields
    const id = item.id;
    const confidence = item.confidence;
    const constraintType = item.constraint_type;
    const validationApproach = item.validation_approach;
    const impact = item.impact_on_planning || item.impact_if_unresolved;
    const mitigation = item.mitigation_direction;
    const likelihood = item.likelihood;
    const why = item.why_it_matters || item.why_early;
    const recommendation = item.recommendation_direction;

    // If no recognizable text field, show the whole object as inline fields
    if (!text) {
        return (
            <span style={{ fontSize: 13, color: '#374151' }}>
                {Object.entries(item).map(([k, v], i) => (
                    <span key={k}>
                        {i > 0 && ' \u00B7 '}
                        <span style={{ fontWeight: 500 }}>{formatLabel(k)}:</span> {typeof v === 'string' ? v : JSON.stringify(v)}
                    </span>
                ))}
            </span>
        );
    }

    return (
        <div>
            <div className="flex items-center gap-2 flex-wrap">
                {id && <span style={{ fontFamily: 'monospace', fontSize: 11, color: '#9ca3af' }}>{id}</span>}
                <span style={{ fontWeight: 500 }}>{text}</span>
                {constraintType && <span style={{ fontSize: 11, padding: '1px 6px', background: '#f3f4f6', borderRadius: 4, color: '#6b7280' }}>{constraintType}</span>}
                {confidence && (
                    <span style={{
                        fontSize: 11, padding: '1px 6px', borderRadius: 4, fontWeight: 600,
                        background: confidence === 'high' ? '#dcfce7' : confidence === 'medium' ? '#fef3c7' : '#fee2e2',
                        color: confidence === 'high' ? '#166534' : confidence === 'medium' ? '#92400e' : '#991b1b',
                    }}>{confidence}</span>
                )}
                {likelihood && <span style={{ fontSize: 11, padding: '1px 6px', background: '#fee2e2', borderRadius: 4, color: '#991b1b' }}>{likelihood}/{item.impact || '?'}</span>}
            </div>
            {validationApproach && <p style={{ fontSize: 12, color: '#6b7280', margin: '2px 0 0' }}>Validation: {validationApproach}</p>}
            {why && <p style={{ fontSize: 12, color: '#6b7280', margin: '2px 0 0' }}>Why: {why}</p>}
            {impact && <p style={{ fontSize: 12, color: '#6b7280', margin: '2px 0 0' }}>Impact: {impact}</p>}
            {mitigation && <p style={{ fontSize: 12, color: '#6b7280', margin: '2px 0 0' }}>Mitigation: {mitigation}</p>}
            {recommendation && <p style={{ fontSize: 12, color: '#059669', margin: '2px 0 0' }}>Recommendation: {recommendation}</p>}
        </div>
    );
}

/** Render an object as a labeled section */
function ObjectSection({ data, label }) {
    return (
        <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8 }}>
            <div style={{ padding: '12px 16px', borderBottom: '1px solid #e2e8f0', fontWeight: 600, fontSize: 14, color: '#1f2937' }}>{label}</div>
            <div style={{ padding: 16 }}>
                {Object.entries(data).map(([k, v]) => (
                    <div key={k} style={{ marginBottom: 8 }}>
                        <div style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 2 }}>{formatLabel(k)}</div>
                        <div style={{ fontSize: 14, color: '#1f2937' }}>
                            {typeof v === 'string' ? v : typeof v === 'object' ? JSON.stringify(v, null, 2) : String(v)}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

/** Section header with icon and count badge */
function SectionHeader({ config, count }) {
    return (
        <div className="flex items-center gap-2" style={{ padding: '12px 16px', borderBottom: '1px solid #e2e8f0' }}>
            <span style={{
                width: 24, height: 24, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 12, fontWeight: 700, background: `${config.color}15`, color: config.color,
            }}>{config.icon}</span>
            <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: '#1f2937' }}>{config.title}</h3>
            {count !== undefined && <span style={{ marginLeft: 'auto', fontSize: 12, color: '#9ca3af' }}>{count}</span>}
        </div>
    );
}

/** Fallback: pure JSON viewer for truly unstructured content */
function FallbackJsonViewer({ content, docTypeId, title }) {
    return (
        <div className="space-y-6">
            <div style={{ padding: '12px 16px', background: '#fef3c7', border: '1px solid #fde68a', borderRadius: 8, fontSize: 13, color: '#92400e' }}>
                No view definition configured for <strong>{docTypeId}</strong> - displaying raw content
            </div>
            {title && (
                <div style={{ padding: 16, background: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0' }}>
                    <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
                </div>
            )}
            <div style={{ background: '#f8fafc', borderRadius: 8, padding: 16, overflow: 'auto' }} onWheel={(e) => e.stopPropagation()}>
                <pre style={{ margin: 0, fontSize: 12, color: '#374151', whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontFamily: 'monospace', lineHeight: 1.6 }}>
                    {JSON.stringify(content, null, 2)}
                </pre>
            </div>
        </div>
    );
}

/** Extract first string value from an object */
function extractText(obj) {
    if (typeof obj === 'string') return obj;
    if (typeof obj !== 'object' || obj === null) return String(obj);
    for (const v of Object.values(obj)) {
        if (typeof v === 'string' && v.length > 10) return v;
    }
    return JSON.stringify(obj);
}

/** Convert snake_case key to Title Case label */
function formatLabel(key) {
    return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}
