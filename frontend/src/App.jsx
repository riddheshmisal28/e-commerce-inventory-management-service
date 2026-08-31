import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import RequirementForm from './components/RequirementForm';
import PipelineTimeline from './components/PipelineTimeline';
import ReportDashboard from './components/ReportDashboard';
import LLMTraceModal from './components/LLMTraceModal';
import { fetchHealth, fetchPresets, streamAgentAnalysis, runAgentAnalysis } from './services/api';

const DEFAULT_REQUIREMENT = {
  id: 'low-stock-alert',
  title: 'Low Stock Alert',
  description:
    'Notify inventory managers and warehouse supervisors when stock falls below a configurable threshold.',
  acceptance_criteria: [
    'Alert should trigger when quantity is below threshold.',
    'Alert should not trigger for inactive products.',
    'Threshold should be configurable per SKU.',
    'Duplicate alerts should not be generated within 24 hours.',
  ],
};

export default function App() {
  const [isOnline, setIsOnline] = useState(false);
  const [presets, setPresets] = useState([]);
  const [requirement, setRequirement] = useState(DEFAULT_REQUIREMENT);
  const [isLoading, setIsLoading] = useState(false);
  const [activeStep, setActiveStep] = useState(null);
  const [liveSteps, setLiveSteps] = useState({});
  const [executionCount, setExecutionCount] = useState(0);
  const [pipelineResult, setPipelineResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const [isTraceModalOpen, setIsTraceModalOpen] = useState(false);

  // Poll backend health & load presets
  useEffect(() => {
    let mounted = true;

    async function init() {
      const health = await fetchHealth();
      if (mounted) {
        setIsOnline(!!health);
      }

      const presetData = await fetchPresets();
      if (mounted && presetData?.length > 0) {
        setPresets(presetData);
      }
    }

    init();
    const interval = setInterval(async () => {
      const health = await fetchHealth();
      if (mounted) {
        setIsOnline(!!health);
      }
    }, 30000);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const handleRunAnalysis = async () => {
    if (!requirement.title.trim()) return;

    setIsLoading(true);
    setErrorMessage(null);
    setPipelineResult(null);
    setLiveSteps({});
    setActiveStep(null);

    const payload = {
      title: requirement.title,
      description: requirement.description,
      acceptance_criteria: requirement.acceptance_criteria,
    };

    try {
      await streamAgentAnalysis(payload, (eventType, data) => {
        if (eventType === 'step_start') {
          setActiveStep(data.step_name);
          setLiveSteps((prev) => ({
            ...prev,
            [data.step_name]: { status: 'running' },
          }));
        } else if (eventType === 'step_complete') {
          setLiveSteps((prev) => ({
            ...prev,
            [data.step_name]: {
              status: 'success',
              duration_ms: data.duration_ms,
            },
          }));
        } else if (eventType === 'step_skipped') {
          setLiveSteps((prev) => ({
            ...prev,
            [data.step_name]: {
              status: 'skipped',
            },
          }));
        } else if (eventType === 'step_error') {
          setActiveStep(data.step_name);
          setLiveSteps((prev) => ({
            ...prev,
            [data.step_name]: {
              status: 'failed',
              duration_ms: data.duration_ms,
              error: data.error,
            },
          }));
          setErrorMessage(data.error || `Step '${data.step_name}' failed.`);
        } else if (eventType === 'pipeline_complete') {
          setPipelineResult(data);
          setExecutionCount((prev) => prev + 1);
          setActiveStep(null);
        } else if (eventType === 'pipeline_error') {
          setErrorMessage(data.error || 'Pipeline execution failed.');
          setActiveStep(null);
        }
      });
    } catch (err) {
      // If streaming is blocked by proxy or network, fallback to standard analyze
      console.warn('Streaming failed, falling back to standard execution:', err);
      try {
        const result = await runAgentAnalysis(payload);
        setPipelineResult(result);
        setExecutionCount((prev) => prev + 1);
      } catch (fallbackErr) {
        console.error('Analysis execution failed:', fallbackErr);
        setErrorMessage(fallbackErr.message || 'Failed to execute Impact Analysis Agent.');
      }
    } finally {
      setActiveStep(null);
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setRequirement({
      id: null,
      title: '',
      description: '',
      acceptance_criteria: [],
    });
    setPipelineResult(null);
    setLiveSteps({});
    setActiveStep(null);
    setErrorMessage(null);
  };

  return (
    <div className="app-container">
      <Header
        isOnline={isOnline}
        executionCount={executionCount}
        totalDuration={pipelineResult?.total_duration_ms || 0}
      />

      {errorMessage && (
        <div
          style={{
            background: 'rgba(244, 63, 94, 0.15)',
            border: '1px solid var(--accent-rose)',
            borderRadius: 'var(--radius-md)',
            padding: '1rem 1.25rem',
            color: '#fecdd3',
            marginBottom: '1.5rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div>
            <strong>Execution Error:</strong> {errorMessage}
          </div>
          <button
            className="btn-secondary"
            style={{ padding: '0.3rem 0.6rem', fontSize: '0.75rem' }}
            onClick={() => setErrorMessage(null)}
          >
            Dismiss
          </button>
        </div>
      )}

      <main className="main-layout">
        {/* Left Column: Requirement Studio */}
        <aside>
          <RequirementForm
            presets={presets}
            currentRequirement={requirement}
            onChangeRequirement={setRequirement}
            onSubmit={handleRunAnalysis}
            isLoading={isLoading}
            onReset={handleReset}
          />
        </aside>

        {/* Right Column: Execution Pipeline & Report */}
        <section className="content-area">
          <PipelineTimeline
            agentRun={pipelineResult?.agent_run}
            liveSteps={liveSteps}
            activeStep={activeStep}
            isLoading={isLoading}
          />

          <ReportDashboard
            pipelineResult={pipelineResult}
            onOpenTraces={() => setIsTraceModalOpen(true)}
          />
        </section>
      </main>

      <LLMTraceModal
        isOpen={isTraceModalOpen}
        onClose={() => setIsTraceModalOpen(false)}
        agentRun={pipelineResult?.agent_run}
      />
    </div>
  );
}
