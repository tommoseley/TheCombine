/**
 * SynthesisReview — ADR-070 Binder Synthesis operator review UI.
 *
 * Operator-legible presentation of synthesis findings. No system jargon.
 * Severity-led layout with inline evidence (side-by-side for merges).
 * Each finding has accept/refine/dismiss controls.
 */

import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client.js';

// ---------------------------------------------------------------------------
// Severity config
// ---------------------------------------------------------------------------

const SEVERITY = {
  blocking: {
    label: 'BLOCKING',
    color: '#e53935',
    bg: 'rgba(229, 57, 53, 0.08)',
    border: 'rgba(229, 57, 53, 0.3)',
    icon: '\u26D4',
  },
  should_fix: {
    label: 'SHOULD FIX',
    color: '#f9a825',
    bg: 'rgba(249, 168, 37, 0.08)',
    border: 'rgba(249, 168, 37, 0.3)',
    icon: '\u26A0\uFE0F',
  },
  advisory: {
    label: 'ADVISORY',
    color: '#90a4ae',
    bg: 'rgba(144, 164, 174, 0.05)',
    border: 'rgba(144, 164, 174, 0.2)',
    icon: '\u2139\uFE0F',
  },
};

const CONFIDENCE_LABEL = {
  high: 'Both reviewers agree',
  moderate: 'One reviewer flagged',
};

// ---------------------------------------------------------------------------
// Evidence panel (side-by-side for 2 items, stacked for 1 or 3+)
// ---------------------------------------------------------------------------

