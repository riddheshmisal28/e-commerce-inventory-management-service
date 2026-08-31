import React from 'react';
import { X, Bot, Zap, Hash, Clock, FileText } from 'lucide-react';

export default function LLMTraceModal({ isOpen, onClose, agentRun }) {
  if (!isOpen) return null;

  const allLLMCalls = [];
  if (agentRun?.steps) {
    for (const step of agentRun.steps) {
      if (step.llm_calls && step.llm_calls.length > 0) {
        for (const call of step.llm_calls) {
          allLLMCalls.push({
            ...call,
            step_name: step.step_name,
          });
        }
      }
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Bot size={20} color="#6366f1" />
            <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>
              LLM Telemetry & Trace Inspector
            </h3>
            <span className="badge badge-change">{allLLMCalls.length} Interactions</span>
          </div>
          <button className="icon-button" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          {allLLMCalls.length === 0 ? (
            <div className="empty-state">
              <p>No LLM interactions recorded for this execution run.</p>
            </div>
          ) : (
            allLLMCalls.map((trace, idx) => (
              <div key={idx} className="trace-item">
                <div className="trace-header">
                  <div>
                    <strong style={{ fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                      {trace.step_name}
                    </strong>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      Provider: <span style={{ color: 'var(--accent-cyan)' }}>{trace.provider}</span> | Model:{' '}
                      <span style={{ color: 'var(--accent-purple)' }}>{trace.model}</span>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center' }}>
                    {trace.duration_ms && (
                      <span className="badge badge-skipped">
                        <Clock size={11} /> {(trace.duration_ms / 1000).toFixed(2)}s
                      </span>
                    )}
                    {trace.total_tokens ? (
                      <span className="badge badge-success">
                        <Hash size={11} /> {trace.total_tokens} tokens
                      </span>
                    ) : null}
                    {trace.tokens_per_second ? (
                      <span className="badge badge-change">
                        <Zap size={11} /> {trace.tokens_per_second.toFixed(1)} tok/s
                      </span>
                    ) : null}
                  </div>
                </div>

                {trace.prompt && (
                  <div>
                    <label className="section-label" style={{ fontSize: '0.72rem' }}>
                      Prompt Payload ({trace.prompt_chars || trace.prompt.length} chars)
                    </label>
                    <pre className="trace-prompt">{trace.prompt}</pre>
                  </div>
                )}

                {trace.response && (
                  <div>
                    <label className="section-label" style={{ fontSize: '0.72rem' }}>
                      Raw LLM Response ({trace.response_chars || trace.response.length} chars)
                    </label>
                    <pre className="trace-response">{trace.response}</pre>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
