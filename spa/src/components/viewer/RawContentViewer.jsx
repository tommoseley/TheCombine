import React from 'react';
import SectionHeader from '../common/SectionHeader';
import { extractText, formatLabel } from '../../utils/documentViewerUtils';

/**
 * Raw content viewer - renders structured content intelligently.
 * Detects arrays of objects and renders fields; falls back to JSON for unknown shapes.
 */
export default function RawContentViewer({ content, docTypeId }) {
    if (!content) {
        return <p style={{ color: 'var(--text-muted)' }}>No content available</p>;
    }

    const title = content.project_name || content.title || content.name;

    // Section configuration: map known keys to display config
    const SECTION_CONFIG = {
        preliminary_summary: { title: 'Summary', icon: 'S', color: '#7c3aed', render: 'summary' },
        stakeholder_questions: { title: 'Stakeholder Questions', icon: '?', color: '#dc2626', render: 'questions' },
        unknowns: { title: 'Unknowns to Resolve', icon: '?', color: '#d97706' },
        early_decision_points: { title: 'Early Decision Points', icon: 'D', color: '#7c3aed' },
        risks: { title: 'Risks', icon: '!', color: '#dc2626' },
        known_constraints: { title: 'Known Constraints', icon: 'C', color: 'var(--text-muted)' },
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
                                config={{ title: formatLabel(key), icon: '#', color: 'var(--text-muted)' }}
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
            <details style={{ borderRadius: 8, border: '1px solid var(--border-node)' }}>
                <summary
                    style={{
                        padding: '12px 16px',
                        cursor: 'pointer',
                        fontSize: 13,
                        fontWeight: 600,
                        color: 'var(--text-muted)',
                        background: 'var(--bg-panel)',
                        borderRadius: 8,
                    }}
                >
                    Raw Data (JSON)
                </summary>
                <div style={{ padding: 16, overflow: 'auto' }}>
                    <pre style={{ margin: 0, fontSize: 11, color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontFamily: 'monospace', lineHeight: 1.5 }}>
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
        <div style={{ background: 'var(--bg-node)', border: '1px solid var(--border-node)', borderRadius: 8 }}>
            <SectionHeader config={config} />
            <div style={{ padding: 16 }} className="space-y-3">
                {fields.map(f => data[f.key] ? (
                    <div key={f.key} style={{ borderLeft: `3px solid ${config.color}`, paddingLeft: 12 }}>
                        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>{f.label}</div>
                        <p style={{ fontSize: 14, color: 'var(--text-primary)', margin: 0, lineHeight: 1.6 }}>{data[f.key]}</p>
                    </div>
                ) : null)}
                {/* Render any other fields */}
                {Object.entries(data)
                    .filter(([k]) => !fields.some(f => f.key === k))
                    .map(([k, v]) => typeof v === 'string' ? (
                        <div key={k} style={{ borderLeft: `3px solid ${config.color}`, paddingLeft: 12 }}>
                            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>{formatLabel(k)}</div>
                            <p style={{ fontSize: 14, color: 'var(--text-primary)', margin: 0, lineHeight: 1.6 }}>{v}</p>
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
        <div style={{ background: 'var(--bg-node)', border: '1px solid var(--border-node)', borderRadius: 8 }}>
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
                        {blocking.length > 0 && <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase' }}>Non-blocking</div>}
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
                {q.id && <span style={{ fontFamily: 'monospace', fontSize: 11, color: 'var(--text-dim)' }}>{q.id}</span>}
                {q.directed_to && <span style={{ fontSize: 11, padding: '1px 6px', background: 'var(--bg-button)', borderRadius: 4, color: 'var(--text-muted)' }}>{q.directed_to.replace(/_/g, ' ')}</span>}
            </div>
            <p style={{ fontSize: 14, color: 'var(--text-primary)', margin: 0, fontWeight: 500 }}>{q.question || q.text || extractText(q)}</p>
            {q.notes && <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '4px 0 0' }}>{q.notes}</p>}
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
        <div style={{ background: 'var(--bg-node)', border: '1px solid var(--border-node)', borderRadius: 8 }}>
            <SectionHeader config={config} count={data.length} />
            <div style={{ padding: 16 }} className="space-y-3">
                {data.map((c, i) => {
                    const kc = kindColors[c.constraint_kind] || kindColors.selection;
                    return (
                        <div key={c.question_id || i} style={{ borderLeft: `3px solid ${config.color}`, paddingLeft: 12, marginBottom: 8 }}>
                            <div className="flex items-center gap-2" style={{ marginBottom: 2, flexWrap: 'wrap' }}>
                                {c.question_id && <span style={{ fontFamily: 'monospace', fontSize: 11, color: 'var(--text-dim)' }}>{c.question_id}</span>}
                                {c.binding && <span style={{ fontSize: 10, padding: '1px 5px', background: '#dbeafe', color: '#1e40af', borderRadius: 4, fontWeight: 600 }}>BINDING</span>}
                                {c.constraint_kind && <span style={{ fontSize: 10, padding: '1px 5px', background: kc.bg, color: kc.color, borderRadius: 4 }}>{c.constraint_kind}</span>}
                                {c.binding_source && <span style={{ fontSize: 10, color: 'var(--text-dim)' }}>via {c.binding_source}</span>}
                            </div>
                            <p style={{ fontSize: 14, color: 'var(--text-primary)', margin: '2px 0', fontWeight: 500 }}>{c.question}</p>
                            {c.why_it_matters && (
                                <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '4px 0', fontStyle: 'italic' }}>{c.why_it_matters}</p>
                            )}
                            {c.answer && (
                                <div style={{ marginTop: 4, display: 'flex', alignItems: 'baseline', gap: 6 }}>
                                    <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Answer:</span>
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
export function PgcContextSection({ pgcContext }) {
    const { clarifications } = pgcContext;
    const binding = clarifications.filter(c => c.binding);
    const informational = clarifications.filter(c => !c.binding);

    return (
        <div style={{ background: 'var(--bg-node)', border: '1px solid var(--border-node)', borderRadius: 8, marginTop: 24 }}>
            <div className="flex items-center gap-2" style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-node)' }}>
                <span style={{
                    width: 24, height: 24, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 12, fontWeight: 700, background: '#7c3aed15', color: '#7c3aed',
                }}>Q</span>
                <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: 'var(--text-primary)' }}>Pre-Generation Clarifications</h3>
                <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--text-dim)' }}>{clarifications.length}</span>
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
                            <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 8, marginTop: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
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
                    <span style={{ fontFamily: 'monospace', fontSize: 11, color: 'var(--text-dim)' }}>{item.question_id}</span>
                )}
                {item.binding && (
                    <span style={{ fontSize: 10, padding: '1px 5px', background: '#dbeafe', color: '#1e40af', borderRadius: 4, fontWeight: 600 }}>BINDING</span>
                )}
                {item.constraint_kind && (
                    <span style={{ fontSize: 10, padding: '1px 5px', background: kc.bg, color: kc.color, borderRadius: 4 }}>{item.constraint_kind}</span>
                )}
                {item.binding_source && (
                    <span style={{ fontSize: 10, color: 'var(--text-dim)' }}>via {item.binding_source}</span>
                )}
            </div>
            <p style={{ fontSize: 14, color: 'var(--text-primary)', margin: '2px 0', fontWeight: 500 }}>{item.question}</p>
            {item.why_it_matters && (
                <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '4px 0', fontStyle: 'italic' }}>
                    {item.why_it_matters}
                </p>
            )}
            {item.answer && (
                <div style={{ marginTop: 4, display: 'flex', alignItems: 'baseline', gap: 6 }}>
                    <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Answer:</span>
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
        <div style={{ background: 'var(--bg-node)', border: '1px solid var(--border-node)', borderRadius: 8 }}>
            <SectionHeader config={config} count={data.length} />
            <div style={{ padding: 16 }}>
                <ul style={{ margin: 0, padding: 0, listStyle: 'none' }} className="space-y-2">
                    {data.map((item, i) => (
                        <li key={typeof item === 'object' ? (item.id || i) : i} className="flex items-start gap-2" style={{ fontSize: 14, color: 'var(--text-secondary)' }}>
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
            <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
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
                {id && <span style={{ fontFamily: 'monospace', fontSize: 11, color: 'var(--text-dim)' }}>{id}</span>}
                <span style={{ fontWeight: 500 }}>{text}</span>
                {constraintType && <span style={{ fontSize: 11, padding: '1px 6px', background: 'var(--bg-button)', borderRadius: 4, color: 'var(--text-muted)' }}>{constraintType}</span>}
                {confidence && (
                    <span style={{
                        fontSize: 11, padding: '1px 6px', borderRadius: 4, fontWeight: 600,
                        background: confidence === 'high' ? '#dcfce7' : confidence === 'medium' ? '#fef3c7' : '#fee2e2',
                        color: confidence === 'high' ? '#166534' : confidence === 'medium' ? '#92400e' : '#991b1b',
                    }}>{confidence}</span>
                )}
                {likelihood && <span style={{ fontSize: 11, padding: '1px 6px', background: '#fee2e2', borderRadius: 4, color: '#991b1b' }}>{likelihood}/{item.impact || '?'}</span>}
            </div>
            {validationApproach && <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '2px 0 0' }}>Validation: {validationApproach}</p>}
            {why && <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '2px 0 0' }}>Why: {why}</p>}
            {impact && <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '2px 0 0' }}>Impact: {impact}</p>}
            {mitigation && <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '2px 0 0' }}>Mitigation: {mitigation}</p>}
            {recommendation && <p style={{ fontSize: 12, color: '#059669', margin: '2px 0 0' }}>Recommendation: {recommendation}</p>}
        </div>
    );
}

