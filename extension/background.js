console.log("[background] Service worker started");

const BACKEND_URL = "http://127.0.0.1:8000/analyze";
const REQUEST_TIMEOUT = 10000; // 10s

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.type === "PING") {
    console.log("[background] PING received from tab:", sender.tab?.id);
    sendResponse({ ok: true, pong: true });
    return true;
  }

  if (msg?.type !== "ANALYZE_PROMPT") return;

  console.log("[background] ANALYZE_PROMPT", { len: msg.user_input?.length });

  let responded = false;
  const safeSend = (payload) => {
    if (responded) return;
    responded = true;
    sendResponse(payload);
  };

  // fetch with timeout
  const fetchWithTimeout = (url, options, timeoutMs) =>
    new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("TIMEOUT")), timeoutMs);
      fetch(url, options)
        .then(res => {
          clearTimeout(timer);
          resolve(res);
        })
        .catch(err => {
          clearTimeout(timer);
          reject(err);
        });
    });

  fetchWithTimeout(BACKEND_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_input: msg.user_input })
  }, REQUEST_TIMEOUT)
    .then(res => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    })
    .then(data => {
      console.log("[background] OK", data);
      safeSend({ ok: true, data });
    })
    .catch(err => {
      console.error("[background] ERROR", err);
      const errorType = err.message === "TIMEOUT"
        ? "TIMEOUT"
        : err.name === "TypeError"
        ? "NETWORK_ERROR"
        : "BACKEND_ERROR";
      safeSend({ ok: false, errorType });
    });

  return true; // keep message channel open for async
});
