// LLM Prompt Defense - Content Script v3.1
// Enhanced with better extension context handling

(function() {
  'use strict';
  
  console.log("LLM Prompt Defense v3.1 - Starting...");

  const CONFIG = {
    MIN_PROMPT_LENGTH: 1,  // Changed from 5 to 1 to capture all messages
    TOAST_DURATION: 4500,
    ANALYSIS_TIMEOUT: 12000,
    MAX_RETRY_ATTEMPTS: 3,
    RETRY_DELAY: 1000
  };

  let isProcessing = false;
  let allowNextSend = false;
  let initAttempts = 0;

  // Enhanced extension validity check
  function isExtensionValid() {
    try {
      // Check if we're in a proper browser context
      if (typeof window === 'undefined') {
        console.error("[Extension Check] No window object");
        return false;
      }

      // Check if chrome API exists
      if (typeof chrome === 'undefined') {
        console.error("[Extension Check] chrome is undefined");
        return false;
      }

      // Check if runtime exists
      if (!chrome.runtime) {
        console.error("[Extension Check] chrome.runtime is undefined");
        return false;
      }

      // Check if we have an extension ID
      if (!chrome.runtime.id) {
        console.error("[Extension Check] chrome.runtime.id is undefined");
        return false;
      }

      // Try to access manifest as a final check
      try {
        const manifest = chrome.runtime.getManifest();
        if (!manifest) {
          console.error("[Extension Check] Cannot access manifest");
          return false;
        }
      } catch (e) {
        console.error("[Extension Check] Manifest access failed:", e);
        return false;
      }

      return true;
    } catch (e) {
      console.error("[Extension Check] Exception:", e);
      return false;
    }
  }

  // Wait for extension context with retry
  async function waitForExtensionContext(maxAttempts = 5) {
    for (let i = 0; i < maxAttempts; i++) {
      if (isExtensionValid()) {
        console.log(`[Wait] Extension context ready (attempt ${i + 1})`);
        return true;
      }
      console.warn(`[Wait] Extension context not ready, attempt ${i + 1}/${maxAttempts}`);
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    return false;
  }

  // Safe message sender with retries
  function sendMessageSafe(message, callback, retryCount = 0) {
    if (!isExtensionValid()) {
      console.error("[sendMessageSafe] Extension context invalid!");
      if (retryCount < CONFIG.MAX_RETRY_ATTEMPTS) {
        console.log(`[sendMessageSafe] Retrying... (${retryCount + 1}/${CONFIG.MAX_RETRY_ATTEMPTS})`);
        setTimeout(() => {
          sendMessageSafe(message, callback, retryCount + 1);
        }, CONFIG.RETRY_DELAY);
        return;
      }
      showReloadWarning();
      if (callback) callback({ ok: false, error: "Extension context invalid after retries" });
      return;
    }

    try {
      chrome.runtime.sendMessage(message, function(response) {
        if (chrome.runtime.lastError) {
          const error = chrome.runtime.lastError.message;
          console.error("[sendMessageSafe] Runtime error:", error);
          
          // Retry on specific errors
          if (retryCount < CONFIG.MAX_RETRY_ATTEMPTS && 
              (error.includes("Extension context") || error.includes("message port"))) {
            console.log(`[sendMessageSafe] Retrying due to error... (${retryCount + 1}/${CONFIG.MAX_RETRY_ATTEMPTS})`);
            setTimeout(() => {
              sendMessageSafe(message, callback, retryCount + 1);
            }, CONFIG.RETRY_DELAY);
            return;
          }
          
          if (callback) callback({ ok: false, error: error });
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
    banner.innerHTML = `
      <div style="position: fixed; top: 20px; right: 20px; background: #dc2626; color: white; 
                  padding: 16px 20px; border-radius: 8px; z-index: 9999999; 
                  font-family: system-ui, -apple-system, sans-serif; font-size: 14px; 
                  box-shadow: 0 4px 12px rgba(0,0,0,0.3); max-width: 350px;">
        <strong>⚠️ Extension Context Lost</strong><br>
        <div style="margin-top: 8px;">
          The LLM Defense extension needs to reconnect.<br>
          <strong style="color: #fef3c7;">Please refresh this page (Ctrl+R)</strong>
        </div>
        <button onclick="location.reload()" 
                style="margin-top: 12px; background: white; color: #dc2626; border: none; 
                       padding: 8px 16px; border-radius: 4px; cursor: pointer; font-weight: bold;">
          Refresh Now
        </button>
      </div>
    `;
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
    
    indicator.innerHTML = `
      <div style="position: fixed; top: 20px; left: 20px; background: rgba(16, 185, 129, 0.95); 
                  color: white; padding: 10px 16px; border-radius: 8px; z-index: 999999; 
                  font-family: system-ui, -apple-system, sans-serif; font-size: 13px; 
                  box-shadow: 0 4px 12px rgba(0,0,0,0.2); display: flex; align-items: center; 
                  gap: 8px; border: 2px solid rgba(255,255,255,0.3);">
        <span style="width: 8px; height: 8px; background: #10b981; border-radius: 50%; 
                     box-shadow: 0 0 8px #10b981; animation: pulse 2s infinite;"></span>
        <strong>🛡️ LLM Defense Active</strong>
      </div>
    `;
    document.body.appendChild(indicator);

    setTimeout(() => {
      if (indicator.parentNode) {
        indicator.style.transition = 'opacity 0.5s';
        indicator.style.opacity = '0';
        setTimeout(() => indicator.remove(), 500);
      }
    }, 5000);
  }

  // Initialize with retry logic
  async function initialize() {
    initAttempts++;
    console.log(`[Initialize] Attempt ${initAttempts} - Checking extension context...`);
    
    // Wait for extension context
    const contextReady = await waitForExtensionContext();
    
    if (!contextReady) {
      console.error("[Initialize] Extension context is NOT available after waiting");
      console.error("[Initialize] Possible causes:");
      console.error("  1. Extension was reloaded - SOLUTION: Refresh this page (Ctrl+R)");
      console.error("  2. Extension is disabled - SOLUTION: Enable in chrome://extensions");
      console.error("  3. manifest.json has errors - SOLUTION: Check extension setup");
      showReloadWarning();
      return;
    }

    console.log("[Initialize] Extension context is VALID ✓");
    console.log("[Initialize] Extension ID:", chrome.runtime.id);

    // Test background script connection
    sendMessageSafe({ type: "PING" }, function(response) {
      if (response && response.ok) {
        console.log("[Initialize] Background script connected ✓");
        startMonitoring();
      } else {
        console.warn("[Initialize] Background script not responding:", response?.error);
        console.warn("[Initialize] Starting monitoring anyway (backend might not be ready yet)");
        startMonitoring();
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
      let btn = document.querySelector('button[data-testid="send-button"]');
      if (btn) return btn;

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
      return { ok: true, data: { defense_action: "ALLOW", classification: "EXTENSION_INVALID" } };
    }

    // Allow empty or very short messages (like "hi", "ok", etc.)
    if (!text || text.length === 0) {
      console.log("[analyzePrompt] Empty message - allowing");
      return { ok: true, data: { defense_action: "ALLOW", classification: "EMPTY" } };
    }

    console.log("===========================================");
    console.log("[ANALYZING COMPLETE MESSAGE]");
    console.log("===========================================");
    console.log("Message:", text);
    console.log("Length:", text.length, "characters");
    console.log("===========================================");

    return new Promise((resolve) => {
      const timer = setTimeout(() => {
        console.warn("[analyzePrompt] Timeout - allowing message");
        showToast("⏱️ Timeout", "Analysis took too long - allowing message");
        resolve({ ok: true, data: { defense_action: "ALLOW", classification: "TIMEOUT" } });
      }, CONFIG.ANALYSIS_TIMEOUT);

      sendMessageSafe(
        { type: "ANALYZE_PROMPT", user_input: text },
        (response) => {
          clearTimeout(timer);
          if (response?.ok) {
            console.log("[Backend Response]:", response);
            resolve(response);
          } else {
            console.error("[Backend Error]:", response?.error);
            resolve({ ok: true, data: { defense_action: "ALLOW", classification: "BACKEND_ERROR" } });
          }
        }
      );
    });
  }

  // Handle analysis result
  async function handleResult(result, inputElem, originalEvent) {
    try {
      const action = result.data?.defense_action || "ALLOW";
      const classification = result.data?.classification || "UNKNOWN";

      console.log("===========================================");
      console.log("[DEFENSE DECISION]");
      console.log("Action:", action);
      console.log("Classification:", classification);
      console.log("===========================================");

      switch (action) {
        case "ALLOW":
          if (classification !== "BACKEND_ERROR" && classification !== "EXTENSION_INVALID") {
            showToast("✓ SAFE", classification);
          }
          console.log("[Action] Message is SAFE - Sending to ChatGPT");
          allowSendThrough(inputElem, originalEvent);
          break;

        case "SANITIZE":
          showToast("🧹 SANITIZED", classification);
          console.log("[Action] Message SANITIZED - Sending cleaned version");
          if (result.data.cleaned_input) {
            console.log("[Cleaned]:", result.data.cleaned_input);
            setText(inputElem, result.data.cleaned_input);
          }
          allowSendThrough(inputElem, originalEvent);
          break;

        case "BLOCK":
          showToast("🚫 BLOCKED", "Injection attempt detected!");
          console.log("[Action] Message BLOCKED - NOT sending to ChatGPT");
          console.warn("SECURITY: Malicious prompt blocked!");
          isProcessing = false;
          break;

        default:
          showToast("⚠️ Unknown Action", "Allowing by default");
          allowSendThrough(inputElem, originalEvent);
      }
    } catch (e) {
      console.error("[handleResult] Error:", e);
      allowSendThrough(inputElem, originalEvent);
    }
  }

  // Allow send through without retriggering
  function allowSendThrough(inputElem, originalEvent) {
    allowNextSend = true;
    
    setTimeout(() => {
      try {
        console.log("[allowSendThrough] Triggering actual send...");
        
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
          const button = findSendButton();
          if (button) button.click();
        }
        
        setTimeout(() => {
          isProcessing = false;
          allowNextSend = false;
        }, 500);
        
      } catch (e) {
        console.error("[allowSendThrough] Error:", e);
        isProcessing = false;
        allowNextSend = false;
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
      toast.innerHTML = `
        <div style="position: fixed; bottom: 20px; right: 20px; background: rgba(0,0,0,0.9); 
                    color: white; padding: 12px 16px; border-radius: 8px; z-index: 999999; 
                    font-family: system-ui, -apple-system, sans-serif; font-size: 14px; 
                    box-shadow: 0 4px 12px rgba(0,0,0,0.4); max-width: 320px; 
                    border: 2px solid rgba(255,255,255,0.1);">
          <strong>${title}</strong><br>
          <span style="opacity: 0.9;">${message}</span>
        </div>
      `;
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
    console.log("[Monitor] Starting message interception...");
    
    let trackedInput = null;
    let trackedButton = null;

    const observer = new MutationObserver(() => {
      try {
        if (!isExtensionValid()) {
          observer.disconnect();
          console.error("[Monitor] Extension invalid - stopping");
          showReloadWarning();
          return;
        }

        const inputElem = findInput();
        const buttonElem = findSendButton();

        if (inputElem && inputElem !== trackedInput) {
          trackedInput = inputElem;
          console.log("[Monitor] ✓ Attached to input - monitoring Enter key");
          showStatusIndicator();

          inputElem.addEventListener("keydown", async (e) => {
            if (allowNextSend) {
              console.log("[ENTER KEY] Allowing send through (already analyzed)");
              return;
            }
            
            if (e.key === "Enter" && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
              const text = getText(inputElem);
              
              // Process ALL messages, even very short ones
              if (isProcessing) {
                console.warn("[ENTER KEY] Already processing, ignoring...");
                return;
              }
              
              console.log("\n🔍 [ENTER KEY] User wants to send message!");
              e.preventDefault();
              e.stopPropagation();
              e.stopImmediatePropagation();

              isProcessing = true;
              const result = await analyzePrompt(text);
              await handleResult(result, inputElem, e);
            }
          }, true);
        }

        if (buttonElem && buttonElem !== trackedButton) {
          trackedButton = buttonElem;
          console.log("[Monitor] ✓ Attached to send button - monitoring clicks");

          buttonElem.addEventListener("click", async (e) => {
            if (allowNextSend) {
              console.log("[SEND BUTTON] Allowing send through (already analyzed)");
              return;
            }
            
            const inputElem = findInput();
            const text = getText(inputElem);
            
            // Process ALL messages, even very short ones
            if (isProcessing) {
              console.warn("[SEND BUTTON] Already processing, ignoring...");
              return;
            }
            
            console.log("\n🔍 [SEND BUTTON] User clicked send!");
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();

            isProcessing = true;
            const result = await analyzePrompt(text);
            await handleResult(result, inputElem, e);
          }, true);
        }

      } catch (e) {
        console.error("[Monitor] Observer error:", e);
      }
    });

    try {
      observer.observe(document.body, { childList: true, subtree: true });
      console.log("[Monitor] ✓ Now watching for send attempts");
      console.log("[Monitor] Will analyze messages when you press Enter or click Send");
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

  console.log("🛡️ LLM Prompt Defense v3.1 - Loaded");

})();