/** Render an object as a labeled section */
function ObjectSection({ data, label }) {
    return (
        <div style={{ background: 'var(--bg-node)', border: '1px solid var(--border-node)', borderRadius: 8 }}>
            <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-node)', fontWeight: 600, fontSize: 14, color: 'var(--text-primary)' }}>{label}</div>
            <div style={{ padding: 16 }}>
                {Object.entries(data).map(([k, v]) => (
                    <div key={k} style={{ marginBottom: 12 }}>
                        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>{formatLabel(k)}</div>
                        <ObjectFieldValue value={v} />
                    </div>
                ))}
            </div>
        </div>
    );
}

/** Render a single field value inside an ObjectSection */
function ObjectFieldValue({ value }) {
    if (value === null || value === undefined) {
        return <span style={{ color: 'var(--text-dim)', fontSize: 13 }}>—</span>;
    }
    if (typeof value === 'boolean') {
        return <span style={{ fontSize: 14, color: 'var(--text-primary)' }}>{value ? 'Yes' : 'No'}</span>;
    }
    if (typeof value === 'string') {
        return <p style={{ fontSize: 14, color: 'var(--text-primary)', margin: 0, lineHeight: 1.6 }}>{value}</p>;
    }
    if (Array.isArray(value)) {
        if (value.length === 0) {
            return <span style={{ color: 'var(--text-dim)', fontSize: 13 }}>None</span>;
        }
        return (
            <ul style={{ margin: 0, padding: 0, listStyle: 'none' }} className="space-y-1">
                {value.map((item, i) => (
                    <li key={i} className="flex items-start gap-2" style={{ fontSize: 14, color: 'var(--text-secondary)' }}>
                        <span style={{ color: 'var(--text-muted)', marginTop: 2, flexShrink: 0, fontSize: 12 }}>{'\u2022'}</span>
                        <span style={{ flex: 1 }}>
                            {typeof item === 'string' ? item
                                : typeof item === 'object' && item !== null ? extractText(item)
                                : String(item)}
                        </span>
                    </li>
                ))}
            </ul>
        );
    }
    if (typeof value === 'object') {
        return (
            <div className="space-y-2" style={{ paddingLeft: 8 }}>
                {Object.entries(value).map(([k, v]) => (
                    <div key={k}>
                        <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-muted)' }}>{formatLabel(k)}: </span>
                        <span style={{ fontSize: 13, color: 'var(--text-primary)' }}>
                            {typeof v === 'string' ? v : JSON.stringify(v)}
                        </span>
                    </div>
                ))}
            </div>
        );
    }
    return <span style={{ fontSize: 14, color: 'var(--text-primary)' }}>{String(value)}</span>;
}

/** Fallback: pure JSON viewer for truly unstructured content */
function FallbackJsonViewer({ content, docTypeId, title }) {
    return (
        <div className="space-y-6">
            <div style={{ padding: '12px 16px', background: '#fef3c7', border: '1px solid #fde68a', borderRadius: 8, fontSize: 13, color: '#92400e' }}>
                No view definition configured for <strong>{docTypeId}</strong> - displaying raw content
            </div>
            {title && (
                <div style={{ padding: 16, background: 'var(--bg-panel)', borderRadius: 8, border: '1px solid var(--border-node)' }}>
                    <h3 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>{title}</h3>
                </div>
            )}
            <div style={{ background: 'var(--bg-panel)', borderRadius: 8, padding: 16, overflow: 'auto' }} onWheel={(e) => e.stopPropagation()}>
                <pre style={{ margin: 0, fontSize: 12, color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontFamily: 'monospace', lineHeight: 1.6 }}>
                    {JSON.stringify(content, null, 2)}
                </pre>
            </div>
        </div>
    );
}
