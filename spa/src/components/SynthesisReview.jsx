/**
 * SynthesisReview — ADR-070 Binder Synthesis operator review UI.
 *
 * Two-lane display: mechanical actions (left) and judgment questions (right).
 * Each finding has accept/reject controls. Synthesis is triggered from the
 * binder view after assembly.
 */

import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client.js';

const SEVERITY_COLORS = {
  blocking: 'var(--error, #e53935)',
  should_fix: 'var(--warning, #f9a825)',
  advisory: 'var(--text-muted, #888)',
};

const CONFIDENCE_LABEL = {
  high: 'Both instances agree',
  moderate: 'One instance flagged',
};

function FindingCard({ finding, type, decision, onDecide }) {
  const isAction = type === 'action';
  const id = isAction
    ? `${finding.action_type}-${finding.targets?.join(',')}`
    : finding.finding_id;

  const decided = decision != null;
  const cardStyle = {
    border: '1px solid var(--border, #333)',
    borderRadius: 6,
    padding: '12px 16px',
    marginBottom: 8,
    background: decided
      ? decision.decision === 'accept'
        ? 'var(--success-bg, #1b3a1b)'
        : 'var(--error-bg, #3a1b1b)'
      : 'var(--bg-panel, #1e1e1e)',
    opacity: decided ? 0.7 : 1,
  };

  return (
    <div style={cardStyle}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <strong style={{ fontSize: 13 }}>
          {isAction ? finding.action_type : finding.lens?.replace(/_/g, ' ')}
        </strong>
        <span style={{
          fontSize: 11,
          padding: '2px 6px',
          borderRadius: 3,
          background: finding.confidence === 'high' ? 'var(--success, #4caf50)' : 'var(--surface-secondary, #333)',
          color: '#fff',
        }}>
          {CONFIDENCE_LABEL[finding.confidence] || finding.confidence}
        </span>
      </div>

      {isAction && (
        <>
          <div style={{ fontSize: 12, marginBottom: 4 }}>
            <span style={{ color: 'var(--text-muted, #888)' }}>Targets: </span>
            {finding.targets?.join(', ')}
          </div>
          <div style={{ fontSize: 12, marginBottom: 4 }}>{finding.rationale}</div>
          <div style={{ fontSize: 11, color: 'var(--text-muted, #888)', fontFamily: 'monospace' }}>
            Post-condition: {finding.post_condition}
          </div>
        </>
      )}

      {!isAction && (
        <>
          <div style={{ fontSize: 12, marginBottom: 4 }}>
            <span style={{
              color: SEVERITY_COLORS[finding.severity] || '#888',
              fontWeight: 600,
              fontSize: 11,
              textTransform: 'uppercase',
            }}>
              {finding.severity}
            </span>
            {' '}
            <span style={{ color: 'var(--text-muted, #888)' }}>
              [{finding.artifacts?.join(', ')}]
            </span>
          </div>
          <div style={{ fontSize: 12 }}>{finding.question}</div>
        </>
      )}

      {!decided && (
        <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
          <button
            onClick={() => onDecide(id, 'accept')}
            style={{
              padding: '4px 12px', fontSize: 11, cursor: 'pointer',
              background: 'var(--success, #4caf50)', color: '#fff',
              border: 'none', borderRadius: 3,
            }}
          >
            Accept
          </button>
          <button
            onClick={() => onDecide(id, 'reject')}
            style={{
              padding: '4px 12px', fontSize: 11, cursor: 'pointer',
              background: 'var(--error, #e53935)', color: '#fff',
              border: 'none', borderRadius: 3,
            }}
          >
            Reject
          </button>
        </div>
      )}

      {decided && (
        <div style={{ fontSize: 11, marginTop: 6, color: 'var(--text-muted, #888)' }}>
          {decision.decision === 'accept' ? 'Accepted' : 'Rejected'}
          {decision.note && ` — ${decision.note}`}
        </div>
      )}
    </div>
  );
}

