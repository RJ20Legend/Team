document.getElementById('analyzeBtn').addEventListener('click', analyzePrompt);

document.getElementById('promptInput').addEventListener('keypress', (e) => {
  if (e.key === 'Enter' && e.ctrlKey) {
    analyzePrompt();
  }
});

async function analyzePrompt() {
  const promptInput = document.getElementById('promptInput');
  const analyzeBtn = document.getElementById('analyzeBtn');
  const resultDiv = document.getElementById('result');
  const metricsDiv = document.getElementById('metrics');

  const userPrompt = promptInput.value.trim();

  if (!userPrompt) {
    alert('Please enter a prompt to analyze');
    return;
  }

  // Loading state
  analyzeBtn.disabled = true;
  analyzeBtn.textContent = 'Analyzing...';
  resultDiv.classList.add('hidden');
  metricsDiv.classList.add('hidden');

  try {
    const response = await fetch('http://127.0.0.1:8000/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_input: userPrompt })
    });

    if (!response.ok) {
      throw new Error(`Backend error: ${response.status}`);
    }

    const data = await response.json();

    if (!data.classification || !data.defense_action) {
      throw new Error('Invalid backend response');
    }

    displayResult(data);

  } catch (error) {
    console.error('Analysis error:', error);

    resultDiv.innerHTML = `
      <strong>⚠️ Connection Error</strong><br><br>
      Make sure backend is running on:<br>
      <code>http://127.0.0.1:8000</code>
    `;
    resultDiv.className = 'result malicious';
    resultDiv.classList.remove('hidden');
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = 'Analyze Prompt';
  }
}

function displayResult(data) {
  const resultDiv = document.getElementById('result');
  const metricsDiv = document.getElementById('metrics');

  const isBlocked = data.defense_action === "BLOCK";

  // Status styling
  const statusIcon = isBlocked ? "🚫" : "✅";
  const statusColor = isBlocked ? "malicious" : "safe";

  resultDiv.innerHTML = `
    <div style="font-size:16px;margin-bottom:12px;">
      <strong>${statusIcon} Security Decision:</strong>
      <span style="font-size:18px;font-weight:700;">
        ${data.defense_action}
      </span>
    </div>

    <div style="margin:10px 0;">
      <strong>🧠 Risk Classification:</strong>
      <code>${data.classification}</code>
    </div>

    ${data.review_verdict ? `
      <div style="margin:10px 0;">
        <strong>🤖 Reviewer LLM Verdict:</strong>
        <code>${data.review_verdict}</code>
      </div>
    ` : ''}

    <div style="margin:10px 0;">
      <strong>💬 Final AI Response:</strong><br>
      <div style="margin-top:6px;padding:10px;background:rgba(0,0,0,0.05);border-radius:6px;max-height:140px;overflow-y:auto;font-size:13px;">
        ${escapeHtml(data.llm_response || "No response")}
      </div>
    </div>
  `;

  resultDiv.className = `result ${statusColor}`;
  resultDiv.classList.remove('hidden');

  // Metrics (shows security architecture)
  metricsDiv.innerHTML = `
    <div class="metric-item">
      <strong>🛡 Security Layers Active:</strong> 3
    </div>
    <div class="metric-item">
      <strong>Layer 1:</strong> Input Firewall
    </div>
    <div class="metric-item">
      <strong>Layer 2:</strong> AI Reviewer LLM
    </div>
    <div class="metric-item">
      <strong>Layer 3:</strong> Output Filter
    </div>
  `;

  metricsDiv.classList.remove('hidden');
}

// Prevent XSS
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

document.addEventListener('DOMContentLoaded', () => {
  const promptInput = document.getElementById('promptInput');
  promptInput.placeholder = 'Enter prompt to test multi-layer AI security...\n\nTip: Press Ctrl+Enter to analyze';
});