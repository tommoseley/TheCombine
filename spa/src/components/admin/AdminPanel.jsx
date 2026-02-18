import { useState, useEffect } from 'react';
import { useAuth } from '../../hooks';
import ExecutionList from './ExecutionList';
import ExecutionDetail from './ExecutionDetail';
import CostDashboard from './CostDashboard';

/**
 * Admin Panel - operational monitoring for executions, costs, and system health.
 *
 * This is separate from AdminWorkbench (prompt/config editing).
 * AdminPanel provides the operational visibility that was previously
 * served by the HTMX admin section.
 */
export default function AdminPanel() {
    const { isAdmin, loading: authLoading } = useAuth();
    const [activeTab, setActiveTab] = useState('executions');
    const [selectedExecutionId, setSelectedExecutionId] = useState(null);

    // Check URL for deep links:
    //   /admin?execution=xxx (query param)
    //   /admin/executions/xxx (path param)
    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const executionParam = params.get('execution');
        if (executionParam) {
            setSelectedExecutionId(executionParam);
            setActiveTab('executions');
            return;
        }
        // Parse /admin/executions/{id} from path
        const pathMatch = window.location.pathname.match(/^\/admin\/executions\/(.+)$/);
        if (pathMatch) {
            setSelectedExecutionId(pathMatch[1]);
            setActiveTab('executions');
        }
    }, []);

    if (authLoading) {
        return (
            <div className="flex h-screen items-center justify-center"
                 style={{ background: 'var(--bg-canvas)' }}>
                <p style={{ color: 'var(--text-muted)' }}>Loading...</p>
            </div>
        );
    }

    if (!isAdmin) {
        return (
            <div className="flex h-screen items-center justify-center"
                 style={{ background: 'var(--bg-canvas)' }}>
                <div className="text-center p-6 rounded-lg" style={{ background: 'var(--bg-panel)' }}>
                    <p style={{ color: 'var(--text-primary)' }}>Admin access required.</p>
                    <a href="/" className="text-sm mt-2 inline-block"
                       style={{ color: 'var(--accent-primary)' }}>
                        Return to Production Floor
                    </a>
                </div>
            </div>
        );
    }

    const tabs = [
        { id: 'executions', label: 'Executions' },
        { id: 'costs', label: 'Costs' },
    ];

    return (
        <div className="flex flex-col h-screen" style={{ background: 'var(--bg-canvas)' }}>
            {/* Header */}
            <header
                className="h-12 flex items-center justify-between px-4 border-b flex-shrink-0"
                style={{ background: 'var(--bg-panel)', borderColor: 'var(--border-panel)' }}
            >
                <div className="flex items-center gap-4">
                    <a href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
                        <img src="/logo-256.png" alt="The Combine" className="h-7 w-7" />
                        <span className="text-sm font-bold tracking-wide"
                              style={{ color: 'var(--text-primary)' }}>
                            THE COMBINE
                        </span>
                    </a>
                    <span className="text-xs px-2 py-0.5 rounded"
                          style={{
                              background: 'var(--accent-primary)',
                              color: 'white',
                              opacity: 0.9
                          }}>
                        ADMIN
                    </span>
                </div>
                <div className="flex items-center gap-3">
                    <a href="/admin/workbench"
                       className="text-xs px-3 py-1.5 rounded hover:opacity-80 transition-opacity"
                       style={{ color: 'var(--text-muted)', border: '1px solid var(--border-panel)' }}>
                        Workbench
                    </a>
                    <a href="/"
                       className="text-xs px-3 py-1.5 rounded hover:opacity-80 transition-opacity"
                       style={{ color: 'var(--text-muted)', border: '1px solid var(--border-panel)' }}>
                        Production Floor
                    </a>
                </div>
            </header>

            {/* Tab bar */}
            <div className="flex border-b px-4 flex-shrink-0"
                 style={{ background: 'var(--bg-panel)', borderColor: 'var(--border-panel)' }}>
                {tabs.map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => {
                            setActiveTab(tab.id);
                            if (tab.id !== 'executions') setSelectedExecutionId(null);
                        }}
                        className="px-4 py-2 text-sm transition-colors relative"
                        style={{
                            color: activeTab === tab.id ? 'var(--text-primary)' : 'var(--text-muted)',
                            fontWeight: activeTab === tab.id ? 600 : 400,
                        }}
                    >
                        {tab.label}
                        {activeTab === tab.id && (
                            <div className="absolute bottom-0 left-0 right-0 h-0.5"
                                 style={{ background: 'var(--accent-primary)' }} />
                        )}
                    </button>
                ))}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-hidden">
                {activeTab === 'executions' && (
                    selectedExecutionId ? (
                        <ExecutionDetail
                            executionId={selectedExecutionId}
                            onBack={() => setSelectedExecutionId(null)}
                        />
                    ) : (
                        <ExecutionList
                            onSelectExecution={setSelectedExecutionId}
                        />
                    )
                )}
                {activeTab === 'costs' && <CostDashboard />}
            </div>
        </div>
    );
}
