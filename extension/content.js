console.log("🛡️ LLM Prompt Defense content script active");

const CONFIG = {
  MIN_PROMPT_LENGTH: 5,
  TOAST_DURATION: 4500,
  ANALYSIS_TIMEOUT: 12000
};

function isPromptBox(el) {
  if (!el) return false;
  const tag = (el.tagName || "").toUpperCase();
  return (
    tag === "TEXTAREA" ||
    (tag === "INPUT" && (el.type === "text" || el.type === "search")) ||
    el.isContentEditable ||
    el.getAttribute("role") === "textbox"
  );
}

function getPromptText(el) {
  if (!el) return "";
  if (el.tagName === "TEXTAREA" || el.tagName === "INPUT") {
    return (el.value || "").trim();
  }
  return (el.innerText || el.textContent || "").trim();
}

function setPromptText(el, text) {
  if (!el) return;
  if (el.tagName === "TEXTAREA" || el.tagName === "INPUT") {
    el.value = text;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  } else {
    el.innerText = text;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }
}

function toast(status, detail = "") {
  const existing = document.getElementById("__llm_defense_toast");
  if (existing) existing.remove();

  const div = document.createElement("div");
  div.id = "__llm_defense_toast";
  div.style.cssText = `
    position: fixed;
    bottom: 20px;
    right: 20px;
    padding: 12px 16px;
    z-index: 2147483647;
    border-radius: 10px;
    font-weight: 600;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
    box-shadow: 0 6px 22px rgba(0,0,0,0.25);
    max-width: 360px;
    word-break: break-word;
    animation: slideIn 0.3s ease-out;
    font-size: 14px;
    line-height: 1.4;
  `;

  // Color scheme based on status
  const colors = {
    ALLOWED: { bg: "#10b981", color: "#fff" },
    SANITIZED: { bg: "#f59e0b", color: "#fff" },
    BLOCKED: { bg: "#ef4444", color: "#fff" },
    ERROR: { bg: "#6b7280", color: "#fff" }
  };

  const colorScheme = colors[status] || colors.ERROR;
  div.style.background = colorScheme.bg;
  div.style.color = colorScheme.color;

  // Status icons
  const icons = {
    ALLOWED: "✅",
    SANITIZED: "⚠️",
    BLOCKED: "🚫",
    ERROR: "❌"
  };

  div.innerHTML = `
    <div style="font-size: 14px; font-weight: 700;">
      ${icons[status] || "🛡️"} Prompt Defense: <strong>${status}</strong>
    </div>
    ${detail ? `<div style="margin-top: 6px; font-size: 12px; opacity: 0.95;">${detail}</div>` : ""}
  `;

  document.body.appendChild(div);
  
  setTimeout(() => {
    div.style.animation = "slideOut 0.3s ease-in";
    setTimeout(() => div.remove(), 300);
  }, CONFIG.TOAST_DURATION);
}

// Add CSS animations
if (!document.getElementById("__llm_defense_styles")) {
  const style = document.createElement("style");
  style.id = "__llm_defense_styles";
  style.textContent = `
    @keyframes slideIn {
      from {
        transform: translateX(400px);
        opacity: 0;
      }
      to {
        transform: translateX(0);
        opacity: 1;
      }
    }
    @keyframes slideOut {
      from {
        transform: translateX(0);
        opacity: 1;
      }
      to {
        transform: translateX(400px);
        opacity: 0;
      }
    }
  `;
  document.head.appendChild(style);
}

async function analyzeViaBackground(promptText) {
  return new Promise((resolve) => {
    const timeout = setTimeout(() => {
      resolve({ 
        ok: false, 
        error: "Analysis timeout - backend not responding",
        errorType: "TIMEOUT"
      });
    }, CONFIG.ANALYSIS_TIMEOUT);

    chrome.runtime.sendMessage(
      { type: "ANALYZE_PROMPT", user_input: promptText },
      (resp) => {
        clearTimeout(timeout);
        
        if (chrome.runtime.lastError) {
          resolve({ 
            ok: false, 
            error: chrome.runtime.lastError.message,
            errorType: "EXTENSION_ERROR"
          });
          return;
        }
        
        resolve(resp);
      }
    );
  });
}

async function guardAndMaybeBlock(el, event) {
  const promptText = getPromptText(el);
  
  if (!promptText || promptText.length < CONFIG.MIN_PROMPT_LENGTH) {
    return;
  }

  console.log("[content] Analyzing prompt:", promptText.substring(0, 50) + "...");

  const resp = await analyzeViaBackground(promptText);

  if (!resp?.ok) {
    const errorMessages = {
      NETWORK_ERROR: "Backend not reachable. Is your server running on 127.0.0.1:8000?",
      TIMEOUT: "Request timeout. Backend is too slow or not responding.",
      EXTENSION_ERROR: "Extension error. Try reloading the page.",
      BACKEND_ERROR: resp?.error || "Unknown backend error"
    };
    
    const errorMsg = errorMessages[resp?.errorType] || errorMessages.BACKEND_ERROR;
    toast("ERROR", errorMsg);
    console.error("[content] Analysis failed:", resp?.error);
    return;
  }

  const data = resp.data;
  const action = (data.defense_action || "").toUpperCase();
  const classification = data.classification || "UNKNOWN";

  console.log("[content] Analysis result:", { action, classification });

  if (action === "BLOCK") {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation?.();
    }
    toast("BLOCKED", `Detected: ${classification}. Prompt was blocked for security.`);
    return;
  }

  if (action === "SANITIZE") {
    if (data.cleaned_input && data.cleaned_input !== promptText) {
      setPromptText(el, data.cleaned_input);
      toast("SANITIZED", `Detected: ${classification}. Prompt has been cleaned.`);
    } else {
      toast("SANITIZED", `Detected: ${classification}. Prompt sanitized.`);
    }
    return;
  }

  // ALLOW or any other action
  toast("ALLOWED", "Prompt looks safe. ✓");
}

function attachBoxListener(el) {
  if (el.dataset.__llmDefenseAttached) return;
  el.dataset.__llmDefenseAttached = "true";

  // Intercept Enter submissions
  el.addEventListener(
    "keydown",
    async (e) => {
      // Common "send" pattern: Enter without Shift
      if (e.key === "Enter" && !e.shiftKey) {
        // Some chat interfaces use Enter to send, others use Ctrl+Enter
        // We'll check for both patterns
        const isSendKey = !e.ctrlKey && !e.metaKey && !e.altKey;
        
        if (isSendKey) {
          await guardAndMaybeBlock(el, e);
        }
      }
    },
    true // capture phase
  );
}

function attachSendButtonListener() {
  // Find buttons that likely submit prompts
  const candidates = Array.from(
    document.querySelectorAll("button, [role='button'], input[type='submit']")
  );
  
  for (const btn of candidates) {
    if (btn.dataset.__llmDefenseBtnAttached) continue;

    const label = (btn.getAttribute("aria-label") || btn.textContent || "").toLowerCase();
    const hasRelevantText = 
      label.includes("send") || 
      label.includes("submit") || 
      label.includes("enter") ||
      label.includes("go") ||
      btn.querySelector("svg"); // Many send buttons use icons

    if (!hasRelevantText) continue;

    btn.dataset.__llmDefenseBtnAttached = "true";
    btn.addEventListener(
      "click",
      async (e) => {
        // Find the most likely prompt input
        const active = document.activeElement;
        let promptEl = null;

        if (isPromptBox(active)) {
          promptEl = active;
        } else {
          // Try to find a prompt box near this button
          const parent = btn.closest("form, div, section");
          if (parent) {
            promptEl = parent.querySelector(
              "textarea, input[type='text'], [contenteditable='true'], [role='textbox']"
            );
          }
          
          // Fallback: find any prompt box on the page
          if (!promptEl) {
            promptEl = document.querySelector(
              "textarea:focus, input[type='text']:focus, [contenteditable='true']:focus, [role='textbox']:focus"
            );
          }
        }

        if (promptEl) {
          await guardAndMaybeBlock(promptEl, e);
        }
      },
      true // capture phase
    );
  }
}

function scan() {
  // Find all potential prompt input boxes
  const selectors = [
    "textarea",
    "input[type='text']",
    "input[type='search']",
    "[contenteditable='true']",
    "[role='textbox']"
  ];

  document.querySelectorAll(selectors.join(", ")).forEach((el) => {
    if (isPromptBox(el)) {
      attachBoxListener(el);
    }
  });

  // Attach to send buttons
  attachSendButtonListener();
}

// Observe DOM changes to catch dynamically added elements
const observer = new MutationObserver((mutations) => {
  // Debounce: only scan if there are actual element additions
  const hasAddedNodes = mutations.some(m => m.addedNodes.length > 0);
  if (hasAddedNodes) {
    scan();
  }
});

observer.observe(document.documentElement, { 
  childList: true, 
  subtree: true 
});

// Initial scan
scan();

console.log("🛡️ LLM Prompt Defense: Monitoring active");
