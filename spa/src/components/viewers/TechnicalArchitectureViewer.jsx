import { useState, useMemo } from 'react';
import RenderModelViewer from '../RenderModelViewer';
import WorkflowStudioPanel from './WorkflowStudioPanel';
import ComponentsStudioPanel from './ComponentsStudioPanel';

/**
 * TechnicalArchitectureViewer - Config-driven tabbed document viewer.
 *
 * Reads tab structure from renderModel.rendering_config.detail_html (ADR-054)
 * and routes render model sections to tabs using information_architecture binds.
 *
 * Specialized renderers:
 * - WorkflowStudioPanel for 'workflows' tab (React Flow diagrams)
 * - ComponentsStudioPanel for 'components' tab (rail navigation)
 * - SectionTabContent (RenderModelViewer) for all other tabs
 */

export default function TechnicalArchitectureViewer({
    renderModel,
    projectId,
    projectCode,
    docTypeId,
    executionId,
    docTypeName,
    onClose
}) {
    const [activeTab, setActiveTab] = useState(null);

    // Build section-to-tab mapping from rendering config + information architecture
    const { tabDefs, tabSections, isRawContentMode } = useMemo(() => {
        const detail_html = renderModel?.rendering_config?.detail_html;
        const ia = renderModel?.information_architecture;
        const sections = renderModel?.sections || [];
        const rawContent = renderModel?.raw_content;

        if (!detail_html?.tabs || !ia?.sections) {
            // Fallback: show all sections in a single overview tab
            return {
                tabDefs: [{ id: 'overview', label: 'Overview', sections: [] }],
                tabSections: { overview: sections },
                isRawContentMode: false,
            };
        }

        // Build map: IA section id -> { binds: [...], label }
        const sectionMeta = {};
        ia.sections.forEach(s => {
            sectionMeta[s.id] = { binds: s.binds || [], label: s.label || s.id };
        });

        // Detect raw content mode: sections empty but raw_content + IA config exist
        // Only enter raw content mode if rawContent has at least one IA-bound field
        if (sections.length === 0 && rawContent && typeof rawContent === 'object') {
            // Collect all bound field names across all IA sections
            const allBinds = new Set();
            ia.sections.forEach(s => (s.binds || []).forEach(b => allBinds.add(b)));
            const hasIAFields = [...allBinds].some(b => rawContent[b] !== undefined && rawContent[b] !== null);

            if (hasIAFields) {
                // Raw content mode: build tabSections as arrays of {fieldName, label, data}
                const grouped = {};
                detail_html.tabs.forEach(tab => {
                    const fields = [];
                    (tab.sections || []).forEach(sectionId => {
                        const meta = sectionMeta[sectionId];
                        if (!meta) return;
                        meta.binds.forEach(fieldName => {
                            const data = rawContent[fieldName];
                            if (data !== undefined && data !== null) {
                                fields.push({ fieldName, label: meta.label, data });
                            }
                        });
                    });
                    grouped[tab.id] = fields;
                });
                return { tabDefs: detail_html.tabs, tabSections: grouped, isRawContentMode: true };
            }

            // No IA-bound fields — extract fallback text from envelope or show raw content
            const fallbackText = rawContent.raw === true && typeof rawContent.content === 'string'
                ? rawContent.content
                : null;
            if (fallbackText) {
                const firstTab = detail_html.tabs[0]?.id || 'overview';
                const grouped = {};
                detail_html.tabs.forEach(tab => { grouped[tab.id] = []; });
                grouped[firstTab] = [{ fieldName: '_fallback', label: 'Content', data: fallbackText }];
                return { tabDefs: detail_html.tabs, tabSections: grouped, isRawContentMode: true };
            }
        }

        // Standard mode: route render model sections to tabs via field binds
        const fieldToTab = {};
        detail_html.tabs.forEach(tab => {
            (tab.sections || []).forEach(sectionId => {
                const meta = sectionMeta[sectionId];
                if (meta) {
                    meta.binds.forEach(field => { fieldToTab[field] = tab.id; });
                }
            });
        });

        const grouped = {};
        detail_html.tabs.forEach(tab => { grouped[tab.id] = []; });

        sections.forEach(section => {
            const sid = section.section_id;
            const tabId = fieldToTab[sid] || 'overview';
            if (grouped[tabId]) {
                grouped[tabId].push(section);
            } else if (grouped.overview) {
                grouped.overview.push(section);
            }
        });

        return { tabDefs: detail_html.tabs, tabSections: grouped, isRawContentMode: false };
    }, [renderModel]);

    // Default to first tab
    const effectiveTab = activeTab || (tabDefs.length > 0 ? tabDefs[0].id : 'overview');

    // Extract workflow data for WorkflowStudioPanel
    const workflows = useMemo(() => {
        if (isRawContentMode) {
            // In raw content mode, tabSections.workflows is an array of {fieldName, label, data}
            const wfFields = tabSections.workflows || [];
            const wfField = wfFields.find(f => f.fieldName === 'workflows');
            const items = wfField?.data;
            if (!Array.isArray(items) || !items.length) return [];
            return items.map((item, idx) => ({
                id: item.id || `wf-${idx}`,
                name: item.name || `Workflow ${idx + 1}`,
                description: item.description,
                trigger: item.trigger,
                nodeCount: item.nodes?.length || item.steps?.length || 0,
                rawItem: item,
            }));
        }
        // Standard mode: extract from blocks
        const wfSections = tabSections.workflows || [];
        if (!wfSections.length) return [];
        const wfSection = wfSections[0];
        if (!wfSection?.blocks) return [];
        return wfSection.blocks.map((block, idx) => ({
            id: block.block_id || `wf-${idx}`,
            name: block.data?.name || `Workflow ${idx + 1}`,
            description: block.data?.description,
            trigger: block.data?.trigger,
            nodeCount: block.data?.nodes?.length || block.data?.steps?.length || 0,
            block,
        }));
    }, [tabSections.workflows, isRawContentMode]);

    // Extract component data for ComponentsStudioPanel
    const components = useMemo(() => {
        if (isRawContentMode) {
            // In raw content mode, tabSections.components is an array of {fieldName, label, data}
            const compFields = tabSections.components || [];
            const compField = compFields.find(f => f.fieldName === 'components');
            const items = compField?.data;
            if (!Array.isArray(items) || !items.length) return [];
            return items.map((item, idx) => ({
                id: item.id || `comp-${idx}`,
                name: item.name || `Component ${idx + 1}`,
                purpose: item.purpose,
                layer: item.layer,
                mvpPhase: item.mvp_phase,
                technology: item.technology || (Array.isArray(item.technology_choices) ? item.technology_choices.join(', ') : null),
                interfaces: item.interfaces || [],
                dependencies: item.dependencies || item.depends_on_components || [],
                responsibilities: item.responsibilities || [],
                rawItem: item,
            }));
        }
        // Standard mode: extract from blocks
        const compSections = tabSections.components || [];
        if (!compSections.length) return [];
        const compSection = compSections[0];
        if (!compSection?.blocks) return [];
        return compSection.blocks.map((block, idx) => {
            const data = block.data || {};
            return {
                id: block.block_id || `comp-${idx}`,
                name: data.name || `Component ${idx + 1}`,
                purpose: data.purpose,
                layer: data.layer,
                mvpPhase: data.mvp_phase,
                technology: data.technology || (Array.isArray(data.technology_choices) ? data.technology_choices.join(', ') : null),
                interfaces: data.interfaces || [],
                dependencies: data.dependencies || data.depends_on_components || [],
                responsibilities: data.responsibilities || [],
                block,
            };
        });
    }, [tabSections.components, isRawContentMode]);

    // Build tab list with counts and disabled state
    const tabs = useMemo(() => {
        return tabDefs.map(tab => {
            const tabData = tabSections[tab.id] || [];
            const isSpecial = tab.id === 'workflows' || tab.id === 'components';
            const specialCount = tab.id === 'workflows' ? workflows.length
                : tab.id === 'components' ? components.length
                : null;

            if (isRawContentMode) {
                // In raw content mode, tabData is array of {fieldName, label, data}
                const hasContent = isSpecial ? (specialCount > 0) : tabData.length > 0;
                return {
                    id: tab.id,
                    label: tab.label,
                    count: isSpecial ? (specialCount || null) : (tabData.length || null),
                    disabled: !hasContent,
                };
            }

            // Standard mode
            const blockCount = tabData[0]?.blocks?.length || null;
            return {
                id: tab.id,
                label: tab.label,
                count: isSpecial ? (specialCount || null) : blockCount,
                disabled: tab.id !== 'overview' && !tabData.length,
            };
        });
    }, [tabDefs, tabSections, workflows, components, isRawContentMode]);

    const metadata = renderModel?.metadata || {};
    const adminUrl = executionId ? `/admin?execution=${executionId}` : '/admin';

    const displayTitle = (() => {
        const t = renderModel?.title || 'Document';
        const colonIndex = t.indexOf(': ');
        return colonIndex > -1 ? t.slice(colonIndex + 2) : t;
    })();

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

    const generatedDate = formatDate(metadata.created_at);
    const updatedDate = formatDate(metadata.updated_at);
    const lifecycleState = metadata.lifecycle_state;

    // Build filtered renderModel for a given tab
    const buildTabRenderModel = (tabId) => {
        if (!renderModel) return null;
        const sections = tabSections[tabId] || [];
        return { ...renderModel, sections };
    };

    return (
        <div className="flex flex-col h-full" style={{ background: '#ffffff' }}>
            {/* Document header */}
            <div
                className="px-5 py-3 border-b"
                style={{ background: '#f8fafc', borderColor: '#e2e8f0' }}
            >
                <div className="flex items-center gap-2 flex-wrap" style={{ marginBottom: 4 }}>
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
                    <span style={{
                        padding: '2px 8px',
                        background: '#eef2ff',
                        color: '#4f46e5',
                        fontSize: 11,
                        fontWeight: 600,
                        borderRadius: 4,
                    }}>
                        {docTypeName || docTypeId?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) || 'Document'}
                    </span>
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
                </div>
                <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: '#111827', lineHeight: 1.3 }}>
                    {displayTitle}
                </h2>
                {generatedDate && (
                    <div style={{ marginTop: 2, fontSize: 12, color: '#9ca3af' }}>
                        Generated {generatedDate}
                        {updatedDate && updatedDate !== generatedDate && (
                            <span> &middot; Updated {updatedDate}</span>
                        )}
                    </div>
                )}
            </div>

            {/* Tab bar */}
            <div
                className="flex items-center gap-1 px-4 border-b"
                style={{
                    background: '#ffffff',
                    borderColor: '#e2e8f0',
                    minHeight: 40,
                }}
            >
                {tabs.map(tab => {
                    const isActive = effectiveTab === tab.id;
                    return (
                        <button
                            key={tab.id}
                            onClick={() => !tab.disabled && setActiveTab(tab.id)}
                            disabled={tab.disabled}
                            className="relative px-4 py-2 text-sm font-medium transition-colors"
                            style={{
                                color: isActive ? '#4f46e5' : tab.disabled ? '#9ca3af' : '#64748b',
                                background: 'transparent',
                                border: 'none',
                                cursor: tab.disabled ? 'not-allowed' : 'pointer',
                            }}
                        >
                            {tab.label}
                            {tab.count !== null && (
                                <span
                                    className="ml-1.5 px-1.5 py-0.5 text-xs rounded-full"
                                    style={{
                                        background: isActive ? '#eef2ff' : '#f1f5f9',
                                        color: isActive ? '#4f46e5' : '#64748b',
                                    }}
                                >
                                    {tab.count}
                                </span>
                            )}
                            {isActive && (
                                <div
                                    className="absolute bottom-0 left-0 right-0 h-0.5"
                                    style={{ background: '#4f46e5' }}
                                />
                            )}
                        </button>
                    );
                })}
            </div>

            {/* Tab content - key forces remount so sections start expanded */}
            <div
                key={effectiveTab}
                className="flex-1 overflow-hidden"
                style={{ minHeight: 0 }}
            >
                {effectiveTab === 'workflows' && workflows.length > 0 ? (
                    <WorkflowStudioPanel workflows={workflows} />
                ) : effectiveTab === 'components' && components.length > 0 ? (
                    <ComponentsStudioPanel components={components} />
                ) : isRawContentMode ? (
                    <RawContentTabContent fields={tabSections[effectiveTab] || []} />
                ) : (
                    <SectionTabContent
                        renderModel={buildTabRenderModel(effectiveTab)}
                        sections={tabSections[effectiveTab] || []}
                    />
                )}
            </div>
        </div>
    );
}

