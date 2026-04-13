/**
 * Build a template reference string for the task_ref field.
 * Format: prompt:template:{template_id}:{version}
 */
export function buildTemplateRef(template) {
    if (!template) return '';
    return `prompt:template:${template.template_id}:${template.active_version || template.version || '1.0.0'}`;
}

/**
 * Parse a template reference to extract template_id.
 * Format: prompt:template:{template_id}:{version}
 */
export function parseTemplateRef(ref) {
    if (!ref) return null;
    const parts = ref.split(':');
    if (parts.length >= 3 && parts[0] === 'prompt' && parts[1] === 'template') {
        return parts[2];
    }
    // Legacy format: tasks/Name v1.0 or just the template_id
    return ref;
}

/**
 * Build a fragment reference string for includes.
 * Format: prompt:{kind}:{fragment_id}:{version}
 */
export function buildFragmentRef(fragment) {
    if (!fragment) return '';
    const kind = fragment.kind || 'role';
    const id = fragment.fragment_id?.replace(`${kind}:`, '') || fragment.id || '';
    const version = fragment.version || fragment.active_version || '1.0.0';
    return `prompt:${kind}:${id}:${version}`;
}

/**
 * Parse a fragment reference to extract the ID.
 * Format: prompt:{kind}:{id}:{version}
 */
export function parseFragmentRef(ref) {
    if (!ref) return null;
    const parts = ref.split(':');
    if (parts.length >= 3 && parts[0] === 'prompt') {
        return parts[2]; // Return the ID part
    }
    return ref;
}

/**
 * Build a schema reference string for includes.
 * Format: schema:{schema_id}:{version}
 */
export function buildSchemaRef(schema) {
    if (!schema) return '';
    const version = schema.active_version || schema.version || '1.0.0';
    return `schema:${schema.schema_id}:${version}`;
}

/**
 * Parse a schema reference to extract the ID.
 * Format: schema:{schema_id}:{version}
 */
export function parseSchemaRef(ref) {
    if (!ref) return null;
    const parts = ref.split(':');
    if (parts.length >= 2 && parts[0] === 'schema') {
        return parts[1]; // Return the ID part
    }
    return ref;
}

/**
 * Build a mechanical operation reference string.
 * Format: mech:{type}:{op_id}:{version}
 */
export function buildMechOpRef(op) {
    if (!op) return '';
    return `mech:${op.type}:${op.op_id}:${op.active_version || op.version || '1.0.0'}`;
}

/**
 * Parse a mechanical operation reference to extract op_id.
 * Format: mech:{type}:{op_id}:{version}
 */
export function parseMechOpRef(ref) {
    if (!ref) return null;
    const parts = ref.split(':');
    if (parts.length >= 3 && parts[0] === 'mech') {
        return parts[2]; // Return the op_id
    }
    return ref;
}
