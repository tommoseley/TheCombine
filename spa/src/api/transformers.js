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
 */
const STATE_MAP = {
    'queued': 'queued',
    'blocked': 'queued',  // Show blocked as queued visually
    'assembling': 'active',
    'binding': 'active',
    'auditing': 'active',
    'remediating': 'active',
    'awaiting_operator': 'active',
    'stabilized': 'stabilized',
    'halted': 'queued',
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

    // Group tracks: first-level docs go in main array, epics go as children of backlog
    const projectDocs = [];
    const epicDocs = [];

    for (const track of apiStatus.tracks) {
        const doc = transformTrack(track, interrupts);

        // Check if this is an epic (scope would come from API)
        if (track.scope === 'epic') {
            epicDocs.push(doc);
        } else {
            projectDocs.push(doc);
        }
    }

    // Build the document tree
    for (const doc of projectDocs) {
        // If this is the epic backlog, attach epics as children
        if (doc.id === 'epic_backlog' && epicDocs.length > 0) {
            doc.children = epicDocs.map(epic => ({
                ...epic,
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
    const state = STATE_MAP[track.state] || 'queued';
    const needsInput = track.state === 'awaiting_operator';

    // Find matching interrupt for this track
    const interrupt = interrupts.find(i => i.document_type === track.document_type);

    // Build stations array
    let stations = null;
    if (state === 'active' || needsInput) {
        stations = buildStations(track.stations, track.state);
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
function buildStations(apiStations, trackState) {
    if (!apiStations || apiStations.length === 0) {
        // Generate default stations based on current state
        const activeStation = trackState === 'awaiting_operator' ? 'pgc' :
                              trackState === 'assembling' ? 'asm' :
                              trackState === 'binding' ? 'pgc' :
                              trackState === 'auditing' ? 'aud' : null;

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