/** Generic tab content that renders sections via RenderModelViewer */
function SectionTabContent({ renderModel, sections }) {
    return (
        <div
            className="h-full overflow-y-auto p-6"
            onWheel={(e) => e.stopPropagation()}
        >
            {renderModel && sections.length > 0 ? (
                <RenderModelViewer
                    renderModel={renderModel}
                    variant="full"
                    hideHeader={true}
                />
            ) : (
                <div className="text-center py-12 text-gray-500">
                    No content available for this tab
                </div>
            )}
        </div>
    );
}

/** Raw content tab - renders fields pulled from raw_content via IA binds */
function RawContentTabContent({ fields }) {
    if (!fields || fields.length === 0) {
        return (
            <div className="h-full overflow-y-auto p-6" onWheel={(e) => e.stopPropagation()}>
                <div className="text-center py-12 text-gray-500">
                    No content available for this tab
                </div>
            </div>
        );
    }
    return (
        <div className="h-full overflow-y-auto p-6 space-y-6" onWheel={(e) => e.stopPropagation()}>
            {fields.map((field, i) => (
                <div key={field.fieldName || i} style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8 }}>
                    <div className="flex items-center gap-2" style={{ padding: '12px 16px', borderBottom: '1px solid #e2e8f0' }}>
                        <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: '#1f2937' }}>
                            {field.label || formatFieldLabel(field.fieldName)}
                        </h3>
                        {Array.isArray(field.data) && (
                            <span style={{ marginLeft: 'auto', fontSize: 12, color: '#9ca3af' }}>
                                {field.data.length}
                            </span>
                        )}
                    </div>
                    <div style={{ padding: 16 }}>
                        <RawFieldRenderer data={field.data} fieldName={field.fieldName} />
                    </div>
                </div>
            ))}
        </div>
    );
}

