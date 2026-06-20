// background.js for Lingo Karaoke Extension

// Set side panel behavior to open when extension action icon is clicked
chrome.runtime.onInstalled.addListener(() => {
  if (chrome.sidePanel && chrome.sidePanel.setPanelBehavior) {
    chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true })
      .catch((err) => console.error("Error setting side panel behavior:", err));
  }
});

// Tell the side panel that the active tab/video may have changed so it can
// re-detect the current video and clear any stale lyrics.
function notifySidePanel(tabId, url) {
  chrome.runtime.sendMessage({ type: 'YOUTUBE_TAB_UPDATED', tabId, url: url || '' })
    .catch(() => {
      // The side panel may not be open/listening yet; safe to ignore.
    });
}

// IMPORTANT: YouTube is a single-page app. Navigating between videos updates the
// URL via history.pushState WITHOUT a full document reload, so it usually does
// NOT fire `status: 'complete'`. We must therefore react to `changeInfo.url`
// (the SPA navigation signal) as well, otherwise switching videos goes unnoticed
// and the panel keeps showing the previous video's lyrics.
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  const url = changeInfo.url || (tab && tab.url) || '';
  if ((changeInfo.url || changeInfo.status === 'complete') && url.includes('youtube.com')) {
    notifySidePanel(tabId, url);
  }
});

// Switching browser tabs should also refresh detection (e.g. moving to/from a
// YouTube tab). The panel itself decides whether the newly-active tab is a video.
chrome.tabs.onActivated.addListener(async ({ tabId }) => {
  try {
    const tab = await chrome.tabs.get(tabId);
    notifySidePanel(tabId, tab.url);
  } catch (err) {
    // Tab may have been closed before we could read it; ignore.
  }
});
