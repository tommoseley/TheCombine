import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { RenderModelSidecar } from './RenderModelViewer';

/**
 * Document Viewer Sidecar - Data-Driven
 *
 * Fetches RenderModel from API and renders using the data-driven
 * RenderModelSidecar component. Falls back to raw JSON display
 * if RenderModel is not available.
 */
export default function DocumentViewer({
    document,
    projectId,
    projectCode,
    nodeWidth,
    onClose,
    onZoomComplete,
    onViewFull,
}) {
    const [renderModel, setRenderModel] = useState(null);
    const [rawContent, setRawContent] = useState(null);
    const [loading, setLoading] = useState(true);
    const [isExpanded, setIsExpanded] = useState(false);

    useEffect(() => {
        if (onZoomComplete) {
            const timer = setTimeout(() => onZoomComplete(), 150);
            return () => clearTimeout(timer);
        }
    }, [onZoomComplete]);

    // Fetch RenderModel (data-driven) or fall back to raw document
    useEffect(() => {
        async function fetchDocument() {
            if (!projectId || !document.id) {
                setLoading(false);
                return;
            }

            try {
                setLoading(true);

                // Try RenderModel first (data-driven display)
                try {
                    const rm = await api.getDocumentRenderModel(projectId, document.id);
                    if (rm && rm.sections && rm.sections.length > 0) {
                        setRenderModel(rm);
                        setRawContent(null);
                        return;
                    }
                    // If RenderModel has fallback flag, use its raw_content
                    if (rm?.metadata?.fallback && rm.raw_content) {
                        setRenderModel(null);
                        setRawContent(rm.raw_content);
                        return;
                    }
                } catch (rmErr) {
                    console.log('RenderModel not available, falling back to raw document:', rmErr.message);
                }

                // Fall back to raw document content
                const doc = await api.getDocument(projectId, document.id);
                setRenderModel(null);
                setRawContent(doc?.content || null);
            } catch (err) {
                console.error('Failed to fetch document for sidecar:', err);
            } finally {
                setLoading(false);
            }
        }

        fetchDocument();
    }, [projectId, document.id]);

    // Don't render until content is loaded
    if (loading) {
        return null;
    }

    // Data-driven rendering via RenderModelSidecar
    if (renderModel) {
        return (
            <RenderModelSidecar
                renderModel={renderModel}
                projectCode={projectCode}
                documentName={document.name}
                isExpanded={isExpanded}
                onToggleExpand={() => setIsExpanded(!isExpanded)}
                onClose={onClose}
                onViewFull={() => onViewFull?.(document.id)}
                nodeWidth={nodeWidth}
            />
        );
    }

    // Fallback: raw content display
    return (
        <FallbackSidecar
            document={document}
            projectCode={projectCode}
            rawContent={rawContent}
            nodeWidth={nodeWidth}
            isExpanded={isExpanded}
            onToggleExpand={() => setIsExpanded(!isExpanded)}
            onClose={onClose}
            onViewFull={() => onViewFull?.(document.id)}
        />
    );
}

/**
 * Fallback sidecar for documents without RenderModel
 * Displays raw JSON content in a styled container
 */