export default function SynthesisReview({ projectId }) {
  const [delta, setDelta] = useState(null);
  const [decisions, setDecisions] = useState({});
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);

  const loadDelta = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const result = await api.getSynthesisDelta(projectId);
      if (result) {
        setDelta(result.content);
        setDecisions(result.operator_decisions || {});
      }
    } catch {
      // No delta yet — that's fine
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadDelta();
  }, [loadDelta]);

  const runSynthesis = async () => {
    setRunning(true);
    setError(null);
    try {
      await api.triggerSynthesis(projectId);
      await loadDelta();
    } catch (err) {
      setError(err.message || 'Synthesis failed');
    } finally {
      setRunning(false);
    }
  };

  const handleDecide = async (findingId, decision) => {
    try {
      await api.recordFindingDecision(projectId, findingId, decision);
      setDecisions(prev => ({
        ...prev,
        [findingId]: { decision, decided_at: new Date().toISOString() },
      }));
    } catch (err) {
      setError(err.message || 'Failed to record decision');
    }
  };

  if (loading) return <div style={{ padding: 16, color: 'var(--text-muted, #888)' }}>Loading synthesis...</div>;

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h3 style={{ margin: 0, fontSize: 15 }}>Binder Synthesis (ADR-070)</h3>
        <button
          onClick={runSynthesis}
          disabled={running}
          style={{
            padding: '6px 16px', fontSize: 12, cursor: running ? 'wait' : 'pointer',
            background: 'var(--primary, #1976d2)', color: '#fff',
            border: 'none', borderRadius: 4, opacity: running ? 0.6 : 1,
          }}
        >
          {running ? 'Running synthesis...' : delta ? 'Re-run Synthesis' : 'Run Synthesis'}
        </button>
      </div>

      {error && (
        <div style={{ padding: 8, marginBottom: 12, background: 'var(--error-bg, #3a1b1b)', borderRadius: 4, fontSize: 12, color: 'var(--error, #e53935)' }}>
          {error}
        </div>
      )}

      {!delta && !running && (
        <div style={{ color: 'var(--text-muted, #888)', fontSize: 13 }}>
          No synthesis delta yet. Run synthesis after the binder is assembled.
        </div>
      )}

      {delta && (
        <>
          <div style={{ fontSize: 12, color: 'var(--text-muted, #888)', marginBottom: 16 }}>
            {delta.binder_document_count} documents analyzed |
            Instance A: {delta.instance_a_finding_count} findings |
            Instance B: {delta.instance_b_finding_count} findings |
            {delta.agreement_count} agreements
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div>
              <h4 style={{ margin: '0 0 8px', fontSize: 13, color: 'var(--success, #4caf50)' }}>
                Mechanical Actions ({delta.actions?.length || 0})
              </h4>
              {(delta.actions || []).map((action, i) => {
                const id = `${action.action_type}-${action.targets?.join(',')}`;
                return (
                  <FindingCard
                    key={i}
                    finding={action}
                    type="action"
                    decision={decisions[id]}
                    onDecide={handleDecide}
                  />
                );
              })}
              {(!delta.actions || delta.actions.length === 0) && (
                <div style={{ fontSize: 12, color: 'var(--text-muted, #888)' }}>No mechanical actions</div>
              )}
            </div>

            <div>
              <h4 style={{ margin: '0 0 8px', fontSize: 13, color: 'var(--warning, #f9a825)' }}>
                Judgment Questions ({delta.questions?.length || 0})
              </h4>
              {(delta.questions || []).map((question, i) => (
                <FindingCard
                  key={i}
                  finding={question}
                  type="question"
                  decision={decisions[question.finding_id]}
                  onDecide={handleDecide}
                />
              ))}
              {(!delta.questions || delta.questions.length === 0) && (
                <div style={{ fontSize: 12, color: 'var(--text-muted, #888)' }}>No judgment questions</div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
