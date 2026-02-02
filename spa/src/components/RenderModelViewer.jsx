/**
 * RenderModelViewer - Generic data-driven document renderer
 *
 * Renders documents based on RenderModel structure from the backend.
 * Maps block types to React components via the block registry.
 */
import { useState } from 'react';
import { renderBlock } from './blocks';

/**
 * Main viewer component for RenderModel documents
 */
export default function RenderModelViewer({
    renderModel,
    variant = 'full',  // 'full', 'compact', 'sidecar'
    hideHeader = false,  // Skip rendering the title/subtitle header
    onSectionClick,
    className = '',
}) {
    const [expandedSections, setExpandedSections] = useState(new Set(
        // Expand all sections by default
        renderModel?.sections?.map(s => s.section_id) || []
    ));

    if (!renderModel) {
        return (
            <div style={{ padding: 20, textAlign: 'center', color: '#6b7280' }}>
                No render model available
            </div>
        );
    }

    const { title, subtitle, sections = [], metadata } = renderModel;

    // Handle fallback mode (raw content)
    if (metadata?.fallback && renderModel.raw_content) {
        return (
            <FallbackViewer
                title={title}
                content={renderModel.raw_content}
                reason={metadata.reason}
            />
        );
    }

    const toggleSection = (sectionId) => {
        setExpandedSections(prev => {
            const next = new Set(prev);
            if (next.has(sectionId)) {
                next.delete(sectionId);
            } else {
                next.add(sectionId);
            }
            return next;
        });
    };

    const isCompact = variant === 'compact' || variant === 'sidecar';
    const isSidecar = variant === 'sidecar';

    // Filter sections based on viewer_tab for sidecar mode
    // Sidecar shows "overview" sections only; full view shows all
    const filteredSections = isSidecar
        ? sections.filter(s => s.viewer_tab === 'overview' || !s.viewer_tab)
        : sections;

    // Strip document type prefix from title (e.g., "Project Discovery: X" -> "X")
    const displayTitle = (() => {
        if (!title) return 'Document';
        const colonIndex = title.indexOf(': ');
        return colonIndex > -1 ? title.slice(colonIndex + 2) : title;
    })();

    return (
        <div className={className}>
            {/* Header */}
            {variant === 'full' && !hideHeader && (
                <div style={{ marginBottom: 24 }}>
                    <h1
                        style={{
                            margin: 0,
                            fontSize: 24,
                            fontWeight: 700,
                            color: '#111827',
                        }}
                    >
                        {displayTitle}
                    </h1>
                    {subtitle && (
                        <p
                            style={{
                                margin: '8px 0 0',
                                fontSize: 14,
                                color: '#6b7280',
                            }}
                        >
                            {subtitle}
                        </p>
                    )}
                </div>
            )}

            {/* Sections */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: isCompact ? 12 : 20 }}>
                {filteredSections.map((section) => (
                    <RenderSection
                        key={section.section_id}
                        section={section}
                        isExpanded={expandedSections.has(section.section_id)}
                        onToggle={() => toggleSection(section.section_id)}
                        onClick={() => onSectionClick?.(section)}
                        variant={variant}
                    />
                ))}
            </div>

            {/* Empty state */}
            {filteredSections.length === 0 && (
                <div
                    style={{
                        padding: 32,
                        textAlign: 'center',
                        color: '#9ca3af',
                        background: '#f9fafb',
                        borderRadius: 8,
                    }}
                >
                    No content sections available
                </div>
            )}
        </div>
    );
}

/**
 * Individual section renderer
 */
