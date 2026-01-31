/**
 * Factory functions for creating document/project data structures
 */
import { STATION_IDS } from '../utils/constants';

export const createDocument = (id, name, desc, state = 'queued', intent = 'mandatory', options = {}) => ({
    id, name, desc, state, intent, level: 1, ...options
});

export const createStations = (activeStation = null) => STATION_IDS.map(id => ({
    id,
    label: id.toUpperCase(),
    state: activeStation === id ? 'active' : STATION_IDS.indexOf(id) < STATION_IDS.indexOf(activeStation) ? 'complete' : 'pending',
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
                stations: createStations('pgc'),
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
