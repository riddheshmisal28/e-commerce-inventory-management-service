import React, { useState } from 'react';
import {
  FileCode,
  Database,
  Radio,
  Sliders,
  CheckCircle2,
  HelpCircle,
  Activity,
  Copy,
  Download,
  Terminal,
  ExternalLink,
  Flame,
  GitBranch,
} from 'lucide-react';

export default function ReportDashboard({ pipelineResult, onOpenTraces }) {
  const [activeTab, setActiveTab] = useState('data-models');
  const [copied, setCopied] = useState(false);

  if (!pipelineResult) {
    return (
      <div className="glass-panel empty-state">
        <div className="empty-icon-wrap">
          <Terminal size={32} />
        </div>
        <h3 style={{ fontSize: '1.15rem', color: 'var(--text-primary)' }}>
          Ready for Requirement Analysis
        </h3>
        <p style={{ maxWidth: '420px', fontSize: '0.88rem' }}>
          Select a sample preset or formulate a custom requirement in the Requirement Studio, then click{' '}
          <strong style={{ color: 'var(--accent-primary)' }}>Run Impact Agent</strong> to analyze codebase impacts.
        </p>
      </div>
    );
  }

  const { report, quality_summary, agent_run, success } = pipelineResult;

  const dataModels = [
    ...(report?.data_model_impact || []),
    ...(report?.model_impacts || []).map((m) => ({
      entity: m.model,
      change_type: m.change_type,
      change: m.change,
      reason: m.reason,
      confidence: m.confidence,
    })),
  ];
  const apiMutations = report?.api_interface_mutations || [];
  const logicComponents = [
    ...(report?.business_logic_impacts || []),
    ...(report?.repository_impacts || []),
    ...(report?.integration_impacts || []),
    ...(report?.component_impacts || []),
  ];
  const blastRadius = report?.component_blast_radius || [];
  const clarificationQuestions = report?.clarification_questions || [];
  const testScenarios = report?.test_scenarios || { happy_path: [], negative_cases: [], edge_cases: [] };
  const bddScenarios = report?.bdd_scenarios || [];

  const handleCopyMarkdown = () => {
    let md = `# Impact Analysis Report: ${report?.feature_summary?.name || 'Requirement'}\n\n`;
    md += `## Business Goal\n${report?.feature_summary?.business_goal || ''}\n\n`;

    md += `## Component Blast Radius\n`;
    blastRadius.forEach((b) => {
      md += `- **[${b.severity}] ${b.component}**: ${b.reason}\n`;
    });
    md += `\n`;

    if (dataModels.length > 0) {
      md += `## Data Model Impacts\n`;
      dataModels.forEach((d) => {
        md += `- **${d.entity}** (${d.change_type}): ${d.change}${d.reason ? ` — *${d.reason}*` : ''}\n`;
      });
      md += `\n`;
    }

    if (apiMutations.length > 0) {
      md += `## API Mutations\n`;
      apiMutations.forEach((a) => {
        md += `- **${a.endpoint}** [${a.change_type}]: ${a.details}\n`;
      });
      md += `\n`;
    }

    if (clarificationQuestions.length > 0) {
      md += `## Clarification Questions\n`;
      clarificationQuestions.forEach((q, i) => {
        md += `${i + 1}. ${q}\n`;
      });
      md += `\n`;
    }

    navigator.clipboard.writeText(md);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadJSON = () => {
    const blob = new Blob([JSON.stringify(pipelineResult, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `impact-report-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const getSeverityBadgeClass = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'high':
      case 'critical':
        return 'badge-high';
      case 'medium':
      case 'moderate':
        return 'badge-medium';
      default:
        return 'badge-low';
    }
  };

  return (
    <div className="glass-panel report-section">
      {/* Header & Feature Summary */}
      <div className="report-header-row">
        <div>
          <span className="section-label">Impact Analysis Report</span>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 700 }}>
            {report?.feature_summary?.name || 'Requirement Analysis'}
          </h2>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button type="button" className="btn-secondary" onClick={onOpenTraces}>
            <Activity size={14} color="#6366f1" />
            <span>LLM Traces</span>
          </button>
          <button type="button" className="btn-secondary" onClick={handleCopyMarkdown}>
            <Copy size={14} />
            <span>{copied ? 'Copied MD!' : 'Copy Markdown'}</span>
          </button>
          <button type="button" className="btn-secondary" onClick={handleDownloadJSON}>
            <Download size={14} />
            <span>JSON</span>
          </button>
        </div>
      </div>

      {report?.feature_summary && (
        <div className="feature-summary-box">
          <div className="feature-title">{report.feature_summary.name}</div>
          <div className="feature-goal">{report.feature_summary.business_goal}</div>
        </div>
      )}

      {/* Blast Radius Section */}
      <div>
        <label className="section-label" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <Flame size={14} color="#f43f5e" />
          <span>Blast Radius & Component Severity ({blastRadius.length})</span>
        </label>
        <div className="blast-grid">
          {blastRadius.length === 0 ? (
            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              No component blast radius detected.
            </div>
          ) : (
            blastRadius.map((item, idx) => (
              <div key={idx} className="blast-card">
                <div className="blast-header">
                  <span className="blast-component">{item.component}</span>
                  <span className={`badge ${getSeverityBadgeClass(item.severity)}`}>
                    {item.severity}
                  </span>
                </div>
                <div className="blast-reason">{item.reason}</div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Tabs Row */}
      <div className="report-tabs">
        <button
          type="button"
          className={`tab-button ${activeTab === 'data-models' ? 'active' : ''}`}
          onClick={() => setActiveTab('data-models')}
        >
          <Database size={15} />
          <span>Data Models</span>
          <span className="tab-count">{dataModels.length}</span>
        </button>

        <button
          type="button"
          className={`tab-button ${activeTab === 'api-mutations' ? 'active' : ''}`}
          onClick={() => setActiveTab('api-mutations')}
        >
          <Radio size={15} />
          <span>API Mutations</span>
          <span className="tab-count">{apiMutations.length}</span>
        </button>

        <button
          type="button"
          className={`tab-button ${activeTab === 'logic' ? 'active' : ''}`}
          onClick={() => setActiveTab('logic')}
        >
          <Sliders size={15} />
          <span>Business Logic & Repos</span>
          <span className="tab-count">{logicComponents.length}</span>
        </button>

        <button
          type="button"
          className={`tab-button ${activeTab === 'test-scenarios' ? 'active' : ''}`}
          onClick={() => setActiveTab('test-scenarios')}
        >
          <CheckCircle2 size={15} />
          <span>Test Scenarios</span>
          <span className="tab-count">
            {(testScenarios.happy_path?.length || 0) +
              (testScenarios.negative_cases?.length || 0) +
              (testScenarios.edge_cases?.length || 0)}
          </span>
        </button>

        <button
          type="button"
          className={`tab-button ${activeTab === 'bdd' ? 'active' : ''}`}
          onClick={() => setActiveTab('bdd')}
        >
          <GitBranch size={15} />
          <span>BDD Specs</span>
          <span className="tab-count">{bddScenarios.length}</span>
        </button>

        <button
          type="button"
          className={`tab-button ${activeTab === 'questions' ? 'active' : ''}`}
          onClick={() => setActiveTab('questions')}
        >
          <HelpCircle size={15} />
          <span>Clarifications</span>
          <span className="tab-count">{clarificationQuestions.length}</span>
        </button>
      </div>

      {/* Tab Contents */}
      {activeTab === 'data-models' && (
        <div>
          {dataModels.length === 0 ? (
            <div className="empty-state" style={{ padding: '2rem' }}>
              <p>No direct data model impacts detected.</p>
            </div>
          ) : (
            <table className="impact-table">
              <thead>
                <tr>
                  <th>Entity / Model</th>
                  <th>Change Type</th>
                  <th>Proposed Modification</th>
                  <th>Rationale</th>
                </tr>
              </thead>
              <tbody>
                {dataModels.map((item, idx) => (
                  <tr key={idx}>
                    <td>
                      <span className="code-pill">{item.entity}</span>
                    </td>
                    <td>
                      <span className="badge badge-change">{item.change_type}</span>
                    </td>
                    <td style={{ fontWeight: 500 }}>{item.change}</td>
                    <td style={{ color: 'var(--text-secondary)' }}>{item.reason || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {activeTab === 'api-mutations' && (
        <div>
          {apiMutations.length === 0 ? (
            <div className="empty-state" style={{ padding: '2rem' }}>
              <p>No API interface mutations required.</p>
            </div>
          ) : (
            <table className="impact-table">
              <thead>
                <tr>
                  <th>API Endpoint</th>
                  <th>Mutation Type</th>
                  <th>Mutation Details</th>
                  <th>Rationale</th>
                </tr>
              </thead>
              <tbody>
                {apiMutations.map((item, idx) => (
                  <tr key={idx}>
                    <td>
                      <span className="code-pill">{item.endpoint}</span>
                    </td>
                    <td>
                      <span className="badge badge-change">{item.change_type}</span>
                    </td>
                    <td style={{ fontWeight: 500 }}>{item.details}</td>
                    <td style={{ color: 'var(--text-secondary)' }}>{item.reason || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {activeTab === 'logic' && (
        <div>
          {logicComponents.length === 0 ? (
            <div className="empty-state" style={{ padding: '2rem' }}>
              <p>No business logic or component impacts detected.</p>
            </div>
          ) : (
            <table className="impact-table">
              <thead>
                <tr>
                  <th>Component / Class / Layer</th>
                  <th>Change Type</th>
                  <th>Change Scope</th>
                </tr>
              </thead>
              <tbody>
                {logicComponents.map((item, idx) => (
                  <tr key={idx}>
                    <td>
                      <span className="code-pill">{item.component}</span>
                    </td>
                    <td>
                      <span className="badge badge-change">{item.change_type}</span>
                    </td>
                    <td>{item.change}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {activeTab === 'test-scenarios' && (
        <div className="scenarios-grid">
          <div className="scenario-category-card">
            <div className="scenario-category-title" style={{ color: 'var(--accent-emerald)' }}>
              <CheckCircle2 size={16} />
              <span>Happy Path Scenarios ({testScenarios.happy_path?.length || 0})</span>
            </div>
            <div className="scenario-list">
              {testScenarios.happy_path?.map((sc, i) => (
                <div key={i} className="scenario-item" style={{ borderLeftColor: 'var(--accent-emerald)' }}>
                  {sc}
                </div>
              ))}
            </div>
          </div>

          <div className="scenario-category-card">
            <div className="scenario-category-title" style={{ color: 'var(--accent-amber)' }}>
              <Sliders size={16} />
              <span>Negative & Failure Cases ({testScenarios.negative_cases?.length || 0})</span>
            </div>
            <div className="scenario-list">
              {testScenarios.negative_cases?.map((sc, i) => (
                <div key={i} className="scenario-item" style={{ borderLeftColor: 'var(--accent-amber)' }}>
                  {sc}
                </div>
              ))}
            </div>
          </div>

          <div className="scenario-category-card">
            <div className="scenario-category-title" style={{ color: 'var(--accent-purple)' }}>
              <FileCode size={16} />
              <span>Edge & Boundary Cases ({testScenarios.edge_cases?.length || 0})</span>
            </div>
            <div className="scenario-list">
              {testScenarios.edge_cases?.map((sc, i) => (
                <div key={i} className="scenario-item" style={{ borderLeftColor: 'var(--accent-purple)' }}>
                  {sc}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'bdd' && (
        <div className="bdd-grid">
          {bddScenarios.length === 0 ? (
            <div className="empty-state" style={{ padding: '2rem' }}>
              <p>No BDD scenarios generated.</p>
            </div>
          ) : (
            bddScenarios.map((bdd, idx) => (
              <div key={idx} className="bdd-card">
                <div className="bdd-title">Scenario: {bdd.scenario}</div>
                <div className="bdd-step">
                  <span className="bdd-keyword">GIVEN</span>
                  <span className="bdd-text">{bdd.given}</span>
                </div>
                <div className="bdd-step">
                  <span className="bdd-keyword">WHEN</span>
                  <span className="bdd-text">{bdd.when}</span>
                </div>
                <div className="bdd-step">
                  <span className="bdd-keyword">THEN</span>
                  <span className="bdd-text">{bdd.then}</span>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === 'questions' && (
        <div className="questions-list">
          {clarificationQuestions.length === 0 ? (
            <div className="empty-state" style={{ padding: '2rem' }}>
              <p>No open clarification questions for this requirement.</p>
            </div>
          ) : (
            clarificationQuestions.map((q, idx) => (
              <div key={idx} className="question-item">
                <div className="question-number">{idx + 1}</div>
                <div>{q}</div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
