// LLM Prompt Defense - Content Script
// This script monitors ChatGPT inputs and analyzes them for security threats

(function() {
  'use strict';
  
  console.log("LLM Prompt Defense v2.0 - Starting...");

  const CONFIG = {
    MIN_PROMPT_LENGTH: 5,
    TOAST_DURATION: 4500,
    ANALYSIS_TIMEOUT: 12000
  };

  // Check if extension context is valid
  function isExtensionValid() {
    try {
      if (typeof chrome === 'undefined') {
        console.error("[Extension Check] chrome is undefined");
        return false;
      }
      if (!chrome.runtime) {
        console.error("[Extension Check] chrome.runtime is undefined");
        return false;
      }
      if (!chrome.runtime.id) {
        console.error("[Extension Check] chrome.runtime.id is undefined");
        return false;
      }
      return true;
    } catch (e) {
      console.error("[Extension Check] Exception:", e);
      return false;
    }
  }

  // Safe message sender
  function sendMessageSafe(message, callback) {
    if (!isExtensionValid()) {
      console.error("[sendMessageSafe] Extension context invalid!");
      showReloadWarning();
      if (callback) callback({ ok: false, error: "Extension context invalid" });
      return;
    }

    try {
      chrome.runtime.sendMessage(message, function(response) {
        if (chrome.runtime.lastError) {
          console.error("[sendMessageSafe] Runtime error:", chrome.runtime.lastError.message);
          if (callback) callback({ ok: false, error: chrome.runtime.lastError.message });
        } else {
          if (callback) callback(response || { ok: false, error: "No response" });
        }
      });
    } catch (err) {
      console.error("[sendMessageSafe] Exception:", err);
      if (callback) callback({ ok: false, error: err.message });
    }
  }

  // Show reload warning banner
  function showReloadWarning() {
    if (document.querySelector('#llm-defense-reload-warning')) return;
    
    const banner = document.createElement('div');
    banner.id = 'llm-defense-reload-warning';
    banner.innerHTML = '<div style="position: fixed; top: 20px; right: 20px; background: #dc2626; color: white; padding: 16px 20px; border-radius: 8px; z-index: 9999999; font-family: system-ui, -apple-system, sans-serif; font-size: 14px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); max-width: 350px;"><strong>Extension Context Lost</strong><br><div style="margin-top: 8px;">The LLM Defense extension was reloaded.<br><strong style="color: #fef3c7;">Please refresh this page (Ctrl+R)</strong></div></div>';
    document.body.appendChild(banner);
  }

  // Show status indicator
  function showStatusIndicator() {
    if (document.querySelector('#llm-defense-status')) return;
    
    const indicator = document.createElement('div');
    indicator.id = 'llm-defense-status';
    const style = document.createElement('style');
    style.textContent = '@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }';
    document.head.appendChild(style);
    
    indicator.innerHTML = '<div style="position: fixed; top: 20px; left: 20px; background: rgba(16, 185, 129, 0.95); color: white; padding: 10px 16px; border-radius: 8px; z-index: 999999; font-family: system-ui, -apple-system, sans-serif; font-size: 13px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); display: flex; align-items: center; gap: 8px; border: 2px solid rgba(255,255,255,0.3);"><span style="width: 8px; height: 8px; background: #10b981; border-radius: 50%; box-shadow: 0 0 8px #10b981; animation: pulse 2s infinite;"></span><strong>LLM Defense Active</strong></div>';
    document.body.appendChild(indicator);

    // Auto-hide after 5 seconds
    setTimeout(() => {
      if (indicator.parentNode) {
        indicator.style.transition = 'opacity 0.5s';
        indicator.style.opacity = '0';
        setTimeout(() => indicator.remove(), 500);
      }
    }, 5000);
  }

  // Initialize
  function initialize() {
    console.log("[Initialize] Checking extension context...");
    
    if (!isExtensionValid()) {
      console.error("[Initialize] Extension context is INVALID");
      console.error("[Initialize] This means the extension was reloaded while this page was open");
      console.error("[Initialize] >>> SOLUTION: Refresh this page (Ctrl+R) <<<");
      showReloadWarning();
      return;
    }

    console.log("[Initialize] Extension context is valid");
    console.log("[Initialize] Extension ID:", chrome.runtime.id);

    // Test connection to background script
    sendMessageSafe({ type: "PING" }, function(response) {
      if (response && response.ok) {
        console.log("[Initialize] Background script connected");
        startMonitoring();
      } else {
        console.warn("[Initialize] Background script not responding:", response?.error);
        startMonitoring(); // Start anyway
      }
    });
  }

  // Find ChatGPT input element
  function findInput() {
    try {
      // Method 1: textarea with name
      let elem = document.querySelector('textarea[name="prompt-textarea"]');
      if (elem?.offsetParent) return elem;

      // Method 2: textarea by ID
      elem = document.getElementById('prompt-textarea');
      if (elem?.offsetParent) return elem;

      // Method 3: contenteditable div
      const divs = document.querySelectorAll('div[role="textbox"][contenteditable="true"]');
      for (const div of divs) {
        if (div.offsetParent) return div;
      }
    } catch (e) {
      console.error("[findInput] Error:", e);
    }
    return null;
  }

  // Find send button
  function findSendButton() {
    try {
      // Method 1: data-testid
      let btn = document.querySelector('button[data-testid="send-button"]');
      if (btn) return btn;

      // Method 2: aria-label
      const buttons = document.querySelectorAll('button');
      for (const button of buttons) {
        if (!button.offsetParent) continue;
        
        const label = button.getAttribute('aria-label');
        if (label && label.toLowerCase().includes('send')) {
          return button;
        }
      }
    } catch (e) {
      console.error("[findSendButton] Error:", e);
    }
    return null;
  }

  // Get text from element
  function getText(elem) {
    if (!elem) return "";
    try {
      if (elem.tagName === "TEXTAREA" || elem.tagName === "INPUT") {
        return (elem.value || "").trim();
      }
      return (elem.innerText || elem.textContent || "").trim();
    } catch (e) {
      return "";
    }
  }

  // Set text to element
  function setText(elem, text) {
    if (!elem) return;
    try {
      if (elem.tagName === "TEXTAREA" || elem.tagName === "INPUT") {
        elem.value = text;
      } else {
        elem.innerText = text;
      }
      elem.dispatchEvent(new Event("input", { bubbles: true }));
    } catch (e) {
      console.error("[setText] Error:", e);
    }
  }

  // Analyze prompt
  async function analyzePrompt(text) {
    if (!isExtensionValid()) {
      console.error("[analyzePrompt] Extension invalid");
      return { ok: false, action: "ALLOW" };
    }

    if (!text || text.length < CONFIG.MIN_PROMPT_LENGTH) {
      return { ok: true, data: { defense_action: "ALLOW", classification: "TOO_SHORT" } };
    }

    console.log("[analyzePrompt] Analyzing:", text.substring(0, 50) + "...");
    console.log("[analyzePrompt] Full text length:", text.length, "characters");

    return new Promise((resolve) => {
      const timer = setTimeout(() => {
        console.warn("[analyzePrompt] Timeout");
        showToast("Timeout", "Analysis took too long");
        resolve({ ok: false, action: "ALLOW" });
      }, CONFIG.ANALYSIS_TIMEOUT);

      sendMessageSafe(
        { type: "ANALYZE_PROMPT", user_input: text },
        (response) => {
          clearTimeout(timer);
          if (response?.ok) {
            console.log("[analyzePrompt] Success:", response);
            resolve(response);
          } else {
            console.error("[analyzePrompt] Failed:", response?.error);
            resolve({ ok: false, action: "ALLOW" });
          }
        }
      );
    });
  }

  // Handle analysis result
  function handleResult(result, inputElem, originalEvent) {
    try {
      if (!result.ok) {
        console.warn("[handleResult] Analysis failed - allowing");
        showToast("Failed", "Allowed by default");
        resendPrompt(inputElem, originalEvent);
        return;
      }

      const action = result.data?.defense_action || "ALLOW";
      const classification = result.data?.classification || "UNKNOWN";

      console.log("[handleResult] Action:", action, "Classification:", classification);

      switch (action) {
        case "ALLOW":
          showToast("Safe", classification);
          resendPrompt(inputElem, originalEvent);
          break;

        case "SANITIZE":
          showToast("Sanitized", classification);
          if (result.data.cleaned_input) {
            setText(inputElem, result.data.cleaned_input);
          }
          resendPrompt(inputElem, originalEvent);
          break;

        case "BLOCK":
          showToast("Blocked", "Injection detected!");
          console.warn("[handleResult] BLOCKED malicious prompt");
          break;

        default:
          showToast("Unknown", "Allowing");
          resendPrompt(inputElem, originalEvent);
      }
    } catch (e) {
      console.error("[handleResult] Error:", e);
      resendPrompt(inputElem, originalEvent);
    }
  }

  // Re-send the prompt
  function resendPrompt(inputElem, originalEvent) {
    setTimeout(() => {
      try {
        if (originalEvent.type === "keydown") {
          const event = new KeyboardEvent("keydown", {
            key: "Enter",
            code: "Enter",
            keyCode: 13,
            which: 13,
            bubbles: true,
            cancelable: true
          });
          inputElem.dispatchEvent(event);
        } else if (originalEvent.type === "click") {
          originalEvent.target.click();
        }
      } catch (e) {
        console.error("[resendPrompt] Error:", e);
      }
    }, 100);
  }

  // Show toast notification
  function showToast(title, message) {
    try {
      if (!document.body) return;

      const existing = document.getElementById("llm-defense-toast");
      if (existing) existing.remove();

      const toast = document.createElement("div");
      toast.id = "llm-defense-toast";
      toast.innerHTML = '<div style="position: fixed; bottom: 20px; right: 20px; background: rgba(0,0,0,0.9); color: white; padding: 12px 16px; border-radius: 8px; z-index: 999999; font-family: system-ui, -apple-system, sans-serif; font-size: 14px; box-shadow: 0 4px 12px rgba(0,0,0,0.4); max-width: 320px; border: 2px solid rgba(255,255,255,0.1);"><strong>' + title + '</strong><br><span style="opacity: 0.9;">' + message + '</span></div>';
      document.body.appendChild(toast);

      setTimeout(() => {
        if (toast.parentNode) {
          toast.style.transition = "opacity 0.3s";
          toast.style.opacity = "0";
          setTimeout(() => toast.remove(), 300);
        }
      }, CONFIG.TOAST_DURATION);
    } catch (e) {
      console.error("[showToast] Error:", e);
    }
  }

  // Start monitoring
  function startMonitoring() {
    console.log("[Monitor] Starting...");
    
    let trackedInput = null;
    let trackedButton = null;

    const observer = new MutationObserver(() => {
      try {
        if (!isExtensionValid()) {
          observer.disconnect();
          console.error("[Monitor] Extension invalid - stopping");
          return;
        }

        const inputElem = findInput();
        const buttonElem = findSendButton();

        // Attach to input
        if (inputElem && inputElem !== trackedInput) {
          trackedInput = inputElem;
          console.log("[Monitor] Attached to input");
          showStatusIndicator();

          // Log input changes with visual feedback
          inputElem.addEventListener("input", () => {
            const text = getText(inputElem);
            if (text.length >= CONFIG.MIN_PROMPT_LENGTH) {
              console.log("[INPUT CAPTURED] Length:", text.length, "characters");
              console.log("[INPUT CAPTURED] Preview:", text.substring(0, 100) + (text.length > 100 ? "..." : ""));
            }
          });

          // Intercept Enter key
          inputElem.addEventListener("keydown", async (e) => {
            if (e.key === "Enter" && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
              const text = getText(inputElem);
              if (text.length >= CONFIG.MIN_PROMPT_LENGTH) {
                console.log("[ENTER PRESSED] Intercepted! Analyzing prompt...");
                console.log("[ENTER PRESSED] Text:", text);
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();

                const result = await analyzePrompt(text);
                handleResult(result, inputElem, e);
              }
            }
          }, true);
        }

        // Attach to button
        if (buttonElem && buttonElem !== trackedButton) {
          trackedButton = buttonElem;
          console.log("[Monitor] Attached to send button");

          buttonElem.addEventListener("click", async (e) => {
            const inputElem = findInput();
            const text = getText(inputElem);
            
            if (text.length >= CONFIG.MIN_PROMPT_LENGTH) {
              console.log("[BUTTON CLICKED] Intercepted! Analyzing prompt...");
              console.log("[BUTTON CLICKED] Text:", text);
              e.preventDefault();
              e.stopPropagation();
              e.stopImmediatePropagation();

              const result = await analyzePrompt(text);
              handleResult(result, inputElem, e);
            }
          }, true);
        }

      } catch (e) {
        console.error("[Monitor] Observer error:", e);
      }
    });

    try {
      observer.observe(document.body, { childList: true, subtree: true });
      console.log("[Monitor] Observing page");
    } catch (e) {
      console.error("[Monitor] Failed to observe:", e);
    }
  }

  // Run when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize);
  } else {
    initialize();
  }

  console.log("LLM Prompt Defense v2.0 - Loaded");

})();
