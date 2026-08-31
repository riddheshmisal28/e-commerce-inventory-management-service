import React from 'react';
import { Workflow } from 'lucide-react';

const PIPELINE_STEP_ORDER = [
  { key: 'LLM Requirement Planner', label: '1. Requirement Planner', desc: 'Context & Keyword Plan' },
  { key: 'Context Retriever', label: '2. Context Retriever', desc: 'Codebase Discovery' },
  { key: 'Impact Reasoner', label: '3. Impact Reasoner', desc: 'Holistic LLM Reasoning' },
  { key: 'Impact Validator', label: '4. Impact Validator', desc: 'Existence & Schema Check' },
  { key: 'Grounding Validator', label: '5. Grounding Validator', desc: 'Artifact Grounding Check' },
  { key: 'Semantic Impact Refiner', label: '6. Semantic Refiner', desc: 'Policy Gating & Refinement' },
  { key: 'Blast Radius Analyzer', label: '7. Blast Radius', desc: 'Severity Aggregation' },
  { key: 'Report Builder', label: '8. Report Builder', desc: 'Synthesis & Scenarios' },
];

export default function PipelineTimeline({ agentRun, liveSteps, activeStep, isLoading }) {
  const stepsMap = React.useMemo(() => {
    const map = {};
    if (agentRun?.steps) {
      for (const step of agentRun.steps) {
        map[step.step_name] = step;
      }
    }
    return map;
  }, [agentRun]);

  return (
    <div className="glass-panel pipeline-section">
      <div className="pipeline-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Workflow size={17} color="#6366f1" />
          <span style={{ fontSize: '0.95rem', fontWeight: 600 }}>Pipeline Execution Graph</span>
        </div>
        {agentRun?.duration_ms ? (
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Total Pipeline Time:{' '}
            <strong style={{ color: 'var(--text-primary)' }}>
              {(agentRun.duration_ms / 1000).toFixed(2)}s
            </strong>
          </div>
        ) : null}
      </div>

      <div className="pipeline-steps-grid">
        {PIPELINE_STEP_ORDER.map((item, index) => {
          const finalStepData = stepsMap[item.key];
          const liveData = liveSteps ? liveSteps[item.key] : null;

          // Determine current status
          let status = 'idle';
          let durationMs = undefined;
          let gatingPolicy = finalStepData?.metrics?.execution_decision?.policy || liveData?.policy;
          let errorMessage = liveData?.error || finalStepData?.error;

          if (liveData?.status) {
            status = liveData.status;
            durationMs = liveData.duration_ms;
          } else if (finalStepData?.status) {
            status = finalStepData.status;
            durationMs = finalStepData.duration_ms;
          } else if (activeStep === item.key) {
            status = 'running';
          }

          let badgeClass = 'badge-skipped';
          let badgeText = 'IDLE';

          if (status === 'running') {
            badgeClass = 'badge-running';
            badgeText = 'RUNNING';
          } else if (status === 'success') {
            badgeClass = 'badge-success';
            badgeText = 'SUCCESS';
          } else if (status === 'skipped') {
            badgeClass = 'badge-skipped';
            badgeText = 'SKIPPED';
          } else if (status === 'failed') {
            badgeClass = 'badge-high';
            badgeText = 'FAILED';
          }

          return (
            <div
              key={item.key}
              className={`step-card ${status} ${status === 'running' ? 'active' : ''}`}
            >
              <div className="step-index">STEP {index + 1}</div>
              <div className="step-name">{item.key}</div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>{item.desc}</div>

              <div className="step-meta">
                <span className={`badge ${badgeClass}`}>{badgeText}</span>
                {durationMs !== undefined && (
                  <span>
                    {durationMs > 1000
                      ? `${(durationMs / 1000).toFixed(2)}s`
                      : `${Math.round(durationMs)}ms`}
                  </span>
                )}
              </div>

              {gatingPolicy && (
                <div
                  style={{
                    fontSize: '0.65rem',
                    color: 'var(--accent-cyan)',
                    marginTop: '0.2rem',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                  title={`Policy: ${gatingPolicy}`}
                >
                  Policy: {gatingPolicy}
                </div>
              )}

              {status === 'failed' && errorMessage && (
                <div
                  style={{
                    fontSize: '0.65rem',
                    color: 'var(--accent-rose)',
                    marginTop: '0.2rem',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                  title={errorMessage}
                >
                  {errorMessage}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
