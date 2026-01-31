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
  
  // Show loading state
  analyzeBtn.disabled = true;
  analyzeBtn.textContent = 'Analyzing...';
  resultDiv.classList.add('hidden');
  metricsDiv.classList.add('hidden');
  
  try {
    // Use consistent JSON format (same as background.js)
    const response = await fetch('http://127.0.0.1:8000/analyze', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ user_input: userPrompt })
    });
    
    if (!response.ok) {
      throw new Error(`Backend error: ${response.status} ${response.statusText}`);
    }
    
    const data = await response.json();
    
    // Validate response structure
    if (!data.classification || !data.defense_action) {
      throw new Error('Invalid response format from backend');
    }
    
    displayResult(data);
    
  } catch (error) {
    console.error('Analysis error:', error);
    
    let errorMessage = '';
    if (error.message.includes('Failed to fetch')) {
      errorMessage = `
        <strong>⚠️ Backend Connection Failed</strong><br><br>
        Make sure your Python server is running:<br>
        <code>uvicorn main:app --reload --host 127.0.0.1 --port 8000</code>
        <br><br>
        <strong>Common issues:</strong><br>
        • Backend server not started<br>
        • Wrong port (should be 8000)<br>
        • CORS not configured<br>
        • Firewall blocking connection
      `;
    } else {
      errorMessage = `
        <strong>⚠️ Error:</strong><br>
        ${error.message}
      `;
    }
    
    resultDiv.innerHTML = errorMessage;
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
  
  const riskClass = data.classification.toLowerCase();
  
  // Status icons
  const statusIcons = {
    'safe': '✅',
    'suspicious': '⚠️',
    'malicious': '🚫'
  };
  
  const actionIcons = {
    'ALLOW': '✅',
    'SANITIZE': '⚠️',
    'BLOCK': '🚫'
  };
  
  const icon = statusIcons[riskClass] || '🛡️';
  const actionIcon = actionIcons[data.defense_action] || '•';
  
  resultDiv.innerHTML = `
    <div style="font-size: 16px; margin-bottom: 12px;">
      <strong>${icon} Classification:</strong> 
      <span style="font-size: 18px; font-weight: 700;">${data.classification}</span>
    </div>
    <div style="margin: 10px 0; padding: 8px; background: rgba(0,0,0,0.05); border-radius: 6px;">
      <strong>${actionIcon} Defense Action:</strong> 
      <span style="font-weight: 600;">${data.defense_action}</span>
    </div>
    ${data.cleaned_input ? `
      <div style="margin: 10px 0;">
        <strong>🔧 Cleaned Input:</strong><br>
        <div style="margin-top: 6px; padding: 10px; background: rgba(0,0,0,0.03); border-radius: 6px; max-height: 120px; overflow-y: auto;">
          <code style="white-space: pre-wrap; word-break: break-word;">${escapeHtml(data.cleaned_input)}</code>
        </div>
      </div>
    ` : ''}
    ${data.llm_response ? `
      <div style="margin: 10px 0;">
        <strong>💬 LLM Analysis:</strong><br>
        <div style="margin-top: 6px; padding: 10px; background: rgba(0,0,0,0.03); border-radius: 6px; max-height: 120px; overflow-y: auto; font-size: 13px; line-height: 1.5;">
          ${escapeHtml(data.llm_response)}
        </div>
      </div>
    ` : ''}
  `;
  
  resultDiv.className = `result ${riskClass}`;
  resultDiv.classList.remove('hidden');
  
  metricsDiv.innerHTML = `
    <div class="metric-item">
      <strong>📊 Risk Score:</strong> ${data.risk_score || 'N/A'}/5
    </div>
    ${data.latency_seconds ? `
      <div class="metric-item">
        <strong>⏱️ Processing Time:</strong> ${(data.latency_seconds).toFixed(3)}s
      </div>
    ` : ''}
    ${data.model_used ? `
      <div class="metric-item">
        <strong>🤖 Model:</strong> ${data.model_used}
      </div>
    ` : ''}
  `;
  metricsDiv.classList.remove('hidden');
}

// Utility function to escape HTML and prevent XSS
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Add keyboard shortcut info
document.addEventListener('DOMContentLoaded', () => {
  const promptInput = document.getElementById('promptInput');
  promptInput.placeholder = 'Enter your prompt here to check for injection attacks...\n\nTip: Press Ctrl+Enter to analyze';
});
