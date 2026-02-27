/**
 * Edge colors per theme using unified artifact states
 *
 * Artifact states:
 * - blocked: red (#ef4444)
 * - in_progress: amber (#f59e0b)
 * - ready: yellow (#eab308)
 * - stabilized: green (#10b981)
 */
/**
 * Edge colors per theme — synced with --state-*-edge CSS variables in themes.css.
 * These are used for React Flow inline styles (can't use CSS vars in SVG paths).
 */
export const EDGE_COLORS = {
    light: {
        // Artifact states (match --state-*-edge in .theme-light)
        blocked: '#ef4444',
        in_progress: '#F6AD55',
        ready: '#1e40af',
        stabilized: '#10b981',
        // Legacy mappings (for backward compat during transition)
        active: '#F6AD55',
        queued: '#94a3b8',
        produced: '#10b981',
        requirements_not_met: '#ef4444',
    },
    industrial: {
        // Artifact states (match --state-*-edge in .theme-industrial)
        blocked: '#ef4444',
        in_progress: '#F6AD55',
        ready: '#00E5FF',
        stabilized: '#10b981',
        // Legacy mappings
        active: '#F6AD55',
        queued: '#334155',
        produced: '#10b981',
        requirements_not_met: '#ef4444',
    },
    blueprint: {
        // Artifact states (match --state-*-edge in .theme-blueprint)
        blocked: '#ef4444',
        in_progress: '#F6AD55',
        ready: '#00E5FF',
        stabilized: '#10b981',
        // Legacy mappings
        active: '#F6AD55',
        queued: '#5a7a9a',
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
    WPS_PER_ROW: 3,
    WP_WIDTH: 220,
    WP_HEIGHT: 85,
    WP_GAP_X: 50,
    WP_GAP_Y: 100,
    WP_OFFSET_X: 80,
    WP_OFFSET_Y: 80
};

// Sidecar tray constants
export const TRAY = {
    GAP: 8,
    WIDTH: 280
};

// Station IDs removed - now driven by workflow definitions per WS-STATION-DATA-001
// Stations come from backend API in track.stations[]

// Theme list
export const THEMES = ['industrial', 'light', 'blueprint'];
export const THEME_LABELS = {
    industrial: 'Industrial',
    light: 'Light',
    blueprint: 'Blueprint'
};
