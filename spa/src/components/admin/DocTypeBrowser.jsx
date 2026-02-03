import React from 'react';

/**
 * Left sidebar for browsing and selecting document types.
 */
export default function DocTypeBrowser({
    documentTypes = [],
    loading = false,
    selectedDocType = null,
    onSelect,
}) {
    // Group by category
    const grouped = documentTypes.reduce((acc, dt) => {
        const category = dt.category || 'other';
        if (!acc[category]) acc[category] = [];
        acc[category].push(dt);
        return acc;
    }, {});

    const categoryOrder = ['intake', 'architecture', 'planning', 'other'];
    const sortedCategories = Object.keys(grouped).sort((a, b) => {
        const aIdx = categoryOrder.indexOf(a);
        const bIdx = categoryOrder.indexOf(b);
        if (aIdx === -1 && bIdx === -1) return a.localeCompare(b);
        if (aIdx === -1) return 1;
        if (bIdx === -1) return -1;
        return aIdx - bIdx;
    });

    return (
        <div
            className="w-60 flex flex-col border-r h-full"
            style={{
                borderColor: 'var(--border-panel)',
                background: 'var(--bg-panel)',
            }}
        >
            {/* Header */}
            <div
                className="px-4 py-3 border-b"
                style={{ borderColor: 'var(--border-panel)' }}
            >
                <h2
                    className="text-sm font-semibold uppercase tracking-wide"
                    style={{ color: 'var(--text-muted)' }}
                >
                    Document Types
                </h2>
            </div>

            {/* List */}
            <div className="flex-1 overflow-y-auto">
                {loading ? (
                    <div className="p-4 text-sm" style={{ color: 'var(--text-muted)' }}>
                        Loading...
                    </div>
                ) : documentTypes.length === 0 ? (
                    <div className="p-4 text-sm" style={{ color: 'var(--text-muted)' }}>
                        No document types found
                    </div>
                ) : (
                    sortedCategories.map(category => (
                        <div key={category} className="py-2">
                            <div
                                className="px-4 py-1 text-xs font-medium uppercase tracking-wider"
                                style={{ color: 'var(--text-muted)' }}
                            >
                                {category}
                            </div>
                            {grouped[category].map(dt => (
                                <button
                                    key={dt.doc_type_id}
                                    onClick={() => onSelect?.(dt)}
                                    className="w-full px-4 py-2 text-left text-sm hover:opacity-80 transition-opacity"
                                    style={{
                                        background: selectedDocType?.doc_type_id === dt.doc_type_id
                                            ? 'var(--bg-selected)'
                                            : 'transparent',
                                        color: selectedDocType?.doc_type_id === dt.doc_type_id
                                            ? 'var(--text-primary)'
                                            : 'var(--text-secondary)',
                                        borderLeft: selectedDocType?.doc_type_id === dt.doc_type_id
                                            ? '2px solid var(--action-primary)'
                                            : '2px solid transparent',
                                    }}
                                >
                                    <div className="font-medium truncate">{dt.display_name}</div>
                                    <div
                                        className="text-xs truncate"
                                        style={{ color: 'var(--text-muted)' }}
                                    >
                                        v{dt.active_version}
                                        {dt.authority_level && ` · ${dt.authority_level}`}
                                    </div>
                                </button>
                            ))}
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