function RenderSection({ section, isExpanded, onToggle, onClick, variant }) {
    const { section_id, title, description, blocks = [], sidecar_max_items } = section;
    const isCompact = variant === 'compact' || variant === 'sidecar';
    const isSidecar = variant === 'sidecar';

    if (blocks.length === 0) return null;

    // Apply sidecar_max_items limit when in sidecar mode
    const displayBlocks = (isSidecar && sidecar_max_items && blocks.length > sidecar_max_items)
        ? blocks.slice(0, sidecar_max_items)
        : blocks;
    const hasMore = isSidecar && sidecar_max_items && blocks.length > sidecar_max_items;

    return (
        <div
            style={{
                background: '#ffffff',
                borderRadius: 8,
                border: '1px solid #e5e7eb',
                overflow: 'hidden',
            }}
        >
            {/* Section header */}
            <button
                onClick={onToggle}
                style={{
                    width: '100%',
                    padding: isCompact ? '10px 14px' : '14px 18px',
                    background: '#f9fafb',
                    border: 'none',
                    borderBottom: isExpanded ? '1px solid #e5e7eb' : 'none',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    textAlign: 'left',
                }}
            >
                <div>
                    <h3
                        style={{
                            margin: 0,
                            fontSize: isCompact ? 13 : 15,
                            fontWeight: 600,
                            color: '#111827',
                        }}
                    >
                        {title}
                        {hasMore && (
                            <span style={{ fontWeight: 400, color: '#6b7280', marginLeft: 6 }}>
                                (showing {sidecar_max_items} of {blocks.length})
                            </span>
                        )}
                    </h3>
                    {description && !isCompact && (
                        <p
                            style={{
                                margin: '4px 0 0',
                                fontSize: 12,
                                color: '#6b7280',
                            }}
                        >
                            {description}
                        </p>
                    )}
                </div>
                <svg
                    width="16"
                    height="16"
                    viewBox="0 0 16 16"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    style={{
                        color: '#9ca3af',
                        transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                        transition: 'transform 0.2s',
                    }}
                >
                    <path d="M4 6l4 4 4-4" />
                </svg>
            </button>

            {/* Section content */}
            {isExpanded && (
                <div style={{ padding: isCompact ? 12 : 18 }}>
                    {displayBlocks.map((block, index) => renderBlock(block, index))}
                    {hasMore && (
                        <div
                            style={{
                                marginTop: 8,
                                padding: '8px 12px',
                                background: '#f3f4f6',
                                borderRadius: 4,
                                fontSize: 12,
                                color: '#6b7280',
                                textAlign: 'center',
                            }}
                        >
                            +{blocks.length - sidecar_max_items} more in full view
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

/**
 * Fallback viewer for when RenderModel building fails
 */
function FallbackViewer({ title, content, reason }) {
    return (
        <div>
            <div
                style={{
                    padding: '12px 16px',
                    background: '#fef3c7',
                    border: '1px solid #fde68a',
                    borderRadius: 8,
                    marginBottom: 16,
                    fontSize: 12,
                    color: '#92400e',
                }}
            >
                Displaying raw content (reason: {reason || 'unknown'})
            </div>
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
                    }}
                >
                    {JSON.stringify(content, null, 2)}
                </pre>
            </div>
        </div>
    );
}

/**
 * Sidecar variant with expand/collapse
 */
export function RenderModelSidecar({
    renderModel,
    projectCode,
    documentName,
    isExpanded,
    onToggleExpand,
    onClose,
    onViewFull,
    nodeWidth = 280,
}) {
    const NORMAL_WIDTH = 520;
    const EXPANDED_WIDTH = 900;
    const NORMAL_HEIGHT = 600;
    const EXPANDED_HEIGHT = 900;

    const width = isExpanded ? EXPANDED_WIDTH : NORMAL_WIDTH;
    const height = isExpanded ? EXPANDED_HEIGHT : NORMAL_HEIGHT;

    const serial = `${projectCode || 'DOC'} - ${documentName || 'Document'}`;

    // Stop drag events from propagating to the floor canvas
    const stopPropagation = (e) => {
        e.stopPropagation();
    };

    return (
        <div
            className="absolute top-0 tray-slide"
            style={{ left: nodeWidth + 30, width, zIndex: 1000, transition: 'width 0.2s ease' }}
            onMouseDown={stopPropagation}
            onPointerDown={stopPropagation}
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
                                STABILIZED DOCUMENT
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
                                {(() => {
                                    // Strip document type prefix (e.g., "Project Discovery: " -> just the rest)
                                    const title = renderModel?.title || 'DOCUMENT';
                                    const colonIndex = title.indexOf(': ');
                                    const displayTitle = colonIndex > -1 ? title.slice(colonIndex + 2) : title;
                                    return displayTitle.toUpperCase();
                                })()}
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

                {/* Content */}
                <div
                    style={{
                        flex: 1,
                        padding: '16px 24px',
                        overflowY: 'auto',
                        maxHeight: isExpanded ? 600 : 400,
                    }}
                >
                    <RenderModelViewer
                        renderModel={renderModel}
                        variant="sidecar"
                    />
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
