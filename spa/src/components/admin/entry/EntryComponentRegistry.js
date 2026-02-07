/**
 * Entry Component Registry
 *
 * Maps Entry operation IDs to their React components.
 * Entry operations capture structured operator input via UI.
 *
 * Per ADR-047 Addendum A, Entry operations follow the same contract
 * as code-based mechanical ops but use React components as executors.
 */

import GenericEntryForm from './GenericEntryForm';
import ConciergeEntryForm from './ConciergeEntryForm';
import PGCAnswerForm from './PGCAnswerForm';

/**
 * Registry mapping operation IDs to components.
 * '_default' is the fallback for unknown operations.
 */
export const entryComponents = {
    'concierge_entry': ConciergeEntryForm,
    'pgc_operator_answers': PGCAnswerForm,
    '_default': GenericEntryForm,
};

/**
 * Get the Entry component for a given operation ID.
 * Returns the specific component if registered, otherwise the generic fallback.
 *
 * @param {string} opId - The operation ID (e.g., 'concierge_entry')
 * @returns {React.ComponentType} The Entry component
 */
export function getEntryComponent(opId) {
    return entryComponents[opId] || entryComponents['_default'];
}

/**
 * Check if a specific component exists for an operation.
 *
 * @param {string} opId - The operation ID
 * @returns {boolean} True if a specific component exists
 */
export function hasSpecificComponent(opId) {
    return opId in entryComponents && opId !== '_default';
}

export default entryComponents;
