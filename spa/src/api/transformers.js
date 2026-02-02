/**
 * Transform API responses to SPA-expected format
 *
 * The SPA uses a specific data structure for rendering the production floor.
 * The API returns data in a different format optimized for the database schema.
 * These transformers bridge the gap.
 */

import { STATION_IDS } from '../utils/constants';

/**
 * Map API production state to SPA state
 *
 * New production states (ADR-043):
 * - produced: Final, certified artifact
 * - in_production: Actively moving through the line
 * - ready_for_production: All requirements met, can start
 * - requirements_not_met: Blocked by missing inputs
 * - awaiting_operator: Line stopped, operator input required
 * - halted: Explicit stop (error, policy, operator)
 */
const STATE_MAP = {
    // New production states (pass through)
    'produced': 'produced',
    'in_production': 'in_production',
    'ready_for_production': 'ready_for_production',
    'requirements_not_met': 'requirements_not_met',
    'awaiting_operator': 'awaiting_operator',
    'halted': 'halted',
    // Legacy states (backward compatibility)
    'queued': 'ready_for_production',
    'blocked': 'requirements_not_met',
    'assembling': 'in_production',
    'binding': 'in_production',
    'auditing': 'in_production',
    'remediating': 'in_production',
    'stabilized': 'produced',
};

/**
 * Map station abbreviations to display labels
 */
const STATION_LABELS = {
    'pgc': 'PGC',
    'bind': 'BIND',
    'asm': 'ASM',
    'aud': 'AUD',
    'rem': 'REM',
    'done': 'DONE',
};

/**
 * Transform API project list to SPA projects object
 */
export function transformProjectsList(apiResponse) {
    const projects = {};

    for (const project of apiResponse.projects) {
        projects[project.id] = {
            id: project.id,
            projectId: project.project_id,
            name: project.name,
            description: project.description || '',
            status: project.status === 'active' ? 'active' :
                    project.is_archived ? 'complete' : 'queued',
            icon: project.icon,
            createdAt: project.created_at,
            isArchived: project.is_archived || false,
        };
    }

    return projects;
}

/**
 * Transform API production status to SPA document data format
 *
 * API format: { project_id, line_state, tracks: [...], interrupts: [...] }
 * SPA format: [{ id, name, desc, state, level, stations, questions, children }]
 */
export function transformProductionStatus(apiStatus, interrupts = []) {
    const documents = [];

    // Group tracks by scope: project-level docs go in main array, others are potential children
    const projectDocs = [];
    const childDocsByType = {}; // Map of doc_type -> array of docs

    for (const track of apiStatus.tracks) {
        const doc = transformTrack(track, interrupts);
        const scope = track.scope || 'project';

        if (scope === 'project') {
            projectDocs.push({
                ...doc,
                // Preserve parent-child metadata from API
                mayOwn: track.may_own || [],
                childDocType: track.child_doc_type,
            });
        } else {
            // Group child docs by their type for later attachment
            const docType = track.document_type;
            if (!childDocsByType[docType]) {
                childDocsByType[docType] = [];
            }
            childDocsByType[docType].push(doc);
        }
    }

    // Build the document tree using may_own metadata from API
    for (const doc of projectDocs) {
        // If this document can own children, attach them
        if (doc.childDocType && childDocsByType[doc.childDocType]) {
            doc.children = childDocsByType[doc.childDocType].map(child => ({
                ...child,
                level: 2,
            }));
        }
        documents.push(doc);
    }

    return documents;
}

/**
 * Transform a single track to document format
 */
function transformTrack(track, interrupts = []) {
    const state = STATE_MAP[track.state] || 'ready_for_production';
    const needsInput = track.state === 'awaiting_operator';

    // Find matching interrupt for this track
    const interrupt = interrupts.find(i => i.document_type === track.document_type);

    // Build stations array (only for in_production or awaiting_operator)
    let stations = null;
    if (state === 'in_production' || needsInput) {
        stations = buildStations(track.stations, track.state, track.station);
    }

    // Build questions from interrupt if awaiting operator
    let questions = null;
    if (interrupt && interrupt.questions) {
        questions = interrupt.questions.map((q, i) => ({
            id: q.id || `q${i + 1}`,
            text: q.question || q.text || q,
            required: q.required !== false,
        }));
    }

    return {
        id: track.document_type,
        name: track.document_name || formatDocTypeName(track.document_type),
        desc: track.description || '',
        state,
        intent: 'mandatory',
        level: 1,
        stations,
        questions,
        interruptId: interrupt?.id,
        blockedBy: track.blocked_by || [],
    };
}

/**
 * Build stations array for active documents
 */
function buildStations(apiStations, trackState, currentStation) {
    if (!apiStations || apiStations.length === 0) {
        // Generate default stations based on current state/station
        // Use the station field from the API if available
        const activeStation = currentStation ||
                              (trackState === 'awaiting_operator' ? 'pgc' :
                               trackState === 'in_production' ? 'asm' : null);

        return STATION_IDS.map(id => ({
            id,
            label: STATION_LABELS[id] || id.toUpperCase(),
            state: activeStation === id ? 'active' :
                   STATION_IDS.indexOf(id) < STATION_IDS.indexOf(activeStation) ? 'complete' : 'pending',
            needs_input: id === 'pgc' && trackState === 'awaiting_operator',
        }));
    }

    return apiStations.map(s => ({
        id: s.station,
        label: STATION_LABELS[s.station] || s.station.toUpperCase(),
        state: s.state || 'pending',
        needs_input: s.needs_input || false,
    }));
}

/**
 * Format document type ID as human-readable name
 */
function formatDocTypeName(docType) {
    return docType
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

/**
 * Transform interrupt data to questions format
 */
export function transformInterrupt(interrupt) {
    return {
        id: interrupt.id,
        documentType: interrupt.document_type,
        executionId: interrupt.execution_id,
        questions: (interrupt.questions || []).map((q, i) => ({
            id: q.id || `q${i + 1}`,
            text: q.question || q.text || q,
            required: q.required !== false,
        })),
        context: interrupt.context || {},
    };
}
