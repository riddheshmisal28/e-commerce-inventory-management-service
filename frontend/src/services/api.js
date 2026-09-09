const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export async function fetchHealth() {
  try {
    const res = await fetch(`${API_BASE_URL}/agent/health`);
    if (!res.ok) throw new Error(`Status: ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error('Health check failed', err);
    return null;
  }
}

export async function fetchPresets() {
  try {
    const res = await fetch(`${API_BASE_URL}/agent/presets`);
    if (!res.ok) throw new Error(`Status: ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error('Failed to fetch presets', err);
    return [];
  }
}

export async function runAgentAnalysis(requirement) {
  const res = await fetch(`${API_BASE_URL}/agent/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requirement),
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorBody.detail || `Analysis failed with HTTP ${res.status}`);
  }

  return await res.json();
}

export async function streamAgentAnalysis(requirement, onEvent) {
  const res = await fetch(`${API_BASE_URL}/agent/analyze/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requirement),
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorBody.detail || `Stream failed with HTTP ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split('\n\n');
    buffer = blocks.pop() || '';

    for (const block of blocks) {
      if (!block.trim()) continue;
      const eventMatch = block.match(/^event:\s*(.+)$/m);
      const dataMatch = block.match(/^data:\s*(.+)$/m);
      const eventType = eventMatch ? eventMatch[1].trim() : 'message';
      if (dataMatch) {
        try {
          const data = JSON.parse(dataMatch[1].trim());
          onEvent(eventType, data);
        } catch (e) {
          console.error('Failed to parse SSE data', e, dataMatch[1]);
        }
      }
    }
  }
}
