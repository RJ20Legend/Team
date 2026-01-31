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
    // Create form data
    const formData = new URLSearchParams();
    formData.append('user_input', userPrompt);
    
    const response = await fetch('http://127.0.0.1:8000/analyze', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData
    });
    
    if (!response.ok) {
      throw new Error('Backend connection failed');
    }
    
    const data = await response.json();
    
    displayResult(data);
    
  } catch (error) {
    resultDiv.innerHTML = `
      <strong>⚠️ Error:</strong><br>
      Backend not running. Make sure your Python server is running:<br>
      <code>uvicorn main:app --reload</code>
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
  
  const riskClass = data.classification.toLowerCase();
  
  resultDiv.innerHTML = `
    <div style="font-size: 16px; margin-bottom: 10px;">
      <strong>Classification:</strong> 
      <span style="font-size: 18px;">${data.classification}</span>
    </div>
    <div style="margin: 8px 0;">
      <strong>Defense Action:</strong> ${data.defense_action}
    </div>
    <div style="margin: 8px 0;">
      <strong>Cleaned Input:</strong><br>
      <code>${data.cleaned_input}</code>
    </div>
    <div style="margin: 8px 0;">
      <strong>LLM Response:</strong><br>
      ${data.llm_response}
    </div>
  `;
  
  resultDiv.className = `result ${riskClass}`;
  resultDiv.classList.remove('hidden');
  
  metricsDiv.innerHTML = `
    <div class="metric-item">
      <strong>Risk Score:</strong> ${data.risk_score}/5
    </div>
    <div class="metric-item">
      <strong>Processing Time:</strong> ${(data.latency_seconds).toFixed(3)}s
    </div>
  `;
  metricsDiv.classList.remove('hidden');
}