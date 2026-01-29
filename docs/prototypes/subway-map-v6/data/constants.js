// data/constants.js
// Color palette and layout configuration

export const COLORS = {
    stabilized: { bg: '#10b981', border: '#059669', text: '#34d399', edge: '#10b981' },
    active: { bg: '#6366f1', border: '#4f46e5', text: '#818cf8', edge: '#6366f1' },
    queued: { bg: '#475569', border: '#334155', text: '#94a3b8', edge: '#334155' }
};

export const getColors = (state) => COLORS[state] || COLORS.queued;

// Grid layout configuration
export const GRID_CONFIG = {
    EPICS_PER_ROW: 3,
    EPIC_WIDTH: 220,
    EPIC_HEIGHT: 70,
    EPIC_GAP_X: 50,
    EPIC_GAP_Y: 100,
    EPIC_OFFSET_X: 80,
    EPIC_OFFSET_Y: 80
};

// Side-car configuration
export const TRAY_CONFIG = {
    GAP: 8,
    WIDTH: 280
};

// Station definitions
export const STATION_IDS = ['pgc', 'asm', 'draft', 'qa', 'done'];