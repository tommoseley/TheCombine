import React, { useState, useEffect, useRef } from 'react';
import { api } from '../../api/client';

/**
 * DownloadDropdown — small button with dropdown for standard/evidence download.
 */
function DownloadDropdown({ onDownload, options }) {
    const [open, setOpen] = useState(false);
    const [downloading, setDownloading] = useState(null);
    const ref = useRef(null);

    useEffect(() => {
        if (!open) return;
        function close(e) { if (ref.current && !ref.current.contains(e.target)) setOpen(false); }
        document.addEventListener('mousedown', close);
        return () => document.removeEventListener('mousedown', close);
    }, [open]);

    const handleClick = async (mode) => {
        setDownloading(mode);
        try { await onDownload(mode); } finally { setDownloading(null); setOpen(false); }
    };

    return (
        <div ref={ref} className="relative">
            <button
                onClick={() => setOpen(!open)}
                className="p-2 rounded-lg hover:opacity-80 transition-colors"
                style={{ color: 'var(--text-muted)' }}
                title="Download Markdown"
            >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                    <polyline points="7 10 12 15 17 10" />
                    <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
            </button>
            {open && (
                <div
                    className="absolute right-0 top-full mt-1 z-50 rounded-lg border shadow-lg py-1"
                    style={{ background: 'var(--bg-panel)', borderColor: 'var(--border-panel)', minWidth: 220 }}
                >
                    {options.map(opt => (
                        <button
                            key={opt.mode}
                            onClick={() => handleClick(opt.mode)}
                            disabled={downloading === opt.mode}
                            className="w-full text-left px-3 py-2 text-xs hover:bg-white/10 transition-colors"
                            style={{ color: 'var(--text-primary)', background: 'transparent', border: 'none', cursor: 'pointer' }}
                        >
                            {downloading === opt.mode ? 'Downloading...' : opt.label}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}

/**
 * Document header with title, project badge, metadata, and close button.
 * Used by both generic and specialized document viewers.
 */
export default function DocumentHeader({ title, projectId, projectCode, adminUrl, executionId, metadata, onClose, nextStepLabel, onProduceNext, docTypeId }) {
    const displayTitle = (() => {
        if (!title) return 'Document';
        const colonIndex = title.indexOf(': ');
        return colonIndex > -1 ? title.slice(colonIndex + 2) : title;
    })();

    const docType = metadata?.document_type_name
        || (metadata?.document_type
            ? metadata.document_type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
            : null);

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

    const generatedDate = formatDate(metadata?.created_at);
    const updatedDate = formatDate(metadata?.updated_at);
    const version = metadata?.version;
    const lifecycleState = metadata?.lifecycle_state;

    return (
        <div
            className="sticky top-0 px-6 py-4 border-b"
            style={{ background: 'var(--bg-panel)', borderColor: 'var(--border-panel)' }}
        >
            <div className="flex items-start justify-between">
                <div style={{ flex: 1, minWidth: 0 }}>
                    {/* Top line: badges */}
                    <div className="flex items-center gap-2 flex-wrap" style={{ marginBottom: 6 }}>
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
                        {docType && (
                            <span style={{
                                padding: '2px 8px',
                                background: '#eef2ff',
                                color: '#4f46e5',
                                fontSize: 11,
                                fontWeight: 600,
                                borderRadius: 4,
                            }}>
                                {docType}
                            </span>
                        )}
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
                        {version && version > 1 && (
                            <span style={{
                                padding: '2px 8px',
                                background: 'var(--bg-button)',
                                color: 'var(--text-muted)',
                                fontSize: 11,
                                fontWeight: 600,
                                borderRadius: 4,
                            }}>
                                v{version}
                            </span>
                        )}
                    </div>
                    {/* Title */}
                    <h2 style={{
                        margin: 0,
                        fontSize: 20,
                        fontWeight: 700,
                        color: 'var(--text-primary)',
                        lineHeight: 1.3,
                    }}>
                        {displayTitle}
                    </h2>
                    {/* Date line */}
                    {generatedDate && (
                        <div style={{ marginTop: 4, fontSize: 12, color: 'var(--text-dim)' }}>
                            Generated {generatedDate}
                            {updatedDate && updatedDate !== generatedDate && (
                                <span> &middot; Updated {updatedDate}</span>
                            )}
                        </div>
                    )}
                </div>
                <div className="flex items-center gap-2" style={{ flexShrink: 0, marginLeft: 12 }}>
                    {/* ADR-063: Rewind control — inline button */}
                    {projectId && docTypeId && (
                        <button
                            onClick={() => {
                                const reason = prompt(`Rewind pipeline to ${docTypeId}?\n\nEnter reason:`);
                                if (!reason) return;
                                api.rewindPipeline(projectId, docTypeId, reason)
                                    .then(r => { alert(`Rewound to ${r.rewind_to_stage}. ${r.affected_document_count} documents marked stale.`); window.location.reload(); })
                                    .catch(e => alert(`Rewind failed: ${e.message}`));
                            }}
                            className="text-[9px] px-1.5 py-0.5 rounded opacity-60 hover:opacity-100 transition-opacity"
                            style={{
                                color: 'var(--text-secondary)',
                                border: '1px solid var(--border-primary, #d1d5db)',
                            }}
                            title="Rewind pipeline to this stage"
                        >
                            ↩ Rewind
                        </button>
                    )}
                    {/* Produce next document CTA */}
                    {nextStepLabel && onProduceNext && (
                        <button
                            className="px-3 py-1.5 rounded-lg font-semibold transition-all hover:brightness-110"
                            style={{
                                fontSize: 11,
                                backgroundColor: 'var(--state-ready-bg)',
                                color: 'white',
                                whiteSpace: 'nowrap',
                            }}
                            onClick={onProduceNext}
                        >
                            Produce {nextStepLabel} &rarr;
                        </button>
                    )}
                    {/* Download Markdown dropdown */}
                    {metadata?.display_id && projectId && (
                        <DownloadDropdown
                            onDownload={async (mode) => {
                                try {
                                    const blob = await api.renderDocument(projectId, metadata.display_id, { mode });
                                    const url = URL.createObjectURL(blob);
                                    const a = document.createElement('a');
                                    a.href = url;
                                    const suffix = mode === 'evidence' ? '-evidence' : '';
                                    a.download = `${projectCode || projectId}-${metadata.display_id}${suffix}.md`;
                                    a.click();
                                    URL.revokeObjectURL(url);
                                } catch (err) {
                                    if (err.status === 409) {
                                        alert(`Render blocked: ${err.data?.message || 'IA verification failed'}`);
                                    } else {
                                        console.error('Download failed:', err);
                                    }
                                }
                            }}
                            options={[
                                { label: 'Download Markdown', mode: 'standard' },
                                { label: 'Download Markdown (With Evidence)', mode: 'evidence' },
                            ]}
                        />
                    )}
                    {onClose && (
                        <button
                            onClick={onClose}
                            className="p-2 rounded-lg hover:opacity-80 transition-colors"
                        >
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M18 6L6 18M6 6l12 12" />
                            </svg>
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
