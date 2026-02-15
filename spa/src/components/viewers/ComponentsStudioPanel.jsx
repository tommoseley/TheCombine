import { useState } from 'react';

/**
 * ComponentsStudioPanel - Vertical rail + detail view for architecture components.
 * Mirrors WorkflowStudioPanel pattern for consistency.
 */
export default function ComponentsStudioPanel({ components }) {
    const [selectedId, setSelectedId] = useState(components[0]?.id || null);

    const selectedComponent = components.find(c => c.id === selectedId);

    const handleKeyDown = (e) => {
        const currentIdx = components.findIndex(c => c.id === selectedId);
        if (e.key === 'ArrowDown' && currentIdx < components.length - 1) {
            e.preventDefault();
            setSelectedId(components[currentIdx + 1].id);
        } else if (e.key === 'ArrowUp' && currentIdx > 0) {
            e.preventDefault();
            setSelectedId(components[currentIdx - 1].id);
        }
    };

    const chipStyle = (bg, color) => ({
        fontSize: 12,
        padding: '3px 10px',
        background: bg,
        color: color,
        borderRadius: 4,
        fontWeight: 500,
    });

    return (
        <div className="flex h-full" onKeyDown={handleKeyDown} tabIndex={0}>
            {/* Left Rail */}
            <div 
                className="flex-shrink-0 border-r overflow-y-auto"
                style={{ width: 220, background: '#f8fafc', borderColor: '#e2e8f0' }}
                onWheel={(e) => e.stopPropagation()}
            >
                <div className="p-3">
                    <div className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: '#64748b' }}>
                        Components ({components.length})
                    </div>
                    {components.map((comp) => {
                        const isSelected = comp.id === selectedId;
                        return (
                            <button
                                key={comp.id}
                                onClick={() => setSelectedId(comp.id)}
                                className="w-full text-left p-2.5 rounded-md mb-1 transition-colors"
                                style={{
                                    background: isSelected ? '#eef2ff' : 'transparent',
                                    borderLeft: isSelected ? '3px solid #4f46e5' : '3px solid transparent',
                                }}
                            >
                                <div className="text-sm font-medium truncate" style={{ color: isSelected ? '#4f46e5' : '#1e293b' }}>
                                    {comp.name}
                                </div>
                                {comp.layer && (
                                    <div className="text-xs mt-0.5" style={{ color: '#64748b' }}>
                                        {comp.layer}
                                    </div>
                                )}
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* Main Detail View */}
            <div className="flex-1 flex flex-col min-w-0 overflow-y-auto" onWheel={(e) => e.stopPropagation()}>
                {selectedComponent ? (
                    <div className="p-6">
                        {/* Header */}
                        <div className="mb-6">
                            <div className="flex items-center gap-3 mb-2">
                                <h2 className="text-xl font-semibold" style={{ color: '#1e293b' }}>
                                    {selectedComponent.name}
                                </h2>
                                {selectedComponent.layer && (
                                    <span style={chipStyle('#f0fdf4', '#166534')}>{selectedComponent.layer}</span>
                                )}
                                {selectedComponent.mvpPhase && (
                                    <span style={chipStyle('#eff6ff', '#1e40af')}>{selectedComponent.mvpPhase}</span>
                                )}
                            </div>
                            {selectedComponent.purpose && (
                                <p className="text-base" style={{ color: '#475569', lineHeight: 1.6 }}>
                                    {selectedComponent.purpose}
                                </p>
                            )}
                        </div>

                        {/* Technology */}
                        {selectedComponent.technology && (
                            <DetailSection title="Technology">
                                <p style={{ color: '#374151', fontSize: 14 }}>{selectedComponent.technology}</p>
                            </DetailSection>
                        )}

                        {/* Responsibilities */}
                        {selectedComponent.responsibilities?.length > 0 && (
                            <DetailSection title="Responsibilities">
                                <ul className="list-disc pl-5 space-y-1">
                                    {selectedComponent.responsibilities.map((r, i) => (
                                        <li key={i} style={{ color: '#374151', fontSize: 14 }}>{r}</li>
                                    ))}
                                </ul>
                            </DetailSection>
                        )}

                        {/* Interfaces */}
                        {selectedComponent.interfaces?.length > 0 && (
                            <DetailSection title="Interfaces">
                                <div className="flex flex-wrap gap-2">
                                    {selectedComponent.interfaces.map((iface, i) => (
                                        <span key={i} style={chipStyle('#e0e7ff', '#3730a3')}>{iface}</span>
                                    ))}
                                </div>
                            </DetailSection>
                        )}

                        {/* Dependencies */}
                        {selectedComponent.dependencies?.length > 0 && (
                            <DetailSection title="Dependencies">
                                <div className="flex flex-wrap gap-2">
                                    {selectedComponent.dependencies.map((dep, i) => (
                                        <span key={i} style={chipStyle('#fef3c7', '#92400e')}>{dep}</span>
                                    ))}
                                </div>
                            </DetailSection>
                        )}
                    </div>
                ) : (
                    <div className="flex items-center justify-center h-full" style={{ color: '#9ca3af' }}>
                        Select a component from the list
                    </div>
                )}
            </div>
        </div>
    );
}

function DetailSection({ title, children }) {
    return (
        <div className="mb-5">
            <div 
                className="text-xs font-semibold uppercase tracking-wider mb-2"
                style={{ color: '#6b7280' }}
            >
                {title}
            </div>
            {children}
        </div>
    );
}