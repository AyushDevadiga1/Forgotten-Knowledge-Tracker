// FKT Capture — background service worker.
// Fetches the selected text from the active tab (via the content script) and
// POSTs it to the FKT dashboard's /api/v1/ingest endpoint. Because the fetch
// originates from the extension's own context with host_permissions, it is
// not subject to page CORS.

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && msg.type === "fkt-send-selection") {
    ingestSelection(msg.tabId, msg.endpoint)
      .then((result) => sendResponse({ ok: true, result: result }))
      .catch((err) => sendResponse({ ok: false, error: String(err) }));
    return true; // keep the message channel open for the async response
  }
});

async function ingestSelection(tabId, endpoint) {
  let reply;
  try {
    reply = await chrome.tabs.sendMessage(tabId, { type: "fkt-get-selection" });
  } catch (e) {
    throw new Error("Cannot read the selection from this tab — reload the page and try again.");
  }

  const text = (reply && reply.text) || "";
  if (!text || text.trim().length < 20) {
    throw new Error("Select at least a few sentences in the tab first (20+ characters).");
  }

  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text: text,
      title: (reply && reply.title) || "",
      url: (reply && reply.url) || "",
      source: "chrome-extension",
    }),
  });

  if (!res.ok) {
    throw new Error("HTTP " + res.status + ": " + (await res.text()));
  }
  return res.json();
}
