import React, { useState } from 'react';
import { Sparkles, Plus, Trash2, Bookmark, Play, RotateCcw } from 'lucide-react';

export default function RequirementForm({
  presets,
  currentRequirement,
  onChangeRequirement,
  onSubmit,
  isLoading,
  onReset,
}) {
  const [newCriterion, setNewCriterion] = useState('');

  const handleSelectPreset = (preset) => {
    onChangeRequirement({
      id: preset.id,
      title: preset.title,
      description: preset.description,
      acceptance_criteria: [...preset.acceptance_criteria],
    });
  };

  const handleAddCriterion = (e) => {
    e?.preventDefault();
    if (!newCriterion.trim()) return;
    onChangeRequirement({
      ...currentRequirement,
      acceptance_criteria: [...currentRequirement.acceptance_criteria, newCriterion.trim()],
    });
    setNewCriterion('');
  };

  const handleRemoveCriterion = (index) => {
    const updated = currentRequirement.acceptance_criteria.filter((_, i) => i !== index);
    onChangeRequirement({
      ...currentRequirement,
      acceptance_criteria: updated,
    });
  };

  return (
    <div className="glass-panel studio-card">
      <div className="card-title">
        <Sparkles size={18} color="#6366f1" />
        <span>Requirement Studio</span>
      </div>

      {/* Presets */}
      <div>
        <label className="section-label">Quick Presets</label>
        <div className="presets-grid">
          {presets.map((preset) => (
            <button
              key={preset.id}
              type="button"
              className={`preset-chip ${currentRequirement.id === preset.id ? 'active' : ''
                }`}
              onClick={() => handleSelectPreset(preset)}
            >
              <div className="preset-title">{preset.title}</div>
              <div className="preset-tag">{preset.tag}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Form Fields */}
      <div className="form-group">
        <label className="section-label">Feature Title</label>
        <input
          type="text"
          className="text-input"
          placeholder="e.g. Low Stock Alert"
          value={currentRequirement.title}
          onChange={(e) =>
            onChangeRequirement({ ...currentRequirement, title: e.target.value, id: null })
          }
          disabled={isLoading}
        />
      </div>

      <div className="form-group">
        <label className="section-label">Description & Context</label>
        <textarea
          className="textarea-input"
          rows={3}
          placeholder="Describe the business requirement, intent, and scope..."
          value={currentRequirement.description}
          onChange={(e) =>
            onChangeRequirement({
              ...currentRequirement,
              description: e.target.value,
              id: null,
            })
          }
          disabled={isLoading}
        />
      </div>

      {/* Acceptance Criteria */}
      <div className="form-group">
        <label className="section-label">
          Acceptance Criteria ({currentRequirement.acceptance_criteria.length})
        </label>
        <div className="criteria-list">
          {currentRequirement.acceptance_criteria.map((item, idx) => (
            <div key={idx} className="criteria-item">
              <span className="criteria-text">{item}</span>
              <button
                type="button"
                className="icon-button"
                title="Remove criterion"
                onClick={() => handleRemoveCriterion(idx)}
                disabled={isLoading}
              >
                <Trash2 size={13} />
              </button>
            </div>
          ))}
          {currentRequirement.acceptance_criteria.length === 0 && (
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              No criteria added yet. Add key acceptance rules below.
            </div>
          )}
        </div>

        <div className="criteria-add-row">
          <input
            type="text"
            className="text-input"
            style={{ padding: '0.5rem 0.75rem', fontSize: '0.82rem' }}
            placeholder="Add acceptance criterion..."
            value={newCriterion}
            onChange={(e) => setNewCriterion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAddCriterion(e)}
            disabled={isLoading}
          />
          <button
            type="button"
            className="btn-secondary"
            onClick={handleAddCriterion}
            disabled={isLoading || !newCriterion.trim()}
          >
            <Plus size={14} /> Add
          </button>
        </div>
      </div>

      {/* Trigger Button */}
      <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
        <button
          type="button"
          className="btn-primary"
          onClick={onSubmit}
          disabled={isLoading || !currentRequirement.title.trim()}
        >
          {isLoading ? (
            <>
              <div className="spinner" />
              <span>Analyzing Impact...</span>
            </>
          ) : (
            <>
              <Play size={16} fill="white" />
              <span>Run Impact Agent</span>
            </>
          )}
        </button>

        <button
          type="button"
          className="btn-secondary"
          title="Reset form"
          onClick={onReset}
          disabled={isLoading}
        >
          <RotateCcw size={15} />
        </button>
      </div>
    </div>
  );
}
