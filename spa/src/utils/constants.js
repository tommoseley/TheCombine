/**
 * Edge colors per theme using unified artifact states
 *
 * Artifact states:
 * - blocked: red (#ef4444)
 * - in_progress: amber (#f59e0b)
 * - ready: yellow (#eab308)
 * - stabilized: green (#10b981)
 */
export const EDGE_COLORS = {
    light: {
        // Artifact states
        blocked: '#ef4444',
        in_progress: '#6366f1',  // indigo for light theme
        ready: '#eab308',
        stabilized: '#10b981',
        // Legacy mappings (for backward compat during transition)
        active: '#6366f1',
        queued: '#eab308',
        produced: '#10b981',
        requirements_not_met: '#ef4444',
    },
    industrial: {
        // Artifact states
        blocked: '#ef4444',
        in_progress: '#f59e0b',
        ready: '#eab308',
        stabilized: '#10b981',
        // Legacy mappings
        active: '#f59e0b',
        queued: '#eab308',
        produced: '#10b981',
        requirements_not_met: '#ef4444',
    },
    blueprint: {
        // Artifact states
        blocked: '#ef4444',
        in_progress: '#fbbf24',
        ready: '#eab308',
        stabilized: '#10b981',
        // Legacy mappings
        active: '#fbbf24',
        queued: '#eab308',
        produced: '#10b981',
        requirements_not_met: '#ef4444',
    }
};

/**
 * Map raw state to artifact state for edge coloring
 */
function rawToArtifactState(rawState) {
    if (['produced', 'stabilized', 'ready', 'complete'].includes(rawState)) return 'stabilized';
    if (['requirements_not_met', 'blocked', 'halted', 'failed'].includes(rawState)) return 'blocked';
    if (['in_production', 'active', 'queued', 'awaiting_operator'].includes(rawState)) return 'in_progress';
    if (['ready_for_production', 'waiting', 'pending_acceptance'].includes(rawState)) return 'ready';
    return 'ready';
}

export const getEdgeColor = (state, theme) => {
    const artifactState = rawToArtifactState(state);
    return EDGE_COLORS[theme]?.[artifactState] || EDGE_COLORS.industrial.ready;
};

// Layout grid constants
export const GRID = {
    EPICS_PER_ROW: 3,
    EPIC_WIDTH: 220,
    EPIC_HEIGHT: 70,
    EPIC_GAP_X: 50,
    EPIC_GAP_Y: 100,
    EPIC_OFFSET_X: 80,
    EPIC_OFFSET_Y: 80
};

// Sidecar tray constants
export const TRAY = {
    GAP: 8,
    WIDTH: 280
};

// Station IDs in order
export const STATION_IDS = ['pgc', 'asm', 'draft', 'qa', 'done'];

// Theme list
export const THEMES = ['industrial', 'light', 'blueprint'];
export const THEME_LABELS = {
    industrial: 'Industrial',
    light: 'Light',
    blueprint: 'Blueprint'
};
