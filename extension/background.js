const BACKEND_URL = "http://127.0.0.1:8000/analyze";
const REQUEST_TIMEOUT = 10000; // 10 seconds

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.type !== "ANALYZE_PROMPT") return;

  console.log("[background] ANALYZE_PROMPT received", { 
    from: sender.tab?.id, 
    len: (msg.user_input || "").length 
  });

  // Create timeout promise
  const timeoutPromise = new Promise((_, reject) => {
    setTimeout(() => reject(new Error("Request timeout")), REQUEST_TIMEOUT);
  });

  // Create fetch promise
  const fetchPromise = fetch(BACKEND_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_input: msg.user_input })
  })
    .then((res) => {
      if (!res.ok) {
        throw new Error(`Backend error: ${res.status} ${res.statusText}`);
      }
      return res.json();
    })
    .then((data) => {
      console.log("[background] analysis OK", data);
      
      // Validate response structure
      if (!data.classification || !data.defense_action) {
        throw new Error("Invalid response format from backend");
      }
      
      sendResponse({ ok: true, data });
    })
    .catch((e) => {
      console.error("[background] analysis error", e);
      sendResponse({ 
        ok: false, 
        error: String(e),
        errorType: e.name === "TypeError" ? "NETWORK_ERROR" : "BACKEND_ERROR"
      });
    });

  // Race between fetch and timeout
  Promise.race([fetchPromise, timeoutPromise])
    .catch((e) => {
      console.error("[background] timeout or error", e);
      sendResponse({ 
        ok: false, 
        error: "Request timeout - backend not responding",
        errorType: "TIMEOUT"
      });
    });

  return true; // keep message channel open for async sendResponse
});

// Handle extension installation/update
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === "install") {
    console.log("[background] Extension installed");
    // You could open a welcome page or set default settings here
  } else if (details.reason === "update") {
    console.log("[background] Extension updated to version", chrome.runtime.getManifest().version);
  }
});