function EvidencePanel({ evidence }) {
  if (!evidence || evidence.length === 0) return null;

  const isSideBySide = evidence.length === 2;

  return (
    <div style={{
      display: isSideBySide ? 'grid' : 'flex',
      gridTemplateColumns: isSideBySide ? '1fr 1fr' : undefined,
      flexDirection: !isSideBySide ? 'column' : undefined,
      gap: 8,
      marginTop: 12,
    }}>
      {evidence.map((ev, i) => (
        <div key={i} style={{
          background: 'var(--bg-canvas, #0f0f23)',
          border: '1px solid var(--border, #333)',
          borderRadius: 4,
          padding: '10px 12px',
        }}>
          <div style={{
            fontSize: 11,
            fontWeight: 600,
            color: 'var(--text-primary)',
            marginBottom: 6,
          }}>
            {ev.artifact_title}
          </div>
          <div style={{
            fontSize: 12,
            color: 'var(--text-secondary, #ccc)',
            lineHeight: 1.5,
            fontStyle: 'italic',
          }}>
            {ev.excerpt}
          </div>
          <div style={{
            fontSize: 10,
            color: 'var(--text-muted, #666)',
            marginTop: 4,
          }}>
            {ev.artifact_id}
          </div>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Finding card
// ---------------------------------------------------------------------------

function FindingCard({ finding, type, decision, onDecide }) {
  const isAction = type === 'action';
  const sev = SEVERITY[finding.severity] || SEVERITY.advisory;
  const [expanded, setExpanded] = useState(true);

  const id = isAction
    ? `${finding.action_type}-${finding.targets?.join(',')}`
    : finding.finding_id;

  const decided = decision != null;

  return (
    <div style={{
      border: `1px solid ${decided ? 'var(--border, #333)' : sev.border}`,
      borderRadius: 8,
      marginBottom: 12,
      background: decided
        ? decision.decision === 'accept'
          ? 'rgba(76, 175, 80, 0.06)'
          : 'rgba(229, 57, 53, 0.04)'
        : sev.bg,
      opacity: decided ? 0.7 : 1,
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '12px 16px',
          cursor: 'pointer',
        }}
      >
        <span style={{
          fontSize: 11,
          fontWeight: 700,
          color: sev.color,
          letterSpacing: '0.05em',
          flexShrink: 0,
        }}>
          {sev.icon} {sev.label}
        </span>

        <span style={{
          fontSize: 14,
          fontWeight: 600,
          color: 'var(--text-primary)',
          flex: 1,
        }}>
          {finding.headline || finding.rationale}
        </span>

        <span style={{
          fontSize: 10,
          padding: '2px 8px',
          borderRadius: 10,
          background: finding.confidence === 'high'
            ? 'rgba(76, 175, 80, 0.2)'
            : 'rgba(144, 164, 174, 0.15)',
          color: finding.confidence === 'high'
            ? '#81c784'
            : 'var(--text-muted, #888)',
          flexShrink: 0,
        }}>
          {CONFIDENCE_LABEL[finding.confidence] || finding.confidence}
        </span>

        <span style={{
          fontSize: 12,
          color: 'var(--text-muted)',
          transform: expanded ? 'rotate(180deg)' : 'rotate(0)',
          transition: 'transform 0.2s',
        }}>
          &#9660;
        </span>
      </div>

      {/* Body */}
      {expanded && (
        <div style={{ padding: '0 16px 16px' }}>
          {/* Impact */}
          {finding.impact && (
            <p style={{
              fontSize: 13,
              color: 'var(--text-secondary, #ccc)',
              lineHeight: 1.6,
              margin: '0 0 12px',
            }}>
              {finding.impact}
            </p>
          )}

          {/* Evidence */}
          <EvidencePanel evidence={finding.evidence} />

          {/* Suggested fix (actions) or question (judgment) */}
          {isAction && finding.suggested_fix && (
            <div style={{
              marginTop: 12,
              padding: '10px 12px',
              background: 'rgba(76, 175, 80, 0.06)',
              border: '1px solid rgba(76, 175, 80, 0.2)',
              borderRadius: 4,
            }}>
              <div style={{
                fontSize: 11,
                fontWeight: 600,
                color: '#81c784',
                marginBottom: 4,
              }}>
                Suggested fix
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary, #ccc)', lineHeight: 1.5 }}>
                {finding.suggested_fix}
              </div>
            </div>
          )}

          {!isAction && finding.question && (
            <div style={{
              marginTop: 12,
              padding: '10px 12px',
              background: 'rgba(249, 168, 37, 0.06)',
              border: '1px solid rgba(249, 168, 37, 0.2)',
              borderRadius: 4,
            }}>
              <div style={{
                fontSize: 11,
                fontWeight: 600,
                color: '#f9a825',
                marginBottom: 4,
              }}>
                Decision needed
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary, #ccc)', lineHeight: 1.5 }}>
                {finding.question}
              </div>
            </div>
          )}

          {/* Technical details (collapsed) */}
          <details style={{ marginTop: 10 }}>
            <summary style={{
              fontSize: 10,
              color: 'var(--text-muted, #666)',
              cursor: 'pointer',
            }}>
              Technical details
            </summary>
            <div style={{
              fontSize: 10,
              color: 'var(--text-muted, #666)',
              fontFamily: 'monospace',
              marginTop: 4,
              padding: 8,
              background: 'var(--bg-canvas, #0f0f23)',
              borderRadius: 3,
              lineHeight: 1.6,
            }}>
              {isAction && <>
                <div>Action: {finding.action_type}</div>
                <div>Targets: {finding.targets?.join(', ')}</div>
                <div>Post-condition: {finding.post_condition}</div>
              </>}
              {!isAction && <>
                <div>Lens: {finding.lens}</div>
                <div>Finding: {finding.finding_id}</div>
                <div>Artifacts: {finding.artifacts?.join(', ')}</div>
              </>}
            </div>
          </details>

          {/* Actions */}
          {!decided && (
            <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
              <button
                onClick={() => onDecide(id, 'accept')}
                style={{
                  padding: '6px 16px', fontSize: 12, cursor: 'pointer',
                  background: '#4caf50', color: '#fff',
                  border: 'none', borderRadius: 4, fontWeight: 600,
                }}
              >
                {isAction
                  ? (finding.action_type === 'MERGE_WS' ? 'Accept Merge'
                    : finding.action_type === 'DEFER_COMPONENT' ? 'Accept Deferral'
                    : finding.action_type === 'REMOVE_WS' ? 'Accept Removal'
                    : finding.action_type === 'SPLIT_WS' ? 'Accept Split'
                    : 'Accept')
                  : 'Acknowledge'}
              </button>
              <button
                onClick={() => onDecide(id, 'reject')}
                style={{
                  padding: '6px 16px', fontSize: 12, cursor: 'pointer',
                  background: 'transparent', color: 'var(--text-muted, #888)',
                  border: '1px solid var(--border, #444)', borderRadius: 4,
                }}
              >
                Dismiss
              </button>
            </div>
          )}

          {decided && (
            <div style={{
              fontSize: 11, marginTop: 10,
              color: decision.decision === 'accept' ? '#81c784' : 'var(--text-muted, #888)',
              fontWeight: 600,
            }}>
              {decision.decision === 'accept'
                ? (isAction ? 'Accepted' : 'Acknowledged')
                : 'Dismissed'}
              {decision.note && ` \u2014 ${decision.note}`}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

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
      // No delta yet
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => { loadDelta(); }, [loadDelta]);

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

  if (loading) {
    return <div style={{ padding: 24, color: 'var(--text-muted, #888)' }}>Loading synthesis...</div>;
  }

  // Sort findings: blocking first, then should_fix, then advisory
  const severityOrder = { blocking: 0, should_fix: 1, advisory: 2 };
  const sortBySeverity = (a, b) =>
    (severityOrder[a.severity] ?? 3) - (severityOrder[b.severity] ?? 3);

  const actions = delta?.actions ? [...delta.actions].sort(sortBySeverity) : [];
  const questions = delta?.questions ? [...delta.questions].sort(sortBySeverity) : [];
  const totalFindings = actions.length + questions.length;

  return (
    <div style={{ padding: '16px 20px', maxWidth: 1200, margin: '0 auto' }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 20,
      }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 17, color: 'var(--text-primary)' }}>
            Synthesis Review
          </h2>
          {delta && (
            <div style={{ fontSize: 12, color: 'var(--text-muted, #888)', marginTop: 4 }}>
              {totalFindings} {totalFindings === 1 ? 'tension' : 'tensions'} detected
              {' \u2022 '}
              {delta.agreement_count} confirmed by both reviewers
            </div>
          )}
        </div>
        <button
          onClick={runSynthesis}
          disabled={running}
          style={{
            padding: '8px 20px', fontSize: 12, cursor: running ? 'wait' : 'pointer',
            background: running ? 'var(--text-muted, #666)' : 'var(--accent-primary, #3b82f6)',
            color: '#fff',
            border: 'none', borderRadius: 4, fontWeight: 600,
            opacity: running ? 0.6 : 1,
          }}
        >
          {running ? 'Running synthesis...' : delta ? 'Re-run Synthesis' : 'Run Synthesis'}
        </button>
      </div>

      {error && (
        <div style={{
          padding: 12, marginBottom: 16,
          background: 'rgba(229, 57, 53, 0.08)',
          border: '1px solid rgba(229, 57, 53, 0.3)',
          borderRadius: 4, fontSize: 12, color: '#e53935',
        }}>
          {error}
        </div>
      )}

      {!delta && !running && (
        <div style={{
          textAlign: 'center',
          padding: '40px 20px',
          color: 'var(--text-muted, #888)',
        }}>
          <p style={{ fontSize: 14, marginBottom: 8 }}>
            No synthesis review yet.
          </p>
          <p style={{ fontSize: 12 }}>
            Run synthesis after the Work Binder is assembled to check for
            overlaps, gaps, and issues across the plan.
          </p>
        </div>
      )}

      {delta && (
        <div>
          {/* Actions section */}
          {actions.length > 0 && (
            <div style={{ marginBottom: 24 }}>
              <h3 style={{
                fontSize: 13,
                fontWeight: 600,
                color: 'var(--text-muted, #888)',
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                marginBottom: 12,
              }}>
                Proposed Changes ({actions.length})
              </h3>
              {actions.map((action, i) => {
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
            </div>
          )}

          {/* Questions section */}
          {questions.length > 0 && (
            <div>
              <h3 style={{
                fontSize: 13,
                fontWeight: 600,
                color: 'var(--text-muted, #888)',
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                marginBottom: 12,
              }}>
                Decisions Needed ({questions.length})
              </h3>
              {questions.map((question, i) => (
                <FindingCard
                  key={i}
                  finding={question}
                  type="question"
                  decision={decisions[question.finding_id]}
                  onDecide={handleDecide}
                />
              ))}
            </div>
          )}

          {totalFindings === 0 && (
            <div style={{
              textAlign: 'center',
              padding: '40px 20px',
              color: 'var(--text-muted, #888)',
            }}>
              <p style={{ fontSize: 14 }}>No tensions detected.</p>
              <p style={{ fontSize: 12 }}>
                The binder appears coherent across all checked dimensions.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