/** Dispatches rendering by data type: strings, arrays, objects, fallback JSON */
function RawFieldRenderer({ data, fieldName }) {
    if (data === null || data === undefined) {
        return <span style={{ color: '#9ca3af', fontSize: 13 }}>No data</span>;
    }
    if (typeof data === 'string') {
        return <p style={{ fontSize: 14, color: '#1f2937', margin: 0, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{data}</p>;
    }
    if (Array.isArray(data)) {
        if (data.length === 0) {
            return <span style={{ color: '#9ca3af', fontSize: 13 }}>Empty list</span>;
        }
        return (
            <ul style={{ margin: 0, padding: 0, listStyle: 'none' }} className="space-y-2">
                {data.map((item, i) => (
                    <li key={typeof item === 'object' ? (item?.id || i) : i} className="flex items-start gap-2" style={{ fontSize: 14, color: '#374151' }}>
                        <span style={{ color: '#6b7280', marginTop: 2, flexShrink: 0, fontSize: 12 }}>{'\u2022'}</span>
                        <div style={{ flex: 1 }}>
                            {typeof item === 'string' ? (
                                <span>{item}</span>
                            ) : typeof item === 'object' && item !== null ? (
                                <RawStructuredItem item={item} />
                            ) : (
                                <span>{String(item)}</span>
                            )}
                        </div>
                    </li>
                ))}
            </ul>
        );
    }
    if (typeof data === 'object') {
        return (
            <div className="space-y-3">
                {Object.entries(data).map(([k, v]) => (
                    <div key={k} style={{ borderLeft: '3px solid #e2e8f0', paddingLeft: 12 }}>
                        <div style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
                            {formatFieldLabel(k)}
                        </div>
                        <div style={{ fontSize: 14, color: '#1f2937' }}>
                            {typeof v === 'string' ? v : typeof v === 'object' ? JSON.stringify(v, null, 2) : String(v)}
                        </div>
                    </div>
                ))}
            </div>
        );
    }
    // Fallback
    return (
        <pre style={{ margin: 0, fontSize: 12, color: '#374151', whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
            {JSON.stringify(data, null, 2)}
        </pre>
    );
}

/** Smart field extraction for structured items (array-of-objects) */
function RawStructuredItem({ item }) {
    // Detect primary text field
    const textKeys = ['constraint', 'assumption', 'guardrail', 'recommendation', 'description',
                      'question', 'text', 'statement', 'name', 'title', 'problem_understanding',
                      'architectural_intent', 'proposed_system_shape'];
    const textKey = textKeys.find(k => item[k] && typeof item[k] === 'string');
    const text = textKey ? item[textKey] : null;

    // Badge-worthy metadata
    const id = item.id;
    const confidence = item.confidence;
    const likelihood = item.likelihood;
    const constraintType = item.constraint_type;

    // Secondary fields
    const why = item.why_it_matters || item.why_early;
    const impact = item.impact_on_planning || item.impact_if_unresolved || item.impact;
    const mitigation = item.mitigation_direction;
    const recommendation = item.recommendation_direction;
    const validation = item.validation_approach;

    if (!text) {
        // No recognizable primary field: show all as inline key-value pairs
        return (
            <span style={{ fontSize: 13, color: '#374151' }}>
                {Object.entries(item).map(([k, v], i) => (
                    <span key={k}>
                        {i > 0 && ' \u00B7 '}
                        <span style={{ fontWeight: 500 }}>{formatFieldLabel(k)}:</span>{' '}
                        {typeof v === 'string' ? v : JSON.stringify(v)}
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
                {constraintType && (
                    <span style={{ fontSize: 11, padding: '1px 6px', background: '#f3f4f6', borderRadius: 4, color: '#6b7280' }}>{constraintType}</span>
                )}
                {confidence && (
                    <span style={{
                        fontSize: 11, padding: '1px 6px', borderRadius: 4, fontWeight: 600,
                        background: confidence === 'high' ? '#dcfce7' : confidence === 'medium' ? '#fef3c7' : '#fee2e2',
                        color: confidence === 'high' ? '#166534' : confidence === 'medium' ? '#92400e' : '#991b1b',
                    }}>{confidence}</span>
                )}
                {likelihood && (
                    <span style={{ fontSize: 11, padding: '1px 6px', background: '#fee2e2', borderRadius: 4, color: '#991b1b' }}>
                        {likelihood}{item.impact ? `/${item.impact}` : ''}
                    </span>
                )}
            </div>
            {validation && <p style={{ fontSize: 12, color: '#6b7280', margin: '2px 0 0' }}>Validation: {validation}</p>}
            {why && <p style={{ fontSize: 12, color: '#6b7280', margin: '2px 0 0' }}>Why: {why}</p>}
            {impact && typeof impact === 'string' && <p style={{ fontSize: 12, color: '#6b7280', margin: '2px 0 0' }}>Impact: {impact}</p>}
            {mitigation && <p style={{ fontSize: 12, color: '#6b7280', margin: '2px 0 0' }}>Mitigation: {mitigation}</p>}
            {recommendation && <p style={{ fontSize: 12, color: '#059669', margin: '2px 0 0' }}>Recommendation: {recommendation}</p>}
        </div>
    );
}

/** Convert snake_case field name to Title Case label */
function formatFieldLabel(key) {
    return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}
