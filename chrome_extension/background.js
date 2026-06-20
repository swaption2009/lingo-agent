// background.js for Lingo Karaoke Extension

// Set side panel behavior to open when extension action icon is clicked
chrome.runtime.onInstalled.addListener(() => {
  if (chrome.sidePanel && chrome.sidePanel.setPanelBehavior) {
    chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true })
      .catch((err) => console.error("Error setting side panel behavior:", err));
  }
});

// Optional: Monitor tab changes and let the side panel know if a YouTube video is loaded
chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url && tab.url.includes('youtube.com/watch')) {
    try {
      // Send a status update event that the side panel can listen to
      chrome.runtime.sendMessage({
        type: 'YOUTUBE_TAB_UPDATED',
        tabId: tabId,
        url: tab.url
      }).catch(() => {
        // Ignore errors if the side panel is not open/active yet
      });
    } catch (err) {
      console.warn("Could not send tab update message:", err);
    }
  }
});
