/**
 * Shared WS constants and utilities.
 *
 * Extracted from WorkView.jsx for use by WPIndex, WSDetailView, and WorkView.
 * WS-WB-030: Work Binder Studio Layout.
 */

export const STATE_BADGE = {
    DRAFT: { label: 'DRAFT', cssVar: '--state-ready-bg' },
    READY: { label: 'READY', cssVar: '--state-stabilized-bg' },
    IN_PROGRESS: { label: 'IN PROGRESS', cssVar: '--state-active-bg' },
    ACCEPTED: { label: 'ACCEPTED', cssVar: '--state-stabilized-bg' },
    REJECTED: { label: 'REJECTED', cssVar: '--state-blocked-bg' },
    BLOCKED: { label: 'BLOCKED', cssVar: '--state-blocked-bg' },
};

export function getStateBadge(state) {
    if (!state) return STATE_BADGE.DRAFT;
    const upper = state.toUpperCase().replace(/ /g, '_');
    return STATE_BADGE[upper] || STATE_BADGE.DRAFT;
}

export function formatWsId(ws) {
    return ws.ws_id || 'WS-???';
}

export function formatWsForClipboard(ws) {
    const lines = [];
    lines.push(`# ${formatWsId(ws)}: ${ws.title || ws.objective || 'Untitled'}`);
    if (ws.state) lines.push(`State: ${ws.state}`);
    if (ws.objective) { lines.push(''); lines.push(`## Objective`); lines.push(ws.objective); }
    const listSection = (heading, items) => {
        if (!items || items.length === 0) return;
        lines.push(''); lines.push(`## ${heading}`);
        items.forEach(item => lines.push(`- ${item}`));
    };
    listSection('Scope', ws.scope_in);
    listSection('Out of Scope', ws.scope_out);
    listSection('Procedure', ws.procedure);
    listSection('Verification Criteria', ws.verification_criteria);
    listSection('Prohibited Actions', ws.prohibited_actions);
    listSection('Allowed Paths', ws.allowed_paths);
    const pins = ws.governance_pins || {};
    if (pins.ta_version_id || (pins.adr_refs && pins.adr_refs.length > 0) || (pins.policy_refs && pins.policy_refs.length > 0)) {
        lines.push(''); lines.push('## Governance Pins');
        if (pins.ta_version_id) lines.push(`- TA: ${pins.ta_version_id}`);
        if (pins.adr_refs && pins.adr_refs.length > 0) lines.push(`- ADR: ${pins.adr_refs.join(', ')}`);
        if (pins.policy_refs && pins.policy_refs.length > 0) lines.push(`- POL: ${pins.policy_refs.join(', ')}`);
    }
    return lines.join('\n');
}

export async function fetchWorkStatements(projectId, wpId) {
    try {
        const res = await fetch(`/api/v1/work-binder/wp/${encodeURIComponent(wpId)}/work-statements`);
        if (!res.ok) throw new Error(`${res.status}`);
        const data = await res.json();
        return Array.isArray(data) ? data : (data?.work_statements || data?.items || []);
    } catch (e) {
        console.warn('wsUtils: WS fetch failed:', e.message);
        return [];
    }
}

export async function createWorkStatement(wpId, intent) {
    const res = await fetch(`/api/v1/work-binder/wp/${encodeURIComponent(wpId)}/work-statements`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: intent }),
    });
    if (!res.ok) throw new Error(`Failed to create WS: ${res.status}`);
    return res.json();
}

export async function stabilizeWorkStatement(wsId) {
    const res = await fetch(`/api/v1/work-binder/work-statements/${encodeURIComponent(wsId)}/stabilize`, {
        method: 'POST',
    });
    if (!res.ok) throw new Error(`Failed to stabilize WS: ${res.status}`);
    return res.json();
}

export async function reorderWorkStatements(wpId, wsIndexEntries) {
    const res = await fetch(`/api/v1/work-binder/wp/${encodeURIComponent(wpId)}/ws-index`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ws_index: wsIndexEntries }),
    });
    if (!res.ok) throw new Error(`Failed to reorder: ${res.status}`);
    return res.json();
}
