import { useEffect, useState } from 'react';
import { api } from '../api/client';

const NORMAL_WIDTH = 520;
const EXPANDED_WIDTH = 900;

/**
 * Skeuomorphic paper document preview sidecar
 */
const NORMAL_HEIGHT = 600;
const EXPANDED_HEIGHT = 900;

export default function DocumentViewer({ document, projectId, projectCode, nodeWidth, onClose, onZoomComplete, onViewFull }) {
    const [isExpanded, setIsExpanded] = useState(false);
    const docWidth = isExpanded ? EXPANDED_WIDTH : NORMAL_WIDTH;
    const docHeight = isExpanded ? EXPANDED_HEIGHT : NORMAL_HEIGHT;
    const [docContent, setDocContent] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (onZoomComplete) {
            const timer = setTimeout(() => onZoomComplete(), 150);
            return () => clearTimeout(timer);
        }
    }, [onZoomComplete]);

    // Fetch document content
    useEffect(() => {
        async function fetchDoc() {
            if (!projectId || !document.id) {
                setLoading(false);
                return;
            }
            try {
                setLoading(true);
                const doc = await api.getDocument(projectId, document.id);
                setDocContent(doc?.content || null);
            } catch (err) {
                console.error('Failed to fetch document for sidecar:', err);
            } finally {
                setLoading(false);
            }
        }
        fetchDoc();
    }, [projectId, document.id]);

    // Don't render until content is loaded
    if (loading) {
        return null;
    }

    // Build content from fetched document
    const content = buildContent(document, docContent, projectCode);

    return (
        <div
            className="absolute top-0 tray-slide"
            style={{ left: nodeWidth + 30, width: docWidth, zIndex: 1000, transition: 'width 0.2s ease' }}
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
                    minHeight: docHeight,
                    transition: 'min-height 0.2s ease'
                }}
            >
                {/* Header */}
                <div
                    style={{
                        padding: '24px 32px 16px',
                        borderBottom: '2px solid #10b981',
                        background: 'linear-gradient(to bottom, #ffffff, #fafafa)'
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
                                    marginBottom: 4
                                }}
                            >
                                STABILIZED DOCUMENT
                            </div>
                            <h1
                                style={{
                                    fontSize: 20,
                                    fontFamily: 'Georgia, serif',
                                    fontWeight: 700,
                                    color: '#1a1a1a',
                                    margin: 0
                                }}
                            >
                                {content.title}
                            </h1>
                            <div
                                style={{
                                    fontSize: 11,
                                    color: '#666',
                                    marginTop: 4,
                                    fontFamily: 'monospace'
                                }}
                            >
                                {content.serial}
                            </div>
                        </div>
                        <div className="flex items-center gap-1">
                            {/* Expand/Contract button */}
                            <button
                                onClick={() => setIsExpanded(!isExpanded)}
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
                                    justifyContent: 'center'
                                }}
                            >
                                {isExpanded ? (
                                    // Contract arrows (pointing inward)
                                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
                                        <path d="M9 1v4h4M5 13v-4H1M9 5L13 1M5 9L1 13" />
                                    </svg>
                                ) : (
                                    // Expand arrows (pointing outward)
                                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
                                        <path d="M13 5V1h-4M1 9v4h4M13 1L9 5M1 13l4-4" />
                                    </svg>
                                )}
                            </button>
                            {/* Close button */}
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
                                    cursor: 'pointer'
                                }}
                            >
                                &times;
                            </button>
                        </div>
                    </div>
                </div>

                {/* Content */}
                <div
                    style={{
                        padding: '24px 32px',
                        maxHeight: isExpanded ? 600 : 400,
                        overflowY: 'auto',
                        fontFamily: 'Georgia, serif',
                        fontSize: 13,
                        lineHeight: 1.7,
                        color: '#333'
                    }}
                >
                    {content.sections.map((section, i) => (
                        <div key={i} style={{ marginBottom: 20 }}>
                            {/* Intro text (no heading) */}
                            {section.isIntro && (
                                <div
                                    style={{
                                        padding: '12px 16px',
                                        borderLeft: '4px solid #10b981',
                                        background: '#f0fdf4',
                                        fontSize: 14,
                                        color: '#166534'
                                    }}
                                >
                                    {section.content}
                                </div>
                            )}

                            {/* Regular sections with heading */}
                            {section.heading && (
                                <>
                                    <h3
                                        style={{
                                            fontSize: 11,
                                            fontWeight: 600,
                                            textTransform: 'uppercase',
                                            letterSpacing: '0.08em',
                                            color: '#666',
                                            marginBottom: 8,
                                            fontFamily: 'system-ui, sans-serif'
                                        }}
                                    >
                                        {section.heading}
                                    </h3>

                                    {/* Badge (for project type) */}
                                    {section.badge && (
                                        <span
                                            style={{
                                                display: 'inline-block',
                                                padding: '4px 12px',
                                                borderRadius: 20,
                                                background: '#ede9fe',
                                                color: '#5b21b6',
                                                fontSize: 12,
                                                fontWeight: 500,
                                                marginBottom: 8
                                            }}
                                        >
                                            {section.badge}
                                        </span>
                                    )}

                                    {/* Status badge (for outcome) */}
                                    {section.status && (
                                        <span
                                            style={{
                                                display: 'inline-block',
                                                padding: '4px 12px',
                                                borderRadius: 20,
                                                background: section.status === 'qualified' ? '#d1fae5' : '#fef3c7',
                                                color: section.status === 'qualified' ? '#065f46' : '#92400e',
                                                fontSize: 12,
                                                fontWeight: 500,
                                                marginBottom: 8
                                            }}
                                        >
                                            {section.status}
                                        </span>
                                    )}

                                    {section.content && (
                                        <p style={{ margin: 0, whiteSpace: 'pre-line' }}>
                                            {section.content}
                                        </p>
                                    )}

                                    {/* Quote (for user statement) */}
                                    {section.quote && (
                                        <blockquote
                                            style={{
                                                margin: '8px 0 0 0',
                                                padding: '8px 12px',
                                                borderLeft: '3px solid #d1d5db',
                                                color: '#6b7280',
                                                fontStyle: 'italic',
                                                fontSize: 12
                                            }}
                                        >
                                            "{section.quote}"
                                        </blockquote>
                                    )}

                                    {/* Next action (for outcome) */}
                                    {section.nextAction && (
                                        <div
                                            style={{
                                                marginTop: 8,
                                                padding: '8px 12px',
                                                borderRadius: 6,
                                                background: '#ecfdf5',
                                                border: '1px solid #a7f3d0',
                                                fontSize: 12,
                                                color: '#065f46'
                                            }}
                                        >
                                            <strong>Next:</strong> {section.nextAction}
                                        </div>
                                    )}
                                </>
                            )}
                        </div>
                    ))}
                </div>

                {/* Footer */}
                <div
                    style={{
                        padding: '16px 32px 24px',
                        borderTop: '1px solid #e5e5e5',
                        background: '#fafafa'
                    }}
                >
                    <div className="flex justify-between items-end">
                        <div>
                            <div style={{ fontSize: 10, color: '#999', marginBottom: 4 }}>
                                APPROVED BY
                            </div>
                            <div
                                style={{
                                    fontFamily: 'cursive',
                                    fontSize: 16,
                                    color: '#333',
                                    borderBottom: '1px solid #333',
                                    paddingBottom: 2,
                                    display: 'inline-block'
                                }}
                            >
                                {content.approved}
                            </div>
                            <div style={{ fontSize: 10, color: '#666', marginTop: 4 }}>
                                {content.date}
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            <span style={{ fontSize: 10, color: '#10b981', fontWeight: 600 }}>
                                VERIFIED
                            </span>
                            <div
                                style={{
                                    width: 20,
                                    height: 20,
                                    borderRadius: '50%',
                                    background: '#10b981',
                                    color: 'white',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    fontSize: 12
                                }}
                            >
                                &#10003;
                            </div>
                        </div>
                    </div>
                    <button
                        onClick={() => onViewFull?.(document.id)}
                        style={{
                            marginTop: 16,
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
                            gap: 8
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
 * Build display content from document data
 */
function buildContent(document, docContent, projectCode) {
    const title = document.name?.toUpperCase() || 'DOCUMENT';
    const serial = (projectCode || document.id) + ' - ' + (document.name || 'Document');

    // Build sections from real document content
    const sections = [];

    if (docContent) {
        // Description/captured intent at top
        const description = docContent.summary?.description || docContent.captured_intent || docContent.conversation_summary;
        if (description) {
            sections.push({ heading: null, content: description, isIntro: true });
        }

        // Project Summary
        const projectName = docContent.project_name;
        const userStatement = docContent.summary?.user_statement || docContent.conversation_summary;
        if (projectName || userStatement) {
            sections.push({
                heading: 'Project Summary',
                content: projectName,
                quote: userStatement
            });
        }

        // Project Type
        const projectType = docContent.project_type;
        if (projectType) {
            const typeLabel = typeof projectType === 'string' ? projectType : projectType.category;
            const typeRationale = projectType.rationale;
            sections.push({
                heading: 'Project Type',
                badge: typeLabel,
                content: typeRationale
            });
        }

        // Intake Outcome / Next Steps
        const outcome = docContent.outcome || {
            status: docContent.gate_outcome,
            rationale: docContent.routing_rationale,
            next_action: docContent.ready_for
        };
        if (outcome.status || outcome.next_action) {
            sections.push({
                heading: 'Intake Outcome',
                status: outcome.status,
                content: outcome.rationale,
                nextAction: outcome.next_action
            });
        }
    } else {
        // Fallback when no content loaded
        sections.push({
            heading: null,
            content: document.desc || 'Loading document content...',
            isIntro: true
        });
    }

    return {
        title,
        serial,
        sections,
        approved: 'System',
        date: 'January 2026'
    };
}
