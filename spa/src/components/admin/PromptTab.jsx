import React, { useCallback } from 'react';

/**
 * Editable textarea for a single prompt artifact.
 * Shows save status indicator.
 */
export default function PromptTab({
    content,
    onChange,
    loading = false,
    saving = false,
    isDirty = false,
    error = null,
    readOnly = false,
    placeholder = 'Enter prompt content...',
    isJson = false,
}) {
    // Format JSON content
    const handleFormatJson = useCallback(() => {
        if (!content || !isJson) return;
        try {
            const parsed = JSON.parse(content);
            const formatted = JSON.stringify(parsed, null, 2);
            onChange?.(formatted);
        } catch (e) {
            // Invalid JSON - don't format
            console.warn('Invalid JSON, cannot format:', e.message);
        }
    }, [content, isJson, onChange]);
    return (
        <div className="flex flex-col h-full">
            {/* Status bar */}
            <div
                className="flex items-center justify-between px-3 py-2 text-xs border-b"
                style={{
                    borderColor: 'var(--border-panel)',
                    background: 'var(--bg-panel)',
                }}
            >
                <div className="flex items-center gap-2">
                    {readOnly && (
                        <span
                            className="px-2 py-0.5 rounded"
                            style={{ background: 'var(--border-panel)', color: 'var(--text-muted)' }}
                        >
                            Read-only
                        </span>
                    )}
                    {!readOnly && isDirty && (
                        <span style={{ color: 'var(--text-muted)' }}>Modified</span>
                    )}
                </div>
                <div className="flex items-center gap-2">
                    {isJson && !readOnly && (
                        <button
                            onClick={handleFormatJson}
                            className="px-2 py-0.5 rounded text-xs hover:opacity-80"
                            style={{
                                background: 'var(--bg-button)',
                                color: 'var(--text-muted)',
                            }}
                        >
                            Format JSON
                        </button>
                    )}
                    {loading && (
                        <span style={{ color: 'var(--text-muted)' }}>Loading...</span>
                    )}
                    {saving && (
                        <span style={{ color: 'var(--state-active-text)' }}>Saving...</span>
                    )}
                    {!saving && !loading && isDirty && (
                        <span style={{ color: 'var(--action-success)' }}>Saved</span>
                    )}
                    {error && (
                        <span style={{ color: 'var(--state-error-text)' }}>Error: {error}</span>
                    )}
                </div>
            </div>

            {/* Editor */}
            <div className="flex-1 relative">
                {loading ? (
                    <div
                        className="absolute inset-0 flex items-center justify-center"
                        style={{ background: 'var(--bg-canvas)' }}
                    >
                        <span style={{ color: 'var(--text-muted)' }}>Loading content...</span>
                    </div>
                ) : (
                    <textarea
                        value={content}
                        onChange={(e) => onChange?.(e.target.value)}
                        placeholder={placeholder}
                        readOnly={readOnly}
                        className="w-full h-full p-4 resize-none font-mono text-sm"
                        style={{
                            background: 'var(--bg-canvas)',
                            color: 'var(--text-primary)',
                            border: 'none',
                            outline: 'none',
                        }}
                        spellCheck={false}
                    />
                )}
            </div>
        </div>
    );
}