function FallbackSidecar({
    document,
    projectCode,
    rawContent,
    nodeWidth,
    isExpanded,
    onToggleExpand,
    onClose,
    onViewFull,
}) {
    const NORMAL_WIDTH = 520;
    const EXPANDED_WIDTH = 900;
    const NORMAL_HEIGHT = 600;
    const EXPANDED_HEIGHT = 900;

    const width = isExpanded ? EXPANDED_WIDTH : NORMAL_WIDTH;
    const height = isExpanded ? EXPANDED_HEIGHT : NORMAL_HEIGHT;
    const serial = `${projectCode || 'DOC'} - ${document.name || 'Document'}`;

    // Stop drag and wheel events from propagating to the floor canvas
    const stopPropagation = (e) => {
        e.stopPropagation();
    };

    return (
        <div
            className="absolute top-0 tray-slide nowheel nopan nodrag"
            style={{ left: nodeWidth + 30, width, zIndex: 1000, transition: 'width 0.2s ease', userSelect: 'text' }}
            onMouseDown={stopPropagation}
            onPointerDown={stopPropagation}
            onWheel={stopPropagation}
        >
            {/* Horizontal bridge */}
            <div
                className="absolute"
                style={{ top: 40, right: '100%', width: 30, height: 3, background: '#10b981' }}
            />
            <div
                className="absolute rounded-full"
                style={{ top: 36, right: '100%', marginRight: 26, width: 10, height: 10, background: '#10b981' }}
            />

            <div
                style={{
                    background: '#ffffff',
                    borderRadius: 2,
                    boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
                    minHeight: height,
                    transition: 'min-height 0.2s ease',
                    display: 'flex',
                    flexDirection: 'column',
                }}
            >
                {/* Header */}
                <div
                    style={{
                        padding: '24px 32px 16px',
                        borderBottom: '2px solid #10b981',
                        background: 'linear-gradient(to bottom, #ffffff, #fafafa)',
                    }}
                >
                    <div className="flex justify-between items-start">
                        <div>
                            <div
                                style={{
                                    fontSize: 10,
                                    letterSpacing: '0.15em',
                                    color: '#10b981',
                                    fontWeight: 600,
                                    marginBottom: 4,
                                }}
                            >
                                PRODUCED DOCUMENT
                            </div>
                            <h1
                                style={{
                                    fontSize: 20,
                                    fontFamily: 'Georgia, serif',
                                    fontWeight: 700,
                                    color: '#1a1a1a',
                                    margin: 0,
                                }}
                            >
                                {document.name?.toUpperCase() || 'DOCUMENT'}
                            </h1>
                            <div
                                style={{
                                    fontSize: 11,
                                    color: '#666',
                                    marginTop: 4,
                                    fontFamily: 'monospace',
                                }}
                            >
                                {serial}
                            </div>
                        </div>
                        <div className="flex items-center gap-1">
                            <button
                                onClick={onToggleExpand}
                                title={isExpanded ? 'Contract' : 'Expand'}
                                style={{
                                    color: '#666',
                                    fontSize: 16,
                                    lineHeight: 1,
                                    padding: 6,
                                    background: 'none',
                                    border: '1px solid #e5e5e5',
                                    borderRadius: 4,
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                }}
                            >
                                {isExpanded ? (
                                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
                                        <path d="M9 1v4h4M5 13v-4H1M9 5L13 1M5 9L1 13" />
                                    </svg>
                                ) : (
                                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
                                        <path d="M13 5V1h-4M1 9v4h4M13 1L9 5M1 13l4-4" />
                                    </svg>
                                )}
                            </button>
                            <button
                                onClick={onClose}
                                title="Close"
                                style={{
                                    color: '#999',
                                    fontSize: 24,
                                    lineHeight: 1,
                                    padding: 4,
                                    background: 'none',
                                    border: 'none',
                                    cursor: 'pointer',
                                }}
                            >
                                &times;
                            </button>
                        </div>
                    </div>
                </div>

                {/* Content - Smart structured display */}
                <div
                    style={{
                        flex: 1,
                        padding: '16px 24px',
                        overflowY: 'auto',
                        maxHeight: isExpanded ? 600 : 400,
                    }}
                    onWheel={(e) => e.stopPropagation()}
                >
                    <SidecarContent content={rawContent} />
                </div>

                {/* Footer */}
                <div
                    style={{
                        padding: '16px 32px 24px',
                        borderTop: '1px solid #e5e5e5',
                        background: '#fafafa',
                    }}
                >
                    <button
                        onClick={onViewFull}
                        style={{
                            width: '100%',
                            padding: '10px 16px',
                            background: '#10b981',
                            color: 'white',
                            border: 'none',
                            borderRadius: 4,
                            fontSize: 12,
                            fontWeight: 600,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: 8,
                        }}
                    >
                        <span>View Full Document</span>
                        <span style={{ fontSize: 14 }}>&#8599;</span>
                    </button>
                </div>
            </div>
        </div>
    );
}

