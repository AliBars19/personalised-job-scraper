/**
 * CorkBoard Service Worker (Manifest V3 background script).
 *
 * Handles:
 *  - Tab tracking for triggered pages
 *  - Message routing between popup and content scripts
 */

const triggeredTabs = new Set();

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "check_trigger") {
    const tabId = sender.tab?.id;
    const isTriggered = tabId ? triggeredTabs.has(tabId) : false;
    if (tabId) triggeredTabs.delete(tabId);
    sendResponse({ triggered: isTriggered });
    return true;
  }

  if (message.type === "trigger_fill") {
    // From popup — mark the current tab for auto-fill
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]?.id) {
        triggeredTabs.add(tabs[0].id);
        chrome.scripting.executeScript({
          target: { tabId: tabs[0].id },
          files: ["supabase-client.js", "mapping-engine.js", "content.js"],
        });
      }
    });
    sendResponse({ ok: true });
    return true;
  }

  if (message.type === "fill_results") {
    // Store latest fill results for popup
    chrome.storage.session.set({ lastFillResults: message.data });
    return false;
  }

  return false;
});

// Clean up old triggered tabs
chrome.tabs.onRemoved.addListener((tabId) => {
  triggeredTabs.delete(tabId);
});
