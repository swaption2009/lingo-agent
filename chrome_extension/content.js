// content.js for Lingo Karaoke Extension

// Listen for messages from the side panel
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'GET_PLAYER_STATUS') {
    const videoElement = document.querySelector('video');
    if (!videoElement) {
      sendResponse({ status: 'no_player' });
      return;
    }

    // Scrape video ID from URL
    const urlParams = new URLSearchParams(window.location.search);
    const videoId = urlParams.get('v');
    
    // Scrape title
    let title = "";
    const titleElement = document.querySelector('h1.ytd-watch-metadata yt-formatted-string');
    if (titleElement) {
      title = titleElement.textContent.trim();
    } else {
      title = document.title.replace(" - YouTube", "").trim();
    }

    sendResponse({
      status: 'ready',
      videoId: videoId,
      title: title,
      currentTime: videoElement.currentTime,
      paused: videoElement.paused,
      duration: videoElement.duration
    });
  }
  
  else if (message.type === 'SEEK_PLAYER') {
    const videoElement = document.querySelector('video');
    if (videoElement && typeof message.time === 'number') {
      videoElement.currentTime = message.time;
      if (videoElement.paused) {
        videoElement.play().catch(() => {});
      }
      sendResponse({ status: 'success', time: videoElement.currentTime });
    } else {
      sendResponse({ status: 'failed' });
    }
  }

  else if (message.type === 'TOGGLE_PLAYBACK') {
    const videoElement = document.querySelector('video');
    if (videoElement) {
      if (videoElement.paused) {
        videoElement.play().catch(() => {});
      } else {
        videoElement.pause();
      }
      sendResponse({ status: 'success', paused: videoElement.paused });
    } else {
      sendResponse({ status: 'failed' });
    }
  }

  return true; // Keep message channel open for async response
});
