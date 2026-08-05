// FKT Capture — content script.
// Tracks the current text selection and hands it to the extension on request.
// Runs on every tab; stays passive until the user clicks Capture in the popup.

let currentSelection = "";

document.addEventListener("selectionchange", () => {
  const sel = window.getSelection();
  currentSelection = sel ? sel.toString().trim() : "";
});

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && msg.type === "fkt-get-selection") {
    const sel = window.getSelection();
    const text = (sel ? sel.toString() : "").trim();
    currentSelection = text;
    sendResponse({
      text: text,
      title: document.title || "",
      url: location.href,
    });
  }
  return false;
});