/**
 * Smart sidecar content - renders structured fields as compact list,
 * falls back to truncated JSON for unrecognized content.
 */
function SidecarContent({ content }) {
    if (!content || typeof content !== 'object') {
        return <p style={{ fontSize: 12, color: '#9ca3af' }}>No content</p>;
    }

    const title = content.project_name || content.title || content.name;
    const SKIP = new Set(['project_name', 'title', 'name', 'meta', 'description']);

    // Collect renderable sections
    const sections = Object.entries(content)
        .filter(([k, v]) => !SKIP.has(k) && v != null)
        .map(([k, v]) => ({ key: k, label: k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()), value: v }));

    if (sections.length === 0) {
        return <pre style={{ fontSize: 11, color: '#374151', whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>{JSON.stringify(content, null, 2)}</pre>;
    }

    return (
        <div className="space-y-3">
            {title && <h3 style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>{title}</h3>}
            {sections.map(({ key, label, value }) => {
                // Object (not array) - show summary fields
                if (typeof value === 'object' && !Array.isArray(value)) {
                    const subFields = Object.entries(value).filter(([, v]) => typeof v === 'string');
                    if (subFields.length === 0) return null;
                    return (
                        <div key={key}>
                            <div style={{ fontSize: 10, fontWeight: 700, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>{label}</div>
                            {subFields.slice(0, 3).map(([sk, sv]) => (
                                <p key={sk} style={{ fontSize: 12, color: '#374151', margin: '0 0 2px', lineHeight: 1.5 }}>
                                    <span style={{ fontWeight: 600 }}>{sk.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}:</span> {sv.length > 120 ? sv.slice(0, 120) + '...' : sv}
                                </p>
                            ))}
                        </div>
                    );
                }

                // Array
                if (Array.isArray(value) && value.length > 0) {
                    return (
                        <div key={key}>
                            <div style={{ fontSize: 10, fontWeight: 700, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>{label} ({value.length})</div>
                            <ul style={{ margin: 0, padding: 0, listStyle: 'none' }}>
                                {value.slice(0, 5).map((item, i) => {
                                    const text = typeof item === 'string' ? item : extractItemText(item);
                                    const id = typeof item === 'object' && item?.id ? item.id : null;
                                    return (
                                        <li key={i} style={{ fontSize: 12, color: '#374151', padding: '2px 0', display: 'flex', gap: 4 }}>
                                            <span style={{ color: '#9ca3af', flexShrink: 0 }}>{'\u2022'}</span>
                                            <span>
                                                {id && <span style={{ fontFamily: 'monospace', fontSize: 10, color: '#9ca3af', marginRight: 4 }}>{id}</span>}
                                                {text.length > 100 ? text.slice(0, 100) + '...' : text}
                                            </span>
                                        </li>
                                    );
                                })}
                                {value.length > 5 && <li style={{ fontSize: 11, color: '#9ca3af', padding: '2px 0' }}>...and {value.length - 5} more</li>}
                            </ul>
                        </div>
                    );
                }

                // Scalar
                if (typeof value === 'string') {
                    return (
                        <div key={key}>
                            <div style={{ fontSize: 10, fontWeight: 700, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 2 }}>{label}</div>
                            <p style={{ fontSize: 12, color: '#374151', margin: 0 }}>{value.length > 150 ? value.slice(0, 150) + '...' : value}</p>
                        </div>
                    );
                }

                return null;
            })}
        </div>
    );
}

/** Extract primary text from an object item */
function extractItemText(item) {
    if (typeof item === 'string') return item;
    if (typeof item !== 'object' || item === null) return String(item);
    const textKeys = ['constraint', 'assumption', 'guardrail', 'recommendation', 'description', 'question', 'text', 'statement', 'name', 'title'];
    for (const k of textKeys) {
        if (item[k] && typeof item[k] === 'string') return item[k];
    }
    // Return first string value
    for (const v of Object.values(item)) {
        if (typeof v === 'string' && v.length > 10) return v;
    }
    return JSON.stringify(item);
}
