// content.js for Lingo Karaoke Extension

// Listen for messages from the side panel
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'GET_PLAYER_STATUS') {
    (async () => {
      const videoElement = document.querySelector('video');
      if (!videoElement) {
        sendResponse({ status: 'no_player' });
        return;
      }

      // Scrape video ID from URL
      const urlParams = new URLSearchParams(window.location.search);
      let videoId = urlParams.get('v');

      // Wait for DOM to match the URL videoId and for the title to be populated
      let retries = 20; // 20 * 100ms = 2 seconds max
      while (retries > 0) {
        const watchFlexy = document.querySelector('ytd-watch-flexy');
        const domVideoId = watchFlexy ? watchFlexy.getAttribute('video-id') : null;
        const titleElement = document.querySelector('h1.ytd-watch-metadata yt-formatted-string');

        // If we have a video ID in the URL, wait until the player DOM matches it and the title is populated.
        // If we don't have a video ID in the URL, no need to wait.
        if (!videoId || (domVideoId === videoId && titleElement && titleElement.textContent.trim())) {
          break;
        }
        await new Promise(r => setTimeout(r, 100));
        retries--;
        // Re-read URL parameter in case user navigated again during wait
        const currentUrlParams = new URLSearchParams(window.location.search);
        videoId = currentUrlParams.get('v');
      }

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
    })();
    return true; // Keep message channel open for async response
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
