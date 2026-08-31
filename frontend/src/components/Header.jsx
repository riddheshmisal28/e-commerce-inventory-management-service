import React from 'react';
import { Layers, Activity, Cpu, CheckCircle2 } from 'lucide-react';

export default function Header({ isOnline, executionCount, totalDuration }) {
  return (
    <header className="app-header">
      <div className="brand-section">
        <div className="brand-logo">
          <Layers size={24} color="#ffffff" />
        </div>
        <div>
          <h1 className="brand-title">Impact Agent Studio</h1>
          <p className="brand-subtitle">
            Autonomous Requirement Analysis & Engineering Blast Radius Engine
          </p>
        </div>
      </div>

      <div className="header-meta">
        <div className="status-pill">
          <span className={`status-dot ${isOnline ? 'online' : 'offline'}`} />
          <span>{isOnline ? 'Agent API Connected' : 'Connecting to API...'}</span>
        </div>

        {executionCount > 0 && (
          <div className="status-pill">
            <Activity size={14} color="#6366f1" />
            <span>Runs: {executionCount}</span>
          </div>
        )}

        {totalDuration > 0 && (
          <div className="status-pill">
            <Cpu size={14} color="#06b6d4" />
            <span>Last Duration: {(totalDuration / 1000).toFixed(2)}s</span>
          </div>
        )}
      </div>
    </header>
  );
}
