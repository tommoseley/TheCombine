import { useState, useEffect } from 'react';

const API_BASE = '/api/v1';

/**
 * Cost Dashboard - displays daily cost breakdown and summary totals.
 * Consumes GET /api/v1/telemetry/costs?days=N
 */
export default function CostDashboard() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [days, setDays] = useState(7);

    useEffect(() => {
        loadData();
    }, [days]);

    async function loadData() {
        setLoading(true);
        setError(null);
        try {
            const response = await fetch(`${API_BASE}/telemetry/costs?days=${days}`, {
                credentials: 'same-origin',
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const json = await response.json();
            setData(json);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full">
                <p style={{ color: 'var(--text-muted)' }}>Loading cost data...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-6">
                <div className="p-3 rounded text-sm" style={{ background: '#fecaca', color: '#991b1b' }}>
                    Failed to load cost data: {error}
                </div>
            </div>
        );
    }

    const summary = data?.summary || {};
    const dailyData = data?.daily_data || [];

    return (
        <div className="h-full overflow-auto p-6">
            {/* Period selector */}
            <div className="flex items-center gap-3 mb-6">
                <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Period:</span>
                {[7, 14, 30].map(d => (
                    <button
                        key={d}
                        onClick={() => setDays(d)}
                        className="text-xs px-3 py-1.5 rounded transition-opacity"
                        style={{
                            background: days === d ? 'var(--accent-primary)' : 'transparent',
                            color: days === d ? 'white' : 'var(--text-muted)',
                            border: days === d ? 'none' : '1px solid var(--border-panel)',
                        }}
                    >
                        {d} days
                    </button>
                ))}
                <button
                    onClick={loadData}
                    className="text-xs px-3 py-1 rounded hover:opacity-80 transition-opacity ml-auto"
                    style={{ color: 'var(--text-muted)', border: '1px solid var(--border-panel)' }}
                >
                    Refresh
                </button>
            </div>

            {/* Summary cards */}
            <div className="grid grid-cols-4 gap-4 mb-6">
                <SummaryCard label="Total Cost" value={`$${(summary.total_cost || 0).toFixed(2)}`} />
                <SummaryCard label="Total Tokens" value={(summary.total_tokens || 0).toLocaleString()} />
                <SummaryCard label="Total Calls" value={summary.total_calls || 0} />
                <SummaryCard label="Avg Cost/Day" value={`$${(summary.avg_cost_per_day || 0).toFixed(2)}`} />
            </div>

            {/* Daily breakdown table */}
            <div className="rounded" style={{ border: '1px solid var(--border-panel)' }}>
                <table className="w-full text-sm" style={{ color: 'var(--text-primary)' }}>
                    <thead>
                        <tr className="border-b" style={{ borderColor: 'var(--border-panel)', background: 'var(--bg-panel)' }}>
                            <th className="text-left p-3 font-medium text-xs" style={{ color: 'var(--text-muted)' }}>Date</th>
                            <th className="text-right p-3 font-medium text-xs" style={{ color: 'var(--text-muted)' }}>Cost</th>
                            <th className="text-right p-3 font-medium text-xs" style={{ color: 'var(--text-muted)' }}>Tokens</th>
                            <th className="text-right p-3 font-medium text-xs" style={{ color: 'var(--text-muted)' }}>Calls</th>
                            <th className="text-right p-3 font-medium text-xs" style={{ color: 'var(--text-muted)' }}>Errors</th>
                            <th className="text-right p-3 font-medium text-xs" style={{ color: 'var(--text-muted)' }}>Workflow</th>
                            <th className="text-right p-3 font-medium text-xs" style={{ color: 'var(--text-muted)' }}>Document</th>
                        </tr>
                    </thead>
                    <tbody>
                        {dailyData.map((day, i) => (
                            <tr key={i} className="border-b" style={{ borderColor: 'var(--border-panel)' }}>
                                <td className="p-3 text-xs">{day.date_short || day.date}</td>
                                <td className="p-3 text-xs text-right font-mono">${(day.cost || 0).toFixed(4)}</td>
                                <td className="p-3 text-xs text-right font-mono">{(day.tokens || 0).toLocaleString()}</td>
                                <td className="p-3 text-xs text-right">{day.calls || 0}</td>
                                <td className="p-3 text-xs text-right"
                                    style={{ color: day.errors > 0 ? 'var(--state-error, #ef4444)' : 'var(--text-muted)' }}>
                                    {day.errors || 0}
                                </td>
                                <td className="p-3 text-xs text-right font-mono">${(day.workflow_cost || 0).toFixed(4)}</td>
                                <td className="p-3 text-xs text-right font-mono">${(day.document_cost || 0).toFixed(4)}</td>
                            </tr>
                        ))}
                        {dailyData.length === 0 && (
                            <tr>
                                <td colSpan={7} className="p-8 text-center" style={{ color: 'var(--text-muted)' }}>
                                    No cost data for this period.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

function SummaryCard({ label, value }) {
    return (
        <div className="p-4 rounded" style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-panel)' }}>
            <div className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>{label}</div>
            <div className="text-lg font-medium font-mono" style={{ color: 'var(--text-primary)' }}>{value}</div>
        </div>
    );
}
