import { useState, useEffect } from 'react';
import { api } from '../api/client';
import RenderModelViewer from './RenderModelViewer';
import ConfigDrivenDocViewer from './viewers/ConfigDrivenDocViewer';
import DocumentHeader from './viewer/DocumentHeader';
import SpawnedChildrenPanel from './viewer/SpawnedChildrenPanel';
import RawContentViewer, { PgcContextSection } from './viewer/RawContentViewer';

/**
 * Full-screen document viewer modal - Data-Driven
 *
 * Fetches RenderModel from API and renders using the data-driven
 * RenderModelViewer component. Falls back to raw JSON display
 * if RenderModel is not available.
 */
export default function FullDocumentViewer({ projectId, projectCode, docTypeId, instanceId, onClose, inline, nextStepLabel, onProduceNext }) {
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

                    // Route 1: IA config present → config-driven viewer (ADR-054)
                    if (rm?.rendering_config?.detail_html) {
                        setRenderModel(rm);
                        setRawContent(null);
                        return;
                    }
                    // Route 2: Populated sections → legacy DocDef path
                    if (rm && rm.sections && rm.sections.length > 0) {
                        setRenderModel(rm);
                        setRawContent(null);
                        return;
                    }
                    // Route 3: Raw content fallback
                    if (rm?.metadata?.fallback && rm.raw_content) {
                        setRenderModel(null);
                        setRawContent(rm.raw_content);
                        return;
                    }
                } catch (rmErr) {
                    // RenderModel not available, falling back to raw document
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
        if (inline) return;
        const handleKeyDown = (e) => {
            if (e.key === 'Escape') onClose();
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [onClose, inline]);

    // Loading state
    if (loading) {
        if (inline) {
            return (
                <div className="flex items-center justify-center h-full" style={{ background: 'var(--bg-canvas)' }}>
                    <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>Loading document...</div>
                </div>
            );
        }
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

    // Route to config-driven tabbed viewer when rendering_config is present (ADR-054)
    const hasRenderingConfig = renderModel?.rendering_config?.detail_html;

    if (hasRenderingConfig && renderModel) {
        const configContent = (
            <ConfigDrivenDocViewer
                renderModel={renderModel}
                projectId={projectId}
                projectCode={projectCode}
                docTypeId={docTypeId}
                executionId={executionId}
                docTypeName={metadata.document_type_name}
                onClose={onClose}
                inline={inline}
                nextStepLabel={nextStepLabel}
                onProduceNext={onProduceNext}
            />
        );
        if (inline) {
            return (
                <div className="w-full h-full overflow-hidden flex flex-col" style={{ background: 'var(--bg-canvas)' }}>
                    {configContent}
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
                    className="relative w-full max-w-6xl h-[90vh] overflow-hidden rounded-lg shadow-2xl flex flex-col"
                    style={{ background: 'var(--bg-canvas)' }}
                >
                    {/* Close button */}
                    <button
                        onClick={onClose}
                        className="absolute top-2 right-3 z-10 p-1.5 rounded-lg hover:opacity-80 transition-colors"
                        style={{ background: 'var(--bg-panel)' }}
                    >
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M18 6L6 18M6 6l12 12" />
                        </svg>
                    </button>
                    {configContent}
                </div>
            </div>
        );
    }

    const legacyContent = (
        <>
            {/* Document Header */}
            <DocumentHeader
                title={renderModel?.title || docTitle}
                projectId={projectId}
                projectCode={projectCode}
                docTypeId={docTypeId}
                adminUrl={adminUrl}
                executionId={executionId}
                metadata={metadata}
                onClose={inline ? undefined : onClose}
                nextStepLabel={nextStepLabel}
                onProduceNext={onProduceNext}
            />

            {/* Spawned children panel */}
            {metadata?.spawned_children?.count > 0 && (
                <SpawnedChildrenPanel children={metadata.spawned_children} />
            )}

            {/* Content */}
            <div
                className="overflow-y-auto p-6"
                style={inline
                    ? { flex: 1 }
                    : { maxHeight: metadata?.spawned_children?.count > 0 ? 'calc(90vh - 130px)' : 'calc(90vh - 80px)' }
                }
                onWheel={inline ? undefined : (e) => e.stopPropagation()}
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
                            <p style={{ color: 'var(--text-muted)' }}>No content available</p>
                        </div>
                    )}

                    {/* PGC Context section - shown for any document that went through PGC */}
                    {pgcContext && pgcContext.clarifications?.length > 0 && (
                        <PgcContextSection pgcContext={pgcContext} />
                    )}
                </div>
        </>
    );

    if (inline) {
        return (
            <div className="w-full h-full overflow-hidden flex flex-col" style={{ background: 'var(--bg-canvas)' }}>
                {legacyContent}
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
                style={{ background: 'var(--bg-canvas)' }}
            >
                {legacyContent}
            </div>
        </div>
    );
}
