import { useState, useMemo } from 'react';
import RenderModelViewer from '../RenderModelViewer';
import WorkflowStudioPanel from './WorkflowStudioPanel';
import ComponentsStudioPanel from './ComponentsStudioPanel';

/**
 * TechnicalArchitectureViewer - Tabbed document viewer for Technical Architecture documents.
 * 
 * Tabs:
 * - Overview: Everything except components and workflows
 * - Components: System components with vertical rail navigation
 * - Workflows: Full Workflow Studio with vertical rail navigation
 * 
 * Per WS-WORKFLOW-STUDIO-001
 */

const TABS = [
    { id: 'overview', label: 'Overview' },
    { id: 'components', label: 'Components' },
    { id: 'workflows', label: 'Workflows' },
];

export default function TechnicalArchitectureViewer({ 
    renderModel, 
    projectCode,
    onClose 
}) {
    const [activeTab, setActiveTab] = useState('overview');

    // Separate workflows and components from other sections
    const { workflowSections, componentSections, overviewSections } = useMemo(() => {
        if (!renderModel?.sections) return { workflowSections: [], componentSections: [], overviewSections: [] };
        
        const workflows = [];
        const components = [];
        const overview = [];
        
        renderModel.sections.forEach(section => {
            if (section.section_id === 'workflows' || section.title === 'Workflows') {
                workflows.push(section);
            } else if (section.section_id === 'components' || section.title === 'Components') {
                components.push(section);
            } else {
                // Everything else goes to overview
                overview.push(section);
            }
        });
        
        return { workflowSections: workflows, componentSections: components, overviewSections: overview };
    }, [renderModel?.sections]);

    // Extract workflow data from blocks
    const workflows = useMemo(() => {
        if (!workflowSections.length) return [];
        
        const wfSection = workflowSections[0];
        if (!wfSection?.blocks) return [];
        
        return wfSection.blocks.map((block, idx) => ({
            id: block.block_id || `wf-${idx}`,
            name: block.data?.name || `Workflow ${idx + 1}`,
            description: block.data?.description,
            trigger: block.data?.trigger,
            nodeCount: block.data?.nodes?.length || block.data?.steps?.length || 0,
            block,
        }));
    }, [workflowSections]);

    // Extract component data from blocks
    const components = useMemo(() => {
        if (!componentSections.length) return [];
        
        const compSection = componentSections[0];
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
    }, [componentSections]);

    // Build a filtered renderModel for overview (everything except components/workflows)
    const overviewRenderModel = useMemo(() => {
        if (!renderModel) return null;
        return {
            ...renderModel,
            sections: overviewSections,
        };
    }, [renderModel, overviewSections]);

    const hasWorkflows = workflows.length > 0;
    const hasComponents = components.length > 0;

    return (
        <div className="flex flex-col h-full" style={{ background: '#ffffff' }}>
            {/* Tab bar */}
            <div 
                className="flex items-center gap-1 px-4 border-b"
                style={{ 
                    background: '#f8fafc', 
                    borderColor: '#e2e8f0',
                    minHeight: 44,
                }}
            >
                {/* Project code badge (left side) */}
                {projectCode && (
                    <span
                        style={{
                            padding: '2px 8px',
                            background: '#10b981',
                            color: 'white',
                            fontSize: 11,
                            fontWeight: 600,
                            borderRadius: 4,
                            letterSpacing: '0.05em',
                            marginRight: 12,
                        }}
                    >
                        {projectCode}
                    </span>
                )}
                
                {TABS.map(tab => {
                    const isActive = activeTab === tab.id;
                    const isWorkflowsDisabled = tab.id === 'workflows' && !hasWorkflows;
                    const isComponentsDisabled = tab.id === 'components' && !hasComponents;
                    const isDisabled = isWorkflowsDisabled || isComponentsDisabled;
                    
                    // Get count for badge
                    let count = null;
                    if (tab.id === 'workflows' && hasWorkflows) count = workflows.length;
                    if (tab.id === 'components' && hasComponents) count = components.length;
                    
                    return (
                        <button
                            key={tab.id}
                            onClick={() => !isDisabled && setActiveTab(tab.id)}
                            disabled={isDisabled}
                            className="relative px-4 py-2 text-sm font-medium transition-colors"
                            style={{
                                color: isActive ? '#4f46e5' : isDisabled ? '#9ca3af' : '#64748b',
                                background: 'transparent',
                                border: 'none',
                                cursor: isDisabled ? 'not-allowed' : 'pointer',
                            }}
                        >
                            {tab.label}
                            {count !== null && (
                                <span 
                                    className="ml-1.5 px-1.5 py-0.5 text-xs rounded-full"
                                    style={{ 
                                        background: isActive ? '#eef2ff' : '#f1f5f9',
                                        color: isActive ? '#4f46e5' : '#64748b',
                                    }}
                                >
                                    {count}
                                </span>
                            )}
                            {/* Active indicator */}
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

            {/* Tab content */}
            <div 
                className="flex-1 overflow-hidden"
                style={{ minHeight: 0 }}
            >
                {activeTab === 'workflows' && hasWorkflows ? (
                    <WorkflowStudioPanel workflows={workflows} />
                ) : activeTab === 'components' && hasComponents ? (
                    <ComponentsStudioPanel components={components} />
                ) : (
                    <div 
                        className="h-full overflow-y-auto p-6"
                        onWheel={(e) => e.stopPropagation()}
                    >
                        {overviewRenderModel && overviewSections.length > 0 ? (
                            <RenderModelViewer 
                                renderModel={overviewRenderModel} 
                                variant="full"
                                hideHeader={true}
                            />
                        ) : (
                            <div className="text-center py-12 text-gray-500">
                                No content available for this tab
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}