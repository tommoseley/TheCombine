// data/factories.js
// Factory functions for creating nodes with consistent structure

import { STATION_IDS } from './constants.js';

/**
 * Create a spine document (L1)
 */
export const createDocument = (id, name, desc, state = 'queued', intent = 'mandatory', options = {}) => ({
    id,
    name,
    desc,
    state,
    intent,
    level: 1,
    ...options
});

/**
 * Create stations for active documents
 * @param {string} activeStation - ID of the currently active station (null if none)
 */
export const createStations = (activeStation = null) => {
    return STATION_IDS.map(id => ({
        id,
        label: id.toUpperCase(),
        state: activeStation === id ? 'active' : 
               STATION_IDS.indexOf(id) < STATION_IDS.indexOf(activeStation) ? 'complete' : 'pending',
        needs_input: activeStation === id && id === 'pgc'
    }));
};

/**
 * Create questions for operator input
 * @param {Array<string|{text: string, required?: boolean}>} questions
 */
export const createQuestions = (questions) => questions.map((q, i) => ({
    id: `q${i + 1}`,
    text: q.text || q,
    required: q.required !== false
}));

/**
 * Create an epic (L2) with features
 */
export const createEpic = (id, name, state = 'queued', intent = 'mandatory', featureNames = []) => ({
    id,
    name,
    state,
    intent,
    level: 2,
    features: featureNames.map((fname, i) => ({
        id: `${id}-f${i + 1}`,
        name: fname,
        state: 'queued'
    }))
});