// Edge colors per theme (JS because edges are programmatic)
export const EDGE_COLORS = {
    light: {
        stabilized: '#10b981',
        active: '#6366f1',
        queued: '#cbd5e1'
    },
    industrial: {
        stabilized: '#10b981',
        active: '#f59e0b',
        queued: '#334155'
    },
    blueprint: {
        stabilized: '#ffffff',
        active: '#fbbf24',
        queued: '#d4e8f8'
    }
};

export const getEdgeColor = (state, theme) =>
    EDGE_COLORS[theme]?.[state] || EDGE_COLORS.industrial.queued;

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
