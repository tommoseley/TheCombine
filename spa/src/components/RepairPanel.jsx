/**
 * RepairPanel — shows TA ownership findings with repair actions (ADR-065).
 *
 * Renders:
 * - Advisory ownership-gap indicator when findings exist
 * - Per-finding "Repair" button
 * - Proposal review (before/after diff) when proposal exists
 * - Accept / Reject / Regenerate actions
 */
import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';

function DiffView({ before, after }) {
    return (
        <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
            <div>
                <div className="text-[10px] uppercase tracking-wider mb-1" style={{ color: 'var(--text-muted)' }}>Before</div>
                <pre
                    className="p-2 rounded overflow-auto max-h-48"
                    style={{ background: 'var(--bg-canvas)', color: 'var(--text-secondary)', border: '1px solid var(--border-node)' }}
                >
                    {JSON.stringify(before, null, 2)}
                </pre>
            </div>
            <div>
                <div className="text-[10px] uppercase tracking-wider mb-1" style={{ color: 'var(--text-muted)' }}>After</div>
                <pre
                    className="p-2 rounded overflow-auto max-h-48"
                    style={{ background: 'var(--bg-canvas)', color: '#4ade80', border: '1px solid var(--border-node)' }}
                >
                    {JSON.stringify(after, null, 2)}
                </pre>
            </div>
        </div>
    );
}

export default function RepairPanel({ artifactId, findings, components }) {
    const [proposals, setProposals] = useState([]);
    const [loading, setLoading] = useState({});
    const [error, setError] = useState(null);

    // Fetch existing proposals
    const fetchProposals = useCallback(async () => {
        if (!artifactId) return;
        try {
            const data = await api.getRepairProposals(artifactId);
            setProposals(data);
        } catch (err) {
            console.error('Failed to fetch proposals:', err);
        }
    }, [artifactId]);

    useEffect(() => { fetchProposals(); }, [fetchProposals]);

    const handleRepair = async (componentName) => {
        setLoading(prev => ({ ...prev, [componentName]: true }));
        setError(null);
        try {
            await api.requestRepair(artifactId, componentName);
            await fetchProposals();
        } catch (err) {
            setError(err.data?.error || err.message || 'Repair request failed');
        } finally {
            setLoading(prev => ({ ...prev, [componentName]: false }));
        }
    };

    const handleDecide = async (proposalId, decision) => {
        setLoading(prev => ({ ...prev, [proposalId]: true }));
        try {
            await api.decideProposal(proposalId, decision);
            await fetchProposals();
        } catch (err) {
            setError(err.data?.error || err.message || 'Decision failed');
        } finally {
            setLoading(prev => ({ ...prev, [proposalId]: false }));
        }
    };

    if (!findings || findings.length === 0) return null;

    // Map proposals by component name for quick lookup
    const proposalsByComponent = {};
    for (const p of proposals) {
        if (p.status === 'pending') {
            proposalsByComponent[p.component_identifier] = p;
        }
    }

    return (
        <div
            className="rounded-lg border p-3 mt-3"
            style={{ background: 'var(--bg-node)', borderColor: 'var(--border-node)' }}
        >
            <div className="flex items-center gap-2 mb-2">
                <span
                    className="text-[10px] font-medium uppercase tracking-wider"
                    style={{ color: 'var(--text-muted)' }}
                >
                    Ownership Gaps
                </span>
                <span
                    className="text-[10px] px-1.5 py-0.5 rounded-full"
                    style={{ background: '#f59e0b33', color: '#f59e0b' }}
                >
                    {findings.length} advisory
                </span>
            </div>

            {error && (
                <div className="text-[11px] mb-2 p-1.5 rounded" style={{ background: '#ef444433', color: '#ef4444' }}>
                    {error}
                </div>
            )}

            {findings.map((f, i) => {
                const proposal = proposalsByComponent[f.component_name];
                const isLoading = loading[f.component_name] || (proposal && loading[proposal.id]);
                const originalComponent = components?.find(c => c.name === f.component_name);

                return (
                    <div
                        key={i}
                        className="border-t pt-2 mt-2"
                        style={{ borderColor: 'var(--border-node)' }}
                    >
                        <div className="flex items-center justify-between">
                            <div>
                                <span className="text-[12px] font-medium" style={{ color: 'var(--text-primary)' }}>
                                    {f.component_name}
                                </span>
                                <span className="text-[11px] ml-2" style={{ color: 'var(--text-muted)' }}>
                                    {f.issue_type}
                                </span>
                            </div>
                            {!proposal && (
                                <button
                                    className="text-[10px] px-2 py-1 rounded border transition-colors hover:opacity-80"
                                    style={{
                                        color: '#f59e0b',
                                        borderColor: '#f59e0b44',
                                        background: 'transparent',
                                        cursor: isLoading ? 'wait' : 'pointer',
                                    }}
                                    disabled={isLoading}
                                    onClick={() => handleRepair(f.component_name)}
                                >
                                    {isLoading ? 'Repairing...' : 'Repair'}
                                </button>
                            )}
                        </div>

                        {/* Proposal review */}
                        {proposal && (
                            <div className="mt-2">
                                <DiffView
                                    before={originalComponent || {}}
                                    after={proposal.proposed_payload}
                                />
                                <div className="flex gap-2 mt-2">
                                    <button
                                        className="text-[10px] px-2 py-1 rounded border"
                                        style={{ color: '#4ade80', borderColor: '#4ade8044', background: 'transparent' }}
                                        disabled={isLoading}
                                        onClick={() => handleDecide(proposal.id, 'accept')}
                                    >
                                        Accept
                                    </button>
                                    <button
                                        className="text-[10px] px-2 py-1 rounded border"
                                        style={{ color: '#ef4444', borderColor: '#ef444444', background: 'transparent' }}
                                        disabled={isLoading}
                                        onClick={() => handleDecide(proposal.id, 'reject')}
                                    >
                                        Reject
                                    </button>
                                    <button
                                        className="text-[10px] px-2 py-1 rounded border"
                                        style={{ color: 'var(--text-muted)', borderColor: 'var(--border-node)', background: 'transparent' }}
                                        disabled={isLoading}
                                        onClick={() => handleDecide(proposal.id, 'regenerate')}
                                    >
                                        Regenerate
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                );
            })}
        </div>
    );
}
