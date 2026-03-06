/**
 * WSDetailView -- Focused WS detail with accordion sections.
 *
 * Shown in center panel when a WS is selected.
 * Uses HTML <details>/<summary> for zero-JS accordion behavior.
 *
 * WS-WB-030: Work Binder Studio Layout.
 */
import { useCallback } from 'react';
import { getStateBadge, formatWsId, formatWsForClipboard } from './wsUtils';

function AccordionSection({ label, children, defaultOpen }) {
    if (!children) return null;
    return (
        <details className="wb-ws-accordion" open={defaultOpen || undefined}>
            <summary className="wb-ws-accordion-trigger">{label}</summary>
            <div className="wb-ws-accordion-content">{children}</div>
        </details>
    );
}

function ListItems({ items, ordered }) {
    if (!items || items.length === 0) return null;
    const Tag = ordered ? 'ol' : 'ul';
    return (
        <Tag className="wb-ws-detail-list">
            {items.map((item, i) => <li key={i}>{item}</li>)}
        </Tag>
    );
}

function SubLabel({ text }) {
    return <div className="wb-ws-detail-sublabel">{text}</div>;
}

export default function WSDetailView({
    ws, statements = [], onStabilize, onMoveUp, onMoveDown, onCopy, onBack,
}) {
    const badge = getStateBadge(ws.state);
    const wsId = formatWsId(ws);
    const idx = statements.findIndex(s => s.ws_id === ws.ws_id);
    const isFirst = idx <= 0;
    const isLast = idx >= statements.length - 1;

    const handleCopy = useCallback(() => {
        const text = formatWsForClipboard(ws);
        navigator.clipboard.writeText(text).catch(() => {
            console.warn('WSDetailView: clipboard write failed');
        });
        if (onCopy) onCopy(ws);
    }, [ws, onCopy]);

    const pins = ws.governance_pins || {};
    const hasGovPins = pins.ta_version_id ||
        (pins.adr_refs && pins.adr_refs.length > 0) ||
        (pins.policy_refs && pins.policy_refs.length > 0);
    const hasConstraints = (ws.prohibited_actions && ws.prohibited_actions.length > 0) ||
        (ws.allowed_paths && ws.allowed_paths.length > 0) ||
        hasGovPins;
    const hasScope = (ws.scope_in && ws.scope_in.length > 0) ||
        (ws.scope_out && ws.scope_out.length > 0);

    return (
        <div className="wb-ws-detail-view">
            {/* Header */}
            <div className="wb-ws-detail-header">
                <button
                    className="wb-ws-detail-back"
                    onClick={onBack}
                    title="Back to WP overview"
                >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M19 12H5M12 19l-7-7 7-7" />
                    </svg>
                </button>
                <span className="wb-mono wb-ws-detail-id">{wsId}</span>
                <span className="wb-ws-detail-title">{ws.title || ws.objective || 'Untitled'}</span>
                <button
                    className="wb-btn wb-btn--ghost wb-btn--sm wb-ws-copy-btn"
                    onClick={handleCopy}
                    title="Copy to clipboard"
                >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                        <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
                    </svg>
                </button>
                <span
                    className="wb-ws-badge"
                    style={{ backgroundColor: `var(${badge.cssVar})` }}
                >
                    {badge.label}
                </span>
            </div>

            {/* Objective */}
            {ws.objective && (
                <p className="wb-ws-detail-objective">{ws.objective}</p>
            )}

            {/* Accordion sections */}
            {hasScope && (
                <AccordionSection label="SCOPE" defaultOpen>
                    {ws.scope_in && ws.scope_in.length > 0 && (
                        <>
                            <SubLabel text="IN SCOPE" />
                            <ListItems items={ws.scope_in} />
                        </>
                    )}
                    {ws.scope_out && ws.scope_out.length > 0 && (
                        <>
                            <SubLabel text="OUT OF SCOPE" />
                            <ListItems items={ws.scope_out} />
                        </>
                    )}
                </AccordionSection>
            )}

            {ws.procedure && ws.procedure.length > 0 && (
                <AccordionSection label="PROCEDURE" defaultOpen>
                    <ListItems items={ws.procedure} ordered />
                </AccordionSection>
            )}

            {ws.verification_criteria && ws.verification_criteria.length > 0 && (
                <AccordionSection label="VERIFICATION">
                    <ListItems items={ws.verification_criteria} />
                </AccordionSection>
            )}

            {hasConstraints && (
                <AccordionSection label="CONSTRAINTS">
                    {ws.prohibited_actions && ws.prohibited_actions.length > 0 && (
                        <>
                            <SubLabel text="PROHIBITED ACTIONS" />
                            <ListItems items={ws.prohibited_actions} />
                        </>
                    )}
                    {ws.allowed_paths && ws.allowed_paths.length > 0 && (
                        <>
                            <SubLabel text="ALLOWED PATHS" />
                            <ListItems items={ws.allowed_paths} />
                        </>
                    )}
                    {hasGovPins && (
                        <>
                            <SubLabel text="GOVERNANCE PINS" />
                            <div className="wb-ws-gov-pins">
                                {pins.ta_version_id && (
                                    <span className="wb-mono wb-ws-pin">TA: {pins.ta_version_id}</span>
                                )}
                                {pins.adr_refs && pins.adr_refs.length > 0 && (
                                    <span className="wb-mono wb-ws-pin">ADR: {pins.adr_refs.join(', ')}</span>
                                )}
                                {pins.policy_refs && pins.policy_refs.length > 0 && (
                                    <span className="wb-mono wb-ws-pin">POL: {pins.policy_refs.join(', ')}</span>
                                )}
                            </div>
                        </>
                    )}
                </AccordionSection>
            )}

            {/* Action bar */}
            <div className="wb-ws-detail-actions">
                {ws.state === 'DRAFT' && (
                    <button
                        className="wb-btn wb-btn--primary wb-btn--sm"
                        onClick={() => onStabilize(ws.ws_id)}
                    >
                        STABILIZE STATEMENT
                    </button>
                )}
                <div className="wb-ws-reorder">
                    <button
                        className="wb-btn wb-btn--ghost wb-btn--sm"
                        onClick={() => onMoveUp(ws.ws_id)}
                        disabled={isFirst}
                        title="Move up"
                    >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M12 19V5M5 12l7-7 7 7" />
                        </svg>
                    </button>
                    <span className="wb-ws-detail-position">
                        {idx >= 0 ? `${idx + 1} of ${statements.length}` : ''}
                    </span>
                    <button
                        className="wb-btn wb-btn--ghost wb-btn--sm"
                        onClick={() => onMoveDown(ws.ws_id)}
                        disabled={isLast}
                        title="Move down"
                    >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M12 5v14M5 12l7 7 7-7" />
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    );
}
