import { useState, useEffect } from 'react';
import { api } from '../api/client';
import RenderModelViewer from './RenderModelViewer';

/**
 * Full-screen document viewer modal
 * Displays complete document content with proper formatting
 */
export default function FullDocumentViewer({ projectId, docTypeId, onClose }) {
    const [document, setDocument] = useState(null);
    const [renderModel, setRenderModel] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        async function fetchDocument() {
            try {
                setLoading(true);
                setError(null);

                // Try to fetch RenderModel first (data-driven display)
                try {
                    const rm = await api.getDocumentRenderModel(projectId, docTypeId);
                    if (rm && rm.sections && rm.sections.length > 0) {
                        setRenderModel(rm);
                        setDocument(null);
                        return;
                    }
                    // If RenderModel has fallback flag, use raw content
                    if (rm?.metadata?.fallback) {
                        setRenderModel(rm);
                        setDocument(null);
                        return;
                    }
                } catch (rmErr) {
                    console.log('RenderModel not available, falling back to raw document:', rmErr.message);
                }

                // Fall back to raw document content
                const doc = await api.getDocument(projectId, docTypeId);
                setDocument(doc);
                setRenderModel(null);
            } catch (err) {
                setError(err.message);
                console.error('Failed to fetch document:', err);
            } finally {
                setLoading(false);
            }
        }
        fetchDocument();
    }, [projectId, docTypeId]);

    // Close on Escape key
    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.key === 'Escape') onClose();
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [onClose]);

    // Don't render until content is loaded
    if (loading) {
        return null;
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
                {/* Header */}
                <div
                    className="sticky top-0 px-6 py-4 border-b flex items-center justify-between"
                    style={{ background: '#f8fafc', borderColor: '#e2e8f0' }}
                >
                    <div>
                        <h2 className="text-xl font-bold text-gray-900">
                            {renderModel?.title || document?.title || formatDocType(docTypeId)}
                        </h2>
                        {(document?.updated_at || renderModel?.subtitle) && (
                            <p className="text-sm text-gray-500 mt-1">
                                {renderModel?.subtitle || `Last updated: ${formatDate(document?.updated_at)}`}
                            </p>
                        )}
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-lg hover:bg-gray-200 transition-colors"
                    >
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M18 6L6 18M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Content */}
                <div className="overflow-y-auto p-6" style={{ maxHeight: 'calc(90vh - 80px)' }}>
                    {error && (
                        <div className="text-center py-12">
                            <p className="text-red-500">{error}</p>
                        </div>
                    )}

                    {renderModel && (
                        <RenderModelViewer renderModel={renderModel} variant="full" />
                    )}

                    {document && !renderModel && (
                        <DocumentContent docTypeId={docTypeId} content={document.content} />
                    )}
                </div>
            </div>
        </div>
    );
}

/**
 * Render document content based on type
 */
function DocumentContent({ docTypeId, content }) {
    if (!content) {
        return <p className="text-gray-500">No content available</p>;
    }

    switch (docTypeId) {
        case 'concierge_intake':
            return <ConciergeIntakeContent content={content} />;
        case 'project_discovery':
            return <ProjectDiscoveryContent content={content} />;
        default:
            return <GenericDocumentContent content={content} />;
    }
}

/**
 * Concierge Intake document renderer
 */
