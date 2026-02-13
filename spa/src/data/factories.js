/**
 * Factory functions for creating document/project data structures
 * 
 * Note: Stations are now workflow-driven per WS-STATION-DATA-001.
 * createStations is kept for test compatibility but should not be used
 * in production code - stations come from the backend API.
 */

export const createDocument = (id, name, desc, state = 'queued', intent = 'mandatory', options = {}) => ({
    id, name, desc, state, intent, level: 1, ...options
});

/**
 * @deprecated Stations are now workflow-driven. Use API-provided stations.
 * Kept for test fixtures only.
 */
export const createStations = (activeStation = null, stationIds = ['pgc', 'draft', 'qa', 'done']) => stationIds.map((id, idx) => ({
    id,
    label: id.toUpperCase(),
    state: activeStation === id ? 'active' : stationIds.indexOf(id) < stationIds.indexOf(activeStation) ? 'complete' : 'pending',
    needs_input: activeStation === id && id === 'pgc'
}));

export const createQuestions = (questions) => questions.map((q, i) => ({
    id: `q${i + 1}`, text: q.text || q, required: q.required !== false
}));

export const createEpic = (id, name, state = 'queued', intent = 'mandatory', featureNames = []) => ({
    id, name, state, intent, level: 2,
    features: featureNames.map((fname, i) => ({ id: `${id}-f${i + 1}`, name: fname, state: 'queued' }))
});

export const createNewProject = (name) => {
    const id = 'project-' + Date.now();
    return {
        id,
        name: name || 'New Project',
        description: 'Untitled project',
        status: 'active',
        data: [
            createDocument('concierge', 'Concierge Intake', 'Tell us about your project', 'active', 'mandatory', {
                stations: createStations('pgc', ['intake', 'draft', 'qa', 'done']),
                questions: createQuestions([
                    'What is the primary goal of this project?',
                    'Who are the main stakeholders?',
                    'What is your target timeline?',
                    { text: 'Any budget constraints?', required: false },
                ])
            })
        ]
    };
};