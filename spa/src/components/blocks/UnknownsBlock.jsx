import { useState } from 'react';

/**
 * Unknowns block renderer
 * Displays a list of unknowns with expandable details
 */
export default function UnknownsBlock({ block }) {
    const { data } = block;
    const items = data.items || [];
    const [expanded, setExpanded] = useState({});

    if (items.length === 0) return null;

    const toggleExpand = (index) => {
        setExpanded(prev => ({ ...prev, [index]: !prev[index] }));
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {items.map((item, i) => {
                const isExpanded = expanded[i];
                const hasDetails = item.why_it_matters || item.impact_if_unresolved;

                return (
                    <div
                        key={i}
                        style={{
                            background: '#fefce8',
                            border: '1px solid #fef08a',
                            borderRadius: 6,
                            borderLeft: '3px solid #eab308',
                            overflow: 'hidden',
                        }}
                    >
                        {/* Question header - clickable */}
                        <button
                            onClick={() => hasDetails && toggleExpand(i)}
                            style={{
                                width: '100%',
                                padding: '10px 12px',
                                background: 'transparent',
                                border: 'none',
                                cursor: hasDetails ? 'pointer' : 'default',
                                display: 'flex',
                                alignItems: 'flex-start',
                                justifyContent: 'space-between',
                                gap: 8,
                                textAlign: 'left',
                            }}
                        >
                            <span
                                style={{
                                    fontSize: 13,
                                    fontWeight: 500,
                                    color: '#854d0e',
                                    lineHeight: 1.4,
                                }}
                            >
                                {item.question || item.value || item.text || 'Unknown'}
                            </span>
                            {hasDetails && (
                                <svg
                                    width="14"
                                    height="14"
                                    viewBox="0 0 14 14"
                                    fill="none"
                                    stroke="#a16207"
                                    strokeWidth="2"
                                    style={{
                                        flexShrink: 0,
                                        marginTop: 2,
                                        transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                                        transition: 'transform 0.15s',
                                    }}
                                >
                                    <path d="M3 5l4 4 4-4" />
                                </svg>
                            )}
                        </button>

                        {/* Expanded details */}
                        {isExpanded && hasDetails && (
                            <div
                                style={{
                                    padding: '0 12px 12px',
                                    borderTop: '1px solid #fde68a',
                                    marginTop: 0,
                                }}
                            >
                                {/* Why it matters */}
                                {item.why_it_matters && (
                                    <div style={{ marginTop: 10 }}>
                                        <div
                                            style={{
                                                fontSize: 10,
                                                fontWeight: 600,
                                                color: '#a16207',
                                                textTransform: 'uppercase',
                                                letterSpacing: '0.05em',
                                                marginBottom: 3,
                                            }}
                                        >
                                            Why it matters
                                        </div>
                                        <div
                                            style={{
                                                fontSize: 12,
                                                color: '#713f12',
                                                lineHeight: 1.5,
                                            }}
                                        >
                                            {item.why_it_matters}
                                        </div>
                                    </div>
                                )}

                                {/* Impact if unresolved */}
                                {item.impact_if_unresolved && (
                                    <div style={{ marginTop: 10 }}>
                                        <div
                                            style={{
                                                fontSize: 10,
                                                fontWeight: 600,
                                                color: '#a16207',
                                                textTransform: 'uppercase',
                                                letterSpacing: '0.05em',
                                                marginBottom: 3,
                                            }}
                                        >
                                            Impact if unresolved
                                        </div>
                                        <div
                                            style={{
                                                fontSize: 12,
                                                color: '#713f12',
                                                lineHeight: 1.5,
                                            }}
                                        >
                                            {item.impact_if_unresolved}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                );
            })}
        </div>
    );
}
