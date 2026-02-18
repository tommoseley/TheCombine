import { useState, useMemo } from 'react';
import RenderModelViewer from '../RenderModelViewer';
import WorkflowStudioPanel from './WorkflowStudioPanel';
import ComponentsStudioPanel from './ComponentsStudioPanel';

/**
 * TechnicalArchitectureViewer - Tabbed document viewer for Technical Architecture documents.
 *
 * Tabs:
 * - Overview: Summary, key decisions, constraints, assumptions, etc.
 * - Components: System components with vertical rail navigation
 * - Workflows: Full Workflow Studio with React Flow diagrams
 * - Data Models: Entity definitions with fields tables and relationships
 * - APIs: Interface definitions with endpoint details
 * - Quality: Quality attributes by category
 */

// Section IDs that route to each tab
const DATA_MODEL_IDS = new Set(['data_model', 'data_models']);
const INTERFACE_IDS = new Set(['interfaces', 'api_interfaces']);
const QUALITY_IDS = new Set(['quality_attributes']);
const WORKFLOW_IDS = new Set(['workflows']);
const COMPONENT_IDS = new Set(['components']);

export default function TechnicalArchitectureViewer({
    renderModel,
    projectId,
    projectCode,
    docTypeId,
    executionId,
    onClose
}) {
    const [activeTab, setActiveTab] = useState('overview');

    // Categorize sections into tabs
    const categorized = useMemo(() => {
        const result = {
            workflows: [],
            components: [],
            dataModels: [],
            interfaces: [],
            quality: [],
            overview: [],
        };
        if (!renderModel?.sections) return result;

        renderModel.sections.forEach(section => {
            const sid = section.section_id;
            if (WORKFLOW_IDS.has(sid)) result.workflows.push(section);
            else if (COMPONENT_IDS.has(sid)) result.components.push(section);
            else if (DATA_MODEL_IDS.has(sid)) result.dataModels.push(section);
            else if (INTERFACE_IDS.has(sid)) result.interfaces.push(section);
            else if (QUALITY_IDS.has(sid)) result.quality.push(section);
            else result.overview.push(section);
        });
        return result;
    }, [renderModel?.sections]);

    // Extract workflow data from blocks
    const workflows = useMemo(() => {
        if (!categorized.workflows.length) return [];
        const wfSection = categorized.workflows[0];
        if (!wfSection?.blocks) return [];
        return wfSection.blocks.map((block, idx) => ({
            id: block.block_id || `wf-${idx}`,
            name: block.data?.name || `Workflow ${idx + 1}`,
            description: block.data?.description,
            trigger: block.data?.trigger,
            nodeCount: block.data?.nodes?.length || block.data?.steps?.length || 0,
            block,
        }));
    }, [categorized.workflows]);

    // Extract component data from blocks
    const components = useMemo(() => {
        if (!categorized.components.length) return [];
        const compSection = categorized.components[0];
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
    }, [categorized.components]);

    // Build filtered renderModels for RenderModelViewer-based tabs
    const overviewRenderModel = useMemo(() => {
        if (!renderModel) return null;
        return { ...renderModel, sections: categorized.overview };
    }, [renderModel, categorized.overview]);

    const dataModelRenderModel = useMemo(() => {
        if (!renderModel) return null;
        return { ...renderModel, sections: categorized.dataModels };
    }, [renderModel, categorized.dataModels]);

    const interfaceRenderModel = useMemo(() => {
        if (!renderModel) return null;
        return { ...renderModel, sections: categorized.interfaces };
    }, [renderModel, categorized.interfaces]);

    const qualityRenderModel = useMemo(() => {
        if (!renderModel) return null;
        return { ...renderModel, sections: categorized.quality };
    }, [renderModel, categorized.quality]);

    // Tab definitions with counts and disabled state
    const tabs = useMemo(() => [
        { id: 'overview', label: 'Overview', count: null, disabled: false },
        { id: 'components', label: 'Components', count: components.length || null, disabled: !components.length },
        { id: 'workflows', label: 'Workflows', count: workflows.length || null, disabled: !workflows.length },
        { id: 'dataModels', label: 'Data Models', count: categorized.dataModels[0]?.blocks?.length || null, disabled: !categorized.dataModels.length },
        { id: 'interfaces', label: 'APIs', count: categorized.interfaces[0]?.blocks?.length || null, disabled: !categorized.interfaces.length },
        { id: 'quality', label: 'Quality', count: categorized.quality[0]?.blocks?.length || null, disabled: !categorized.quality.length },
    ], [components, workflows, categorized]);

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
                    const isActive = activeTab === tab.id;
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
                key={activeTab}
                className="flex-1 overflow-hidden"
                style={{ minHeight: 0 }}
            >
                {activeTab === 'workflows' && workflows.length > 0 ? (
                    <WorkflowStudioPanel workflows={workflows} />
                ) : activeTab === 'components' && components.length > 0 ? (
                    <ComponentsStudioPanel components={components} />
                ) : activeTab === 'dataModels' ? (
                    <SectionTabContent renderModel={dataModelRenderModel} sections={categorized.dataModels} />
                ) : activeTab === 'interfaces' ? (
                    <SectionTabContent renderModel={interfaceRenderModel} sections={categorized.interfaces} />
                ) : activeTab === 'quality' ? (
                    <SectionTabContent renderModel={qualityRenderModel} sections={categorized.quality} />
                ) : (
                    <SectionTabContent renderModel={overviewRenderModel} sections={categorized.overview} />
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
