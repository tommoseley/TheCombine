import React from 'react';

/**
 * Display tier 1 validation results.
 */
export default function ValidationResults({ results, compact = false }) {
    if (!results || results.length === 0) {
        return null;
    }

    const failingResults = results.filter(r => r.status === 'fail');
    const passingResults = results.filter(r => r.status === 'pass');

    if (compact) {
        return (
            <div className="flex items-center gap-2">
                {failingResults.length > 0 ? (
                    <span
                        className="text-xs px-2 py-0.5 rounded"
                        style={{ background: 'var(--state-error-bg)', color: 'var(--state-error-text)' }}
                    >
                        {failingResults.length} error{failingResults.length !== 1 ? 's' : ''}
                    </span>
                ) : (
                    <span
                        className="text-xs px-2 py-0.5 rounded"
                        style={{ background: 'var(--state-success-bg)', color: 'var(--state-success-text)' }}
                    >
                        Valid
                    </span>
                )}
            </div>
        );
    }

    return (
        <div className="space-y-2">
            {failingResults.map((result, i) => (
                <div
                    key={i}
                    className="text-xs p-2 rounded border"
                    style={{
                        background: 'rgba(239, 68, 68, 0.1)',
                        borderColor: 'var(--state-error-bg)',
                        color: 'var(--text-primary)',
                    }}
                >
                    <div className="flex items-center gap-2 font-medium">
                        <span className="text-red-400">FAIL</span>
                        <span className="font-mono">{result.rule_id}</span>
                    </div>
                    {result.message && (
                        <div className="mt-1 opacity-80">{result.message}</div>
                    )}
                    {result.artifact_id && (
                        <div className="mt-1 font-mono text-xs opacity-60">
                            {result.artifact_id}
                        </div>
                    )}
                </div>
            ))}
            {passingResults.length > 0 && failingResults.length > 0 && (
                <div
                    className="text-xs p-2 rounded"
                    style={{ background: 'rgba(34, 197, 94, 0.1)', color: 'var(--text-muted)' }}
                >
                    {passingResults.length} rule{passingResults.length !== 1 ? 's' : ''} passed
                </div>
            )}
        </div>
    );
}
