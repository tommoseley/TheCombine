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
    onClose
}) {
    const [activeTab, setActiveTab] = useState(null);

    // Build section-to-tab mapping from rendering config + information architecture
    const { tabDefs, tabSections } = useMemo(() => {
        const detail_html = renderModel?.rendering_config?.detail_html;
        const ia = renderModel?.information_architecture;

        if (!detail_html?.tabs || !ia?.sections) {
            // Fallback: show all sections in a single overview tab
            return {
                tabDefs: [{ id: 'overview', label: 'Overview', sections: [] }],
                tabSections: { overview: renderModel?.sections || [] },
            };
        }

        // Build map: IA section id -> set of bound schema fields
        const sectionBinds = {};
        ia.sections.forEach(s => {
            sectionBinds[s.id] = new Set(s.binds || []);
        });

        // Build map: schema field name -> tab id
        const fieldToTab = {};
        detail_html.tabs.forEach(tab => {
            (tab.sections || []).forEach(sectionId => {
                const binds = sectionBinds[sectionId];
                if (binds) {
                    binds.forEach(field => { fieldToTab[field] = tab.id; });
                }
            });
        });

        // Route each render model section to its tab
        const grouped = {};
        detail_html.tabs.forEach(tab => { grouped[tab.id] = []; });

        (renderModel?.sections || []).forEach(section => {
            const sid = section.section_id;
            const tabId = fieldToTab[sid] || 'overview';
            if (grouped[tabId]) {
                grouped[tabId].push(section);
            } else if (grouped.overview) {
                grouped.overview.push(section);
            }
        });

        return { tabDefs: detail_html.tabs, tabSections: grouped };
    }, [renderModel]);

    // Default to first tab
    const effectiveTab = activeTab || (tabDefs.length > 0 ? tabDefs[0].id : 'overview');

    // Extract workflow data from blocks for WorkflowStudioPanel
    const workflows = useMemo(() => {
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
    }, [tabSections.workflows]);

    // Extract component data from blocks for ComponentsStudioPanel
    const components = useMemo(() => {
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
    }, [tabSections.components]);

    // Build tab list with counts and disabled state
    const tabs = useMemo(() => {
        return tabDefs.map(tab => {
            const sections = tabSections[tab.id] || [];
            const blockCount = sections[0]?.blocks?.length || null;
            const isSpecial = tab.id === 'workflows' || tab.id === 'components';
            const specialCount = tab.id === 'workflows' ? workflows.length
                : tab.id === 'components' ? components.length
                : null;
            return {
                id: tab.id,
                label: tab.label,
                count: isSpecial ? (specialCount || null) : blockCount,
                disabled: tab.id !== 'overview' && !sections.length,
            };
        });
    }, [tabDefs, tabSections, workflows, components]);

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
                        Technical Architecture
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
