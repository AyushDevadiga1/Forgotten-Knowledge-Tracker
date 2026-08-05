// FKT Capture — popup logic.
const DEFAULT_ENDPOINT = "http://127.0.0.1:5000/api/v1/ingest";

const btn = document.getElementById("capture");
const statusEl = document.getElementById("status");
const endpointInput = document.getElementById("endpoint");

chrome.storage.sync.get("endpoint").then((data) => {
  endpointInput.value = data.endpoint || DEFAULT_ENDPOINT;
});

endpointInput.addEventListener("change", () => {
  chrome.storage.sync.set({ endpoint: endpointInput.value.trim() });
});

btn.addEventListener("click", async () => {
  const endpoint = endpointInput.value.trim() || DEFAULT_ENDPOINT;
  chrome.storage.sync.set({ endpoint: endpoint });

  btn.disabled = true;
  statusEl.textContent = "Capturing\u2026";
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || tab.id == null) {
      throw new Error("No active tab found.");
    }
    const resp = await chrome.runtime.sendMessage({
      type: "fkt-send-selection",
      tabId: tab.id,
      endpoint: endpoint,
    });
    if (resp && resp.ok) {
      const d = resp.result;
      statusEl.textContent =
        "Saved " + (d.concepts_saved || 0) + " concept(s).\n" +
        "Keywords: " + ((d.keywords || []).join(", ") || "none");
    } else {
      statusEl.textContent = "Failed: " + (resp ? resp.error : "no response — is the dashboard running?");
    }
  } catch (e) {
    statusEl.textContent = "Failed: " + e.message;
  } finally {
    btn.disabled = false;
  }
});
