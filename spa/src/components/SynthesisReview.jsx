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
// Advisor panel — inline "Need more info" expansion
// ---------------------------------------------------------------------------

const ADVISOR_SECTIONS = [
  { key: 'whats_happening', label: "What's happening" },
  { key: 'what_the_plan_says', label: 'What the plan says' },
  { key: 'whats_missing', label: "What's missing" },
  { key: 'options_and_tradeoffs', label: 'Options and trade-offs' },
  { key: 'impact', label: 'Impact of your decision' },
];

function AdvisorPanel({ data, loading, error }) {
  if (loading) {
    return (
      <div style={{
        marginTop: 12, padding: 16,
        background: 'rgba(59, 130, 246, 0.06)',
        border: '1px solid rgba(59, 130, 246, 0.2)',
        borderRadius: 6, fontSize: 12,
        color: 'var(--text-muted, #888)',
      }}>
        Analyzing binder context...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        marginTop: 12, padding: 12,
        background: 'rgba(229, 57, 53, 0.06)',
        border: '1px solid rgba(229, 57, 53, 0.2)',
        borderRadius: 4, fontSize: 12, color: '#e53935',
      }}>
        {error}
      </div>
    );
  }

  if (!data) return null;

  return (
    <div style={{
      marginTop: 12,
      border: '1px solid rgba(59, 130, 246, 0.25)',
      borderRadius: 6,
      overflow: 'hidden',
    }}>
      <div style={{
        padding: '8px 12px',
        background: 'rgba(59, 130, 246, 0.08)',
        fontSize: 11, fontWeight: 600,
        color: 'var(--accent-primary, #3b82f6)',
        borderBottom: '1px solid rgba(59, 130, 246, 0.15)',
      }}>
        Decision context
      </div>
      {ADVISOR_SECTIONS.map(({ key, label }) => {
        const text = data[key];
        if (!text) return null;
        return (
          <div key={key} style={{
            padding: '10px 12px',
            borderBottom: '1px solid rgba(59, 130, 246, 0.08)',
          }}>
            <div style={{
              fontSize: 11, fontWeight: 600,
              color: 'var(--accent-primary, #3b82f6)',
              marginBottom: 4,
            }}>
              {label}
            </div>
            <div style={{
              fontSize: 12, color: 'var(--text-secondary, #ccc)',
              lineHeight: 1.6, whiteSpace: 'pre-wrap',
            }}>
              {text}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Option parser — extracts selectable options from advisor tradeoffs text
// ---------------------------------------------------------------------------

function parseAdvisorOptions(text) {
  if (!text) return [];
  const options = [];
  const lines = text.split('\n');
  let current = null;
  let optNum = 0;

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      // blank line can separate options
      continue;
    }

    // Match "Option N: ..." or "- Option N: ..."
    const numberedMatch = trimmed.match(/^-?\s*Option\s+(\d+):\s*(.+)/i);
    if (numberedMatch) {
      if (current) options.push(current);
      optNum++;
      current = { id: `option_${numberedMatch[1]}`, label: trimmed.replace(/^-\s*/, ''), details: [] };
      continue;
    }

    // Match detail lines (start with "- Pros:" or "- Cons:" or just "- ")
    const isDetail = trimmed.startsWith('- ');
    if (isDetail && current) {
      current.details.push(trimmed);
      continue;
    }

    // Non-detail, non-blank, non-option-numbered line = new option header
    // (handles "Use Apple's Natural Language Framework built-in models:" style)
    if (!isDetail && trimmed.endsWith(':')) {
      if (current) options.push(current);
      optNum++;
      current = { id: `option_${optNum}`, label: trimmed.replace(/:$/, ''), details: [] };
      continue;
    }

    // Fallback: if it's a non-detail line that doesn't end with ":", treat as new option
    if (!isDetail && !current) {
      optNum++;
      current = { id: `option_${optNum}`, label: trimmed, details: [] };
    } else if (current) {
      current.details.push(trimmed);
    }
  }
  if (current) options.push(current);
  return options;
}

// ---------------------------------------------------------------------------
// Finding card
// ---------------------------------------------------------------------------

function FindingCard({ finding, type, decision, onDecide, projectId }) {
  const isAction = type === 'action';
  const sev = SEVERITY[finding.severity] || SEVERITY.advisory;
  const [expanded, setExpanded] = useState(true);
  const [resolving, setResolving] = useState(false);
  const [resolveText, setResolveText] = useState('');
  const [advisorData, setAdvisorData] = useState(null);
  const [advisorLoading, setAdvisorLoading] = useState(false);
  const [advisorError, setAdvisorError] = useState(null);
  const [selectedOption, setSelectedOption] = useState(null);
  const [refineText, setRefineText] = useState('');

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
                Decision required
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary, #ccc)', lineHeight: 1.5 }}>
                {finding.question}
              </div>
            </div>
          )}

          {/* Advisor — Need more info */}
          {!decided && !advisorData && !advisorLoading && (
            <button
              onClick={async () => {
                setAdvisorLoading(true);
                setAdvisorError(null);
                try {
                  const result = await api.explainFinding(projectId, id);
                  setAdvisorData(result);
                } catch (err) {
                  setAdvisorError(err.message || 'Failed to get advisor context');
                } finally {
                  setAdvisorLoading(false);
                }
              }}
              style={{
                marginTop: 12, padding: '6px 14px',
                fontSize: 11, cursor: 'pointer',
                background: 'transparent',
                color: 'var(--accent-primary, #3b82f6)',
                border: '1px solid rgba(59, 130, 246, 0.3)',
                borderRadius: 4, fontWeight: 600,
              }}
            >
              Need more info
            </button>
          )}

          <AdvisorPanel
            data={advisorData}
            loading={advisorLoading}
            error={advisorError}
          />

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
          {!decided && !resolving && (
            <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
              {isAction ? (
                advisorData ? (
                  <button
                    onClick={() => setResolving(true)}
                    style={{
                      padding: '6px 16px', fontSize: 12, cursor: 'pointer',
                      background: '#4caf50', color: '#fff',
                      border: 'none', borderRadius: 4, fontWeight: 600,
                    }}
                  >
                    {finding.action_type === 'MERGE_WS' ? 'Accept Merge'
                      : finding.action_type === 'DEFER_COMPONENT' ? 'Accept Deferral'
                      : finding.action_type === 'REMOVE_WS' ? 'Accept Removal'
                      : finding.action_type === 'SPLIT_WS' ? 'Accept Split'
                      : 'Accept'}
                  </button>
                ) : (
                  <button
                    onClick={() => onDecide(id, 'accept')}
                    style={{
                      padding: '6px 16px', fontSize: 12, cursor: 'pointer',
                      background: '#4caf50', color: '#fff',
                      border: 'none', borderRadius: 4, fontWeight: 600,
                    }}
                  >
                    {finding.action_type === 'MERGE_WS' ? 'Accept Merge'
                      : finding.action_type === 'DEFER_COMPONENT' ? 'Accept Deferral'
                      : finding.action_type === 'REMOVE_WS' ? 'Accept Removal'
                      : finding.action_type === 'SPLIT_WS' ? 'Accept Split'
                      : 'Accept'}
                  </button>
                )
              ) : (
                <button
                  onClick={() => setResolving(true)}
                  style={{
                    padding: '6px 16px', fontSize: 12, cursor: 'pointer',
                    background: '#4caf50', color: '#fff',
                    border: 'none', borderRadius: 4, fontWeight: 600,
                  }}
                >
                  Resolve
                </button>
              )}
              <button
                onClick={() => onDecide(id, 'reject')}
                style={{
                  padding: '6px 16px', fontSize: 12, cursor: 'pointer',
                  background: 'transparent', color: 'var(--text-muted, #888)',
                  border: '1px solid var(--border, #444)', borderRadius: 4,
                }}
              >
                Mark as Intentional
              </button>
            </div>
          )}

          {/* Resolve input — structured options for actions w/ advisor, freeform for questions */}
          {!decided && resolving && (() => {
            const advisorOptions = advisorData ? parseAdvisorOptions(advisorData.options_and_tradeoffs) : [];
            const hasStructuredOptions = advisorOptions.length > 0;

            // Build the final note from selection + refinement
            const buildNote = () => {
              if (hasStructuredOptions) {
                if (selectedOption === 'custom') return refineText;
                const opt = advisorOptions.find(o => o.id === selectedOption);
                const base = opt ? opt.label : selectedOption;
                return refineText ? `${base} — ${refineText}` : base;
              }
              return resolveText;
            };

            const canSubmit = hasStructuredOptions
              ? (selectedOption && (selectedOption !== 'custom' || refineText.trim()))
              : resolveText.trim();

            return (
              <div style={{ marginTop: 14 }}>
                {hasStructuredOptions ? (
                  <>
                    <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary, #ccc)', marginBottom: 8 }}>
                      Which approach?
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {advisorOptions.map((opt) => (
                        <label key={opt.id} style={{
                          display: 'flex', alignItems: 'flex-start', gap: 8,
                          padding: '8px 10px', borderRadius: 4, cursor: 'pointer',
                          background: selectedOption === opt.id
                            ? 'rgba(76, 175, 80, 0.08)'
                            : 'transparent',
                          border: `1px solid ${selectedOption === opt.id
                            ? 'rgba(76, 175, 80, 0.3)'
                            : 'var(--border, #333)'}`,
                        }}>
                          <input
                            type="radio"
                            name={`option-${id}`}
                            checked={selectedOption === opt.id}
                            onChange={() => setSelectedOption(opt.id)}
                            style={{ marginTop: 2 }}
                          />
                          <div>
                            <div style={{ fontSize: 12, color: 'var(--text-primary, #eee)', fontWeight: 500 }}>
                              {opt.label}
                            </div>
                            {opt.details.length > 0 && (
                              <div style={{ fontSize: 11, color: 'var(--text-muted, #888)', marginTop: 2, lineHeight: 1.4 }}>
                                {opt.details.join(' ')}
                              </div>
                            )}
                          </div>
                        </label>
                      ))}
                      <label style={{
                        display: 'flex', alignItems: 'flex-start', gap: 8,
                        padding: '8px 10px', borderRadius: 4, cursor: 'pointer',
                        background: selectedOption === 'custom'
                          ? 'rgba(76, 175, 80, 0.08)'
                          : 'transparent',
                        border: `1px solid ${selectedOption === 'custom'
                          ? 'rgba(76, 175, 80, 0.3)'
                          : 'var(--border, #333)'}`,
                      }}>
                        <input
                          type="radio"
                          name={`option-${id}`}
                          checked={selectedOption === 'custom'}
                          onChange={() => setSelectedOption('custom')}
                          style={{ marginTop: 2 }}
                        />
                        <div style={{ fontSize: 12, color: 'var(--text-primary, #eee)', fontWeight: 500 }}>
                          Custom approach
                        </div>
                      </label>
                    </div>

                    {/* Refinement / custom text */}
                    {selectedOption && (
                      <div style={{ marginTop: 8 }}>
                        <div style={{ fontSize: 10, color: 'var(--text-muted, #888)', marginBottom: 4 }}>
                          {selectedOption === 'custom' ? 'Describe your approach' : 'Optional: refine or add detail'}
                        </div>
                        <textarea
                          value={refineText}
                          onChange={(e) => setRefineText(e.target.value)}
                          placeholder={selectedOption === 'custom'
                            ? 'Describe the approach you want to take...'
                            : 'e.g., use src/ui/journal/basic/ and src/ui/journal/enhanced/'}
                          style={{
                            width: '100%', minHeight: 40, padding: 8,
                            fontSize: 12, lineHeight: 1.5,
                            background: 'var(--bg-canvas, #0f0f23)',
                            color: 'var(--text-primary, #eee)',
                            border: '1px solid var(--border, #444)',
                            borderRadius: 4, resize: 'vertical',
                            boxSizing: 'border-box',
                          }}
                        />
                      </div>
                    )}
                  </>
                ) : (
                  <>
                    <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary, #ccc)', marginBottom: 6 }}>
                      What's the answer?
                    </div>
                    <textarea
                      value={resolveText}
                      onChange={(e) => setResolveText(e.target.value)}
                      placeholder="Enter your decision..."
                      style={{
                        width: '100%', minHeight: 60, padding: 8,
                        fontSize: 12, lineHeight: 1.5,
                        background: 'var(--bg-canvas, #0f0f23)',
                        color: 'var(--text-primary, #eee)',
                        border: '1px solid var(--border, #444)',
                        borderRadius: 4, resize: 'vertical',
                        boxSizing: 'border-box',
                      }}
                    />
                  </>
                )}

                <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                  <button
                    onClick={() => {
                      onDecide(id, 'accept', buildNote());
                      setResolving(false);
                      setSelectedOption(null);
                      setRefineText('');
                    }}
                    disabled={!canSubmit}
                    style={{
                      padding: '6px 16px', fontSize: 12, cursor: canSubmit ? 'pointer' : 'not-allowed',
                      background: canSubmit ? '#4caf50' : 'var(--text-muted, #666)',
                      color: '#fff',
                      border: 'none', borderRadius: 4, fontWeight: 600,
                      opacity: canSubmit ? 1 : 0.5,
                    }}
                  >
                    Submit Resolution
                  </button>
                  <button
                    onClick={() => { setResolving(false); setResolveText(''); setSelectedOption(null); setRefineText(''); }}
                    style={{
                      padding: '6px 16px', fontSize: 12, cursor: 'pointer',
                      background: 'transparent', color: 'var(--text-muted, #888)',
                      border: '1px solid var(--border, #444)', borderRadius: 4,
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            );
          })()}

          {decided && (
            <div style={{
              fontSize: 11, marginTop: 10,
              color: decision.decision === 'accept' ? '#81c784' : 'var(--text-muted, #888)',
              fontWeight: 600,
            }}>
              {decision.decision === 'accept'
                ? (isAction ? 'Accepted' : 'Resolved')
                : 'Marked as intentional'}
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

  const handleDecide = async (findingId, decision, note) => {
    try {
      await api.recordFindingDecision(projectId, findingId, decision, note);
      setDecisions(prev => ({
        ...prev,
        [findingId]: { decision, note: note || null, decided_at: new Date().toISOString() },
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
                    projectId={projectId}
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
                  projectId={projectId}
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