function ConciergeIntakeContent({ content }) {
    // Handle both old format (project_name, summary.description) and new format (captured_intent)
    const projectName = content.project_name;
    const description = content.summary?.description || content.captured_intent || '';
    const userStatement = content.summary?.user_statement || content.conversation_summary || '';
    const projectType = content.project_type;
    const constraints = content.constraints;
    const openGaps = content.open_gaps || {
        questions: content.known_unknowns || [],
    };
    const outcome = content.outcome || {
        status: content.gate_outcome,
        rationale: content.routing_rationale,
        next_action: content.ready_for,
    };

    return (
        <div className="space-y-6">
            {/* Project Summary */}
            <Section title="Project Summary" icon="clipboard">
                {projectName && (
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">{projectName}</h3>
                )}
                {description && (
                    <div className="pl-4 border-l-4 border-violet-500 text-gray-700 mb-4">
                        {description}
                    </div>
                )}
                {userStatement && (
                    <blockquote className="pl-4 border-l-4 border-gray-300 text-gray-500 italic">
                        "{userStatement}"
                    </blockquote>
                )}
            </Section>

            {/* Project Type */}
            {projectType && (
                <Section title="Project Type" icon="tag">
                    <div className="flex items-center gap-3 mb-2">
                        <span className="px-3 py-1 rounded-full text-sm font-medium bg-violet-100 text-violet-800">
                            {typeof projectType === 'string' ? projectType : projectType.category}
                        </span>
                        {projectType.confidence && (
                            <span className="text-sm text-gray-500">
                                Confidence: {projectType.confidence}
                            </span>
                        )}
                    </div>
                    {projectType.rationale && (
                        <p className="text-gray-600">{projectType.rationale}</p>
                    )}
                </Section>
            )}

            {/* Constraints */}
            {constraints && (hasItems(constraints.explicit) || hasItems(constraints.inferred) || hasItems(constraints)) && (
                <Section title="Constraints" icon="lock">
                    {/* Handle array format (new schema) */}
                    {Array.isArray(constraints) && constraints.length > 0 && (
                        <ItemList items={constraints} icon="lock" color="amber" />
                    )}
                    {/* Handle object format (old schema) */}
                    {!Array.isArray(constraints) && (
                        <>
                            {hasItems(constraints.explicit) && (
                                <div className="mb-3">
                                    <h4 className="text-sm font-medium text-gray-500 mb-2">Explicit</h4>
                                    <ItemList items={constraints.explicit} icon="lock" color="amber" />
                                </div>
                            )}
                            {hasItems(constraints.inferred) && (
                                <div>
                                    <h4 className="text-sm font-medium text-gray-500 mb-2">Inferred</h4>
                                    <ItemList items={constraints.inferred} icon="lightbulb" color="blue" />
                                </div>
                            )}
                        </>
                    )}
                </Section>
            )}

            {/* Open Gaps */}
            {openGaps && (hasItems(openGaps.questions) || hasItems(openGaps.missing_context) || hasItems(openGaps.assumptions_made)) && (
                <Section title="Open Gaps" icon="help-circle">
                    {hasItems(openGaps.questions) && (
                        <div className="mb-3">
                            <h4 className="text-sm font-medium text-gray-500 mb-2">Questions</h4>
                            <ItemList items={openGaps.questions} icon="help" color="blue" />
                        </div>
                    )}
                    {hasItems(openGaps.missing_context) && (
                        <div className="mb-3">
                            <h4 className="text-sm font-medium text-gray-500 mb-2">Missing Context</h4>
                            <ItemList items={openGaps.missing_context} icon="alert" color="amber" />
                        </div>
                    )}
                    {hasItems(openGaps.assumptions_made) && (
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-2">Assumptions</h4>
                            <ItemList items={openGaps.assumptions_made} icon="lightbulb" color="gray" />
                        </div>
                    )}
                </Section>
            )}

            {/* Outcome */}
            {outcome && (outcome.status || outcome.rationale) && (
                <Section title="Intake Outcome" icon="flag">
                    {outcome.status && (
                        <div className="mb-3">
                            <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                                outcome.status === 'qualified' ? 'bg-emerald-100 text-emerald-800' :
                                outcome.status === 'not_ready' ? 'bg-amber-100 text-amber-800' :
                                'bg-gray-100 text-gray-800'
                            }`}>
                                {outcome.status}
                            </span>
                        </div>
                    )}
                    {outcome.rationale && (
                        <p className="text-gray-600 mb-3">{outcome.rationale}</p>
                    )}
                    {outcome.next_action && (
                        <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200">
                            <span className="text-sm font-medium text-emerald-800">
                                Next: {outcome.next_action}
                            </span>
                        </div>
                    )}
                </Section>
            )}

            {/* Metadata */}
            {content.metadata && (
                <Section title="Metadata" icon="info" collapsed>
                    <dl className="grid grid-cols-2 gap-2 text-sm">
                        {content.metadata.conversation_turn_count && (
                            <>
                                <dt className="text-gray-500">Conversation Turns</dt>
                                <dd className="text-gray-900">{content.metadata.conversation_turn_count}</dd>
                            </>
                        )}
                        {content.metadata.workflow_id && (
                            <>
                                <dt className="text-gray-500">Workflow</dt>
                                <dd className="text-gray-900 font-mono text-xs">{content.metadata.workflow_id}</dd>
                            </>
                        )}
                    </dl>
                </Section>
            )}
        </div>
    );
}

/**
 * Project Discovery document renderer
 */
function ProjectDiscoveryContent({ content }) {
    return (
        <div className="space-y-6">
            {content.project_name && (
                <Section title="Project" icon="compass">
                    <h3 className="text-lg font-semibold text-gray-900">{content.project_name}</h3>
                    {content.summary?.description && (
                        <p className="text-gray-600 mt-2">{content.summary.description}</p>
                    )}
                </Section>
            )}

            {content.goals && hasItems(content.goals) && (
                <Section title="Goals" icon="target">
                    <ItemList items={content.goals} color="emerald" />
                </Section>
            )}

            {content.stakeholders && hasItems(content.stakeholders) && (
                <Section title="Stakeholders" icon="users">
                    <ItemList items={content.stakeholders} color="blue" />
                </Section>
            )}

            {content.scope && (
                <Section title="Scope" icon="box">
                    {content.scope.in_scope && hasItems(content.scope.in_scope) && (
                        <div className="mb-3">
                            <h4 className="text-sm font-medium text-emerald-600 mb-2">In Scope</h4>
                            <ItemList items={content.scope.in_scope} color="emerald" />
                        </div>
                    )}
                    {content.scope.out_of_scope && hasItems(content.scope.out_of_scope) && (
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-2">Out of Scope</h4>
                            <ItemList items={content.scope.out_of_scope} color="gray" />
                        </div>
                    )}
                </Section>
            )}

            {/* Fallback: show raw content */}
            {!content.project_name && !content.goals && (
                <GenericDocumentContent content={content} />
            )}
        </div>
    );
}

/**
 * Generic document renderer (JSON tree)
 */
function GenericDocumentContent({ content }) {
    return (
        <div className="bg-gray-50 rounded-lg p-4 overflow-x-auto">
            <pre className="text-sm text-gray-800 whitespace-pre-wrap font-mono">
                {JSON.stringify(content, null, 2)}
            </pre>
        </div>
    );
}

/**
 * Section wrapper component
 */
function Section({ title, icon, collapsed = false, children }) {
    const [isOpen, setIsOpen] = useState(!collapsed);

    return (
        <div className="border border-gray-200 rounded-lg overflow-hidden">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full px-4 py-3 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors"
            >
                <div className="flex items-center gap-2">
                    <span className="text-gray-400">{getIcon(icon)}</span>
                    <span className="font-medium text-gray-900">{title}</span>
                </div>
                <svg
                    width="20"
                    height="20"
                    viewBox="0 0 20 20"
                    fill="none"
                    stroke="currentColor"
                    className={`text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
                >
                    <path d="M6 8l4 4 4-4" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
            </button>
            {isOpen && (
                <div className="px-4 py-4 bg-white">
                    {children}
                </div>
            )}
        </div>
    );
}

/**
 * Item list component
 */
function ItemList({ items, icon, color = 'gray' }) {
    if (!items || items.length === 0) return null;

    const colorClasses = {
        gray: 'text-gray-600',
        blue: 'text-blue-600',
        emerald: 'text-emerald-600',
        amber: 'text-amber-600',
        violet: 'text-violet-600',
    };

    return (
        <ul className="space-y-2">
            {items.map((item, i) => (
                <li key={i} className="flex items-start gap-2">
                    <span className={`mt-0.5 ${colorClasses[color]}`}>{getIcon(icon || 'dot')}</span>
                    <span className="text-gray-700">{typeof item === 'string' ? item : JSON.stringify(item)}</span>
                </li>
            ))}
        </ul>
    );
}

// Helper functions
function hasItems(arr) {
    return Array.isArray(arr) && arr.length > 0;
}

function formatDocType(docTypeId) {
    return docTypeId
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

function formatDate(isoString) {
    if (!isoString) return '';
    return new Date(isoString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

function getIcon(name) {
    const icons = {
        clipboard: '📋',
        tag: '🏷️',
        lock: '🔒',
        lightbulb: '💡',
        'help-circle': '❓',
        help: '❓',
        alert: '⚠️',
        flag: '🚩',
        info: 'ℹ️',
        compass: '🧭',
        target: '🎯',
        users: '👥',
        box: '📦',
        dot: '•',
    };
    return icons[name] || '•';
}
