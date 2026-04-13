/** Extract first string value from an object */
export function extractText(obj) {
    if (typeof obj === 'string') return obj;
    if (typeof obj !== 'object' || obj === null) return String(obj);
    for (const v of Object.values(obj)) {
        if (typeof v === 'string' && v.length > 10) return v;
    }
    return JSON.stringify(obj);
}

/** Convert snake_case key to Title Case label */
export function formatLabel(key) {
    return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}
