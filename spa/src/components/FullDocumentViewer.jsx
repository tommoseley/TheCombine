import { useState, useEffect } from 'react';
import { api } from '../api/client';
import RenderModelViewer from './RenderModelViewer';

/**
 * Full-screen document viewer modal - Data-Driven
 *
 * Fetches RenderModel from API and renders using the data-driven
 * RenderModelViewer component. Falls back to raw JSON display
 * if RenderModel is not available.
 */
export default function FullDocumentViewer({ projectId, projectCode, docTypeId, onClose }) {
    const [renderModel, setRenderModel] = useState(null);
    const [rawContent, setRawContent] = useState(null);
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
                const doc = await api.getDocument(projectId, docTypeId);
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
    }, [projectId, docTypeId]);

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
                        {/* Project code badge */}
                        {projectCode && (
                            <div
                                style={{
                                    display: 'inline-block',
                                    padding: '2px 8px',
                                    background: '#10b981',
                                    color: 'white',
                                    fontSize: 11,
                                    fontWeight: 600,
                                    borderRadius: 4,
                                    letterSpacing: '0.05em',
                                }}
                            >
                                {projectCode}
                            </div>
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
                <div
                    className="overflow-y-auto p-6"
                    style={{ maxHeight: 'calc(90vh - 80px)' }}
                    onWheel={(e) => e.stopPropagation()}
                >
                    {error && (
                        <div className="text-center py-12">
                            <p className="text-red-500">{error}</p>
                        </div>
                    )}

                    {renderModel && (
                        <RenderModelViewer renderModel={renderModel} variant="full" />
                    )}

                    {rawContent && !renderModel && (
                        <RawContentViewer content={rawContent} docTypeId={docTypeId} />
                    )}

                    {!renderModel && !rawContent && !error && (
                        <div className="text-center py-12">
                            <p className="text-gray-500">No content available</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

/**
 * Raw content viewer - displays JSON with some structure
 */
function RawContentViewer({ content, docTypeId }) {
    if (!content) {
        return <p className="text-gray-500">No content available</p>;
    }

    // Try to extract some common fields for a nicer display
    const title = content.project_name || content.title || content.name;
    const description = content.description || content.summary || content.preliminary_summary;

    return (
        <div className="space-y-6">
            {/* Warning banner */}
            <div
                style={{
                    padding: '12px 16px',
                    background: '#fef3c7',
                    border: '1px solid #fde68a',
                    borderRadius: 8,
                    fontSize: 13,
                    color: '#92400e',
                }}
            >
                No view definition configured for <strong>{docTypeId}</strong> - displaying raw content
            </div>

            {/* Basic info if available */}
            {(title || description) && (
                <div
                    style={{
                        padding: 16,
                        background: '#f8fafc',
                        borderRadius: 8,
                        border: '1px solid #e2e8f0',
                    }}
                >
                    {title && (
                        <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
                    )}
                    {description && (
                        <p className="text-gray-700 text-sm">{description}</p>
                    )}
                </div>
            )}

            {/* Raw JSON */}
            <div
                style={{
                    background: '#f8fafc',
                    borderRadius: 8,
                    padding: 16,
                    overflow: 'auto',
                }}
            >
                <pre
                    style={{
                        margin: 0,
                        fontSize: 12,
                        color: '#374151',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        fontFamily: 'monospace',
                        lineHeight: 1.6,
                    }}
                >
                    {JSON.stringify(content, null, 2)}
                </pre>
            </div>
        </div>
    );
}

/**
 * Format document type ID as human-readable name
 */
function formatDocType(docTypeId) {
    return docTypeId
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}
