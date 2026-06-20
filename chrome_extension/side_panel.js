// side_panel.js for Lingo Karaoke Extension

const BACKEND_URL = "http://localhost:8000";
let activeVideoId = null;
let activeVideoTitle = null;
let connectionActive = false;
let currentPlayTime = 0;
let playbackPollInterval = null;

let lyricsData = []; // Array of { start: float, text: string, pinyin: string, translation: string }
let currentHighlightIndex = -1;
let currentVocabList = []; // Dictionary items for current song
let activeQuizQuestions = [];
let currentQuizQuestionIndex = 0;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  setupTabs();
  checkBackendConnection();
  detectActiveTab();

  // Button Event Listeners
  document.getElementById('btn-refresh-detection').addEventListener('click', detectActiveTab);
  document.getElementById('btn-analyze-video').addEventListener('click', analyzeCurrentVideo);
  document.getElementById('btn-clear-vocab').addEventListener('click', clearVocabDeck);
  document.getElementById('btn-play-pause').addEventListener('click', togglePlayback);
  document.getElementById('btn-submit-answer').addEventListener('click', checkQuizAnswer);
  document.getElementById('btn-next-question').addEventListener('click', nextQuizQuestion);

  // Listen for messages from background script
  chrome.runtime.onMessage.addListener((message) => {
    if (message.type === 'YOUTUBE_TAB_UPDATED') {
      detectActiveTab();
    }
  });

  // Load vocabulary deck initially
  loadVocabDeck();
});

// Setup Tab Navigation
function setupTabs() {
  const tabs = document.querySelectorAll('.nav-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      // Remove active class from all tabs & panels
      document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));

      // Add active class to selected tab & panel
      tab.classList.add('active');
      const panelId = `tab-${tab.getAttribute('data-tab')}`;
      const panel = document.getElementById(panelId);
      if (panel) panel.classList.add('active');
      
      // Load vocabulary deck specifically when opening the vocab tab
      if (tab.getAttribute('data-tab') === 'vocab') {
        loadVocabDeck();
      }
    });
  });
}

// Check Backend Connection Status
async function checkBackendConnection() {
  const dot = document.getElementById('connection-status-dot');
  const text = document.getElementById('connection-status-text');

  try {
    const res = await fetch(`${BACKEND_URL}/api/profile?user_id=2`);
    if (res.ok) {
      connectionActive = true;
      dot.className = 'dot connected';
      text.textContent = 'Connected to server';
    } else {
      throw new Error();
    }
  } catch (err) {
    connectionActive = false;
    dot.className = 'dot disconnected';
    text.textContent = 'Offline (Start backend)';
  }
}

// Detect Active YouTube Tab
async function detectActiveTab() {
  const loading = document.getElementById('youtube-loading');
  const inactive = document.getElementById('youtube-inactive');
  const active = document.getElementById('youtube-active');

  loading.classList.remove('hidden');
  inactive.classList.add('hidden');
  active.classList.add('hidden');

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.url || !tab.url.includes('youtube.com/watch')) {
      loading.classList.add('hidden');
      inactive.classList.remove('hidden');
      stopPlaybackPolling();
      return;
    }

    // Send message to Content Script to get player status
    chrome.tabs.sendMessage(tab.id, { type: 'GET_PLAYER_STATUS' }, (response) => {
      loading.classList.add('hidden');

      if (chrome.runtime.lastError || !response || response.status !== 'ready') {
        inactive.classList.remove('hidden');
        stopPlaybackPolling();
        return;
      }

      activeVideoId = response.videoId;
      activeVideoTitle = response.title;
      
      document.getElementById('detected-video-title').textContent = activeVideoTitle;
      active.classList.remove('hidden');

      // Start polling for synchronized lyrics playback
      startPlaybackPolling(tab.id);
    });
  } catch (err) {
    loading.classList.add('hidden');
    inactive.classList.remove('hidden');
    stopPlaybackPolling();
  }
}

// Start polling player position
function startPlaybackPolling(tabId) {
  stopPlaybackPolling();
  playbackPollInterval = setInterval(() => {
    chrome.tabs.sendMessage(tabId, { type: 'GET_PLAYER_STATUS' }, (response) => {
      if (response && response.status === 'ready') {
        currentPlayTime = response.currentTime;
        updatePlayerTimeUI(response.currentTime, response.duration, response.paused);
        syncLyricsHighlight(response.currentTime);
      }
    });
  }, 250);
}

function stopPlaybackPolling() {
  if (playbackPollInterval) {
    clearInterval(playbackPollInterval);
    playbackPollInterval = null;
  }
}

function updatePlayerTimeUI(current, duration, paused) {
  const formatTime = (secs) => {
    if (isNaN(secs)) return "00:00";
    const m = Math.floor(secs / 60).toString().padStart(2, '0');
    const s = Math.floor(secs % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };
  
  const timeSpan = document.getElementById('player-time');
  if (timeSpan) {
    timeSpan.textContent = `${formatTime(current)} / ${formatTime(duration)}`;
  }
  
  const playBtn = document.getElementById('btn-play-pause');
  if (playBtn) {
    playBtn.textContent = paused ? '▶️' : '⏸️';
  }
}

// Play/Pause YouTube video from side panel controls
async function togglePlayback() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab) {
    chrome.tabs.sendMessage(tab.id, { type: 'TOGGLE_PLAYBACK' }, (response) => {
      if (response && response.status === 'success') {
        const playBtn = document.getElementById('btn-play-pause');
        playBtn.textContent = response.paused ? '▶️' : '⏸️';
      }
    });
  }
}

// Sync Highlight with active lyric line based on timestamp
function syncLyricsHighlight(time) {
  if (lyricsData.length === 0) return;

  // Find the active line
  let activeIndex = -1;
  for (let i = 0; i < lyricsData.length; i++) {
    if (time >= lyricsData[i].start) {
      activeIndex = i;
    } else {
      break;
    }
  }

  if (activeIndex !== currentHighlightIndex && activeIndex !== -1) {
    currentHighlightIndex = activeIndex;
    
    // Update active class in DOM
    const lines = document.querySelectorAll('.lyrics-line');
    lines.forEach((line, idx) => {
      if (idx === activeIndex) {
        line.classList.add('active');
        line.scrollIntoView({ behavior: 'smooth', block: 'center' });
      } else {
        line.classList.remove('active');
      }
    });
  }
}

// Analyze Current YouTube Video
async function analyzeCurrentVideo() {
  if (!connectionActive) {
    alert("Backend is offline. Please launch the FastAPI server first.");
    return;
  }

  const btn = document.getElementById('btn-analyze-video');
  const btnText = btn.querySelector('.btn-text');
  const btnLoading = btn.querySelector('.btn-loading');

  btn.disabled = true;
  btnText.classList.add('hidden');
  btnLoading.classList.remove('hidden');

  try {
    const res = await fetch(`${BACKEND_URL}/api/youtube/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ video_id: activeVideoId, title: activeVideoTitle })
    });

    if (!res.ok) throw new Error("Failed to analyze video");

    const data = await res.json();
    loadAnalysisData(data);
  } catch (err) {
    console.error(err);
    alert("Error transcribing and analyzing the YouTube video. Please try again.");
  } finally {
    btn.disabled = false;
    btnText.classList.remove('hidden');
    btnLoading.classList.add('hidden');
  }
}

// Load Analyzed Video Data into UI
function loadAnalysisData(data) {
  // 1. Process Lyrics
  const placeholder = document.getElementById('lyrics-placeholder');
  const list = document.getElementById('lyrics-list');
  const controls = document.getElementById('player-controls');

  placeholder.classList.add('hidden');
  list.classList.remove('hidden');
  controls.classList.remove('hidden');

  list.innerHTML = '';
  lyricsData = [];

  // Parse lines with [start_time] format
  data.lines.forEach((line, idx) => {
    let startVal = idx * 5.0; // Default approximation if no timestamp
    let rawText = line.text;
    let rawPinyin = line.pinyin;
    let rawTranslation = line.translation;

    // Handle standard timestamp prefixes [12.34]
    const match = rawText.match(/^\[([\d.]+)\](.*)/);
    if (match) {
      startVal = parseFloat(match[1]);
      rawText = match[2];
      
      const pinMatch = rawPinyin.match(/^\[[\d.]+\](.*)/);
      if (pinMatch) rawPinyin = pinMatch[1];
      
      const transMatch = rawTranslation.match(/^\[[\d.]+\](.*)/);
      if (transMatch) rawTranslation = transMatch[1];
    }

    lyricsData.push({
      start: startVal,
      text: rawText,
      pinyin: rawPinyin,
      translation: rawTranslation
    });

    // Create DOM element
    const lineDiv = document.createElement('div');
    lineDiv.className = 'lyrics-line';
    lineDiv.innerHTML = `
      <div class="lyric-original">${rawText}</div>
      <div class="lyric-pinyin">${rawPinyin}</div>
      <div class="lyric-translation">${rawTranslation}</div>
    `;

    // Click line to seek player
    lineDiv.addEventListener('click', async () => {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab) {
        chrome.tabs.sendMessage(tab.id, { type: 'SEEK_PLAYER', time: startVal });
      }
    });

    list.appendChild(lineDiv);
  });

  // 2. Load Dictionary & Tutorial
  document.getElementById('dictionary-placeholder').classList.add('hidden');
  document.getElementById('dictionary-content').classList.remove('hidden');
  document.getElementById('grammar-tutorial-text').textContent = data.tutorial;

  const cardList = document.getElementById('vocab-cards-list');
  cardList.innerHTML = '';
  currentVocabList = data.dictionary || [];

  currentVocabList.forEach(vocab => {
    const card = document.createElement('div');
    card.className = 'vocab-card';
    card.innerHTML = `
      <div class="vocab-card-header">
        <div class="vocab-word-group">
          <span class="vocab-word">${vocab.word}</span>
          <span class="vocab-pinyin">${vocab.pinyin}</span>
        </div>
        <button class="btn-star" data-word="${vocab.word}" data-pinyin="${vocab.pinyin}" data-translation="${vocab.translation}">★</button>
      </div>
      <div class="vocab-meaning">${vocab.translation}</div>
      <div class="vocab-explanation">${vocab.explanation || ""}</div>
    `;

    // Star/Unstar Click Listener
    card.querySelector('.btn-star').addEventListener('click', (e) => {
      toggleStarWord(e.target);
    });

    cardList.appendChild(card);
  });

  // 3. Generate Quiz questions
  setupQuiz(data.dictionary, data.lines);
}

// Add/Remove word in vocabulary deck
async function toggleStarWord(starBtn) {
  const word = starBtn.getAttribute('data-word');
  const pinyin = starBtn.getAttribute('data-pinyin');
  const translation = starBtn.getAttribute('data-translation');
  const context = lyricsData[0] ? lyricsData[0].text : "YouTube Chinese Karaoke";

  if (starBtn.classList.contains('starred')) {
    // Delete
    try {
      const res = await fetch(`${BACKEND_URL}/api/vocab/${encodeURIComponent(word)}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        starBtn.classList.remove('starred');
        loadVocabDeck();
      }
    } catch (err) {
      console.error(err);
    }
  } else {
    // Add
    try {
      const res = await fetch(`${BACKEND_URL}/api/vocab`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          word: word,
          translation: translation,
          context: context,
          pinyin: pinyin,
          user_id: 2
        })
      });
      if (res.ok) {
        starBtn.classList.add('starred');
        loadVocabDeck();
      }
    } catch (err) {
      console.error(err);
    }
  }
}

// Fetch vocabulary deck and render
async function loadVocabDeck() {
  if (!connectionActive) return;

  try {
    const res = await fetch(`${BACKEND_URL}/api/vocab?user_id=2`);
    if (!res.ok) return;

    const data = await res.json();
    const placeholder = document.getElementById('vocab-placeholder');
    const list = document.getElementById('vocab-list');

    if (!data.deck || data.deck.length === 0) {
      placeholder.classList.remove('hidden');
      list.classList.add('hidden');
      return;
    }

    placeholder.classList.add('hidden');
    list.classList.remove('hidden');
    list.innerHTML = '';

    data.deck.forEach(item => {
      const row = document.createElement('div');
      row.className = 'vocab-item';
      row.innerHTML = `
        <div class="vocab-item-content">
          <span class="vocab-item-word">${item.word}</span>
          <span class="vocab-item-pinyin">${item.pinyin || ''}</span>
          <span class="vocab-item-meaning">${item.translation}</span>
        </div>
        <button class="btn-delete-vocab" data-word="${item.word}">🗑️</button>
      `;

      row.querySelector('.btn-delete-vocab').addEventListener('click', async (e) => {
        const wordToDelete = e.target.getAttribute('data-word');
        await fetch(`${BACKEND_URL}/api/vocab/${encodeURIComponent(wordToDelete)}`, { method: 'DELETE' });
        loadVocabDeck();
        
        // Remove active class star back in dictionary list if visible
        const activeStar = document.querySelector(`.btn-star[data-word="${wordToDelete}"]`);
        if (activeStar) activeStar.classList.remove('starred');
      });

      list.appendChild(row);
    });
  } catch (err) {
    console.error("Error loading vocab deck:", err);
  }
}

// Clear Entire Vocab Deck
async function clearVocabDeck() {
  if (!confirm("Are you sure you want to clear your study flashcard deck?")) return;
  try {
    await fetch(`${BACKEND_URL}/api/vocab/reset`, { method: 'POST' }); // Handled on backend reset or delete all
    // Or call a delete/reset loop
    const res = await fetch(`${BACKEND_URL}/api/vocab?user_id=2`);
    const data = await res.json();
    for (let item of data.deck) {
      await fetch(`${BACKEND_URL}/api/vocab/${encodeURIComponent(item.word)}`, { method: 'DELETE' });
    }
    loadVocabDeck();
    document.querySelectorAll('.btn-star').forEach(star => star.classList.remove('starred'));
  } catch (err) {
    console.error(err);
  }
}

// Setup Practice Quizzes
function setupQuiz(dictionary, lines) {
  if (!dictionary || dictionary.length < 2) {
    document.getElementById('quiz-placeholder').classList.remove('hidden');
    document.getElementById('quiz-content').classList.add('hidden');
    return;
  }

  document.getElementById('quiz-placeholder').classList.add('hidden');
  document.getElementById('quiz-content').classList.remove('hidden');

  activeQuizQuestions = [];
  currentQuizQuestionIndex = 0;

  // Generate 3 Multiple-Choice Questions
  const vocabWords = [...dictionary];
  const count = Math.min(3, vocabWords.length);

  for (let i = 0; i < count; i++) {
    const target = vocabWords[i];
    
    // Select 3 random incorrect choices
    const wrongChoices = dictionary
      .filter(d => d.word !== target.word)
      .map(d => d.translation);
    
    // Mix them
    const choices = [target.translation];
    while (choices.length < Math.min(4, dictionary.length) && wrongChoices.length > 0) {
      const idx = Math.floor(Math.random() * wrongChoices.length);
      choices.push(wrongChoices.splice(idx, 1)[0]);
    }
    
    // Shuffle choices
    choices.sort(() => Math.random() - 0.5);

    activeQuizQuestions.push({
      word: target.word,
      pinyin: target.pinyin,
      correctAnswer: target.translation,
      choices: choices,
      sentence: lines[Math.floor(Math.random() * lines.length)].text
    });
  }

  showQuizQuestion(0);
}

// Display active Quiz Question
function showQuizQuestion(index) {
  const q = activeQuizQuestions[index];
  if (!q) return;

  document.getElementById('quiz-question-number').textContent = `Question ${index + 1}/${activeQuizQuestions.length}`;
  document.getElementById('quiz-prompt').innerHTML = `What does the word <span style="color:var(--accent-cyan); font-weight:700;">"${q.word}"</span> (${q.pinyin}) mean?`;
  document.getElementById('quiz-question-context').textContent = `Context: "${q.sentence}"`;

  const body = document.getElementById('quiz-body');
  body.innerHTML = '';

  const optionsDiv = document.createElement('div');
  optionsDiv.className = 'quiz-options';

  q.choices.forEach(choice => {
    const btn = document.createElement('button');
    btn.className = 'quiz-option-btn';
    btn.textContent = choice;
    btn.addEventListener('click', () => {
      document.querySelectorAll('.quiz-option-btn').forEach(b => b.classList.remove('selected'));
      btn.classList.add('selected');
    });
    optionsDiv.appendChild(btn);
  });

  body.appendChild(optionsDiv);

  // Reset actions
  document.getElementById('quiz-feedback').classList.add('hidden');
  document.getElementById('btn-submit-answer').classList.remove('hidden');
  document.getElementById('btn-next-question').classList.add('hidden');
}

// Check Quiz Answer
async function checkQuizAnswer() {
  const selectedBtn = document.querySelector('.quiz-option-btn.selected');
  if (!selectedBtn) {
    alert("Please select an option first!");
    return;
  }

  const q = activeQuizQuestions[currentQuizQuestionIndex];
  const answer = selectedBtn.textContent;
  const feedback = document.getElementById('quiz-feedback');
  
  document.getElementById('btn-submit-answer').classList.add('hidden');

  if (answer === q.correctAnswer) {
    selectedBtn.classList.add('correct');
    feedback.className = 'quiz-feedback-box correct';
    feedback.innerHTML = `<strong>Correct!</strong> Great job! "${q.word}" indeed means "${q.correctAnswer}".`;
    feedback.classList.remove('hidden');

    // Auto-save correct word to study deck
    await fetch(`${BACKEND_URL}/api/vocab`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        word: q.word,
        translation: q.correctAnswer,
        context: q.sentence,
        pinyin: q.pinyin,
        user_id: 2
      })
    });
    loadVocabDeck();
  } else {
    selectedBtn.classList.add('wrong');
    // Highlight correct one
    document.querySelectorAll('.quiz-option-btn').forEach(btn => {
      if (btn.textContent === q.correctAnswer) btn.classList.add('correct');
    });

    feedback.className = 'quiz-feedback-box wrong';
    feedback.innerHTML = `<strong>Incorrect.</strong> The correct answer is "${q.correctAnswer}". Keep practicing!`;
    feedback.classList.remove('hidden');
  }

  document.getElementById('btn-next-question').classList.remove('hidden');
}

// Advance to next Quiz Question
function nextQuizQuestion() {
  currentQuizQuestionIndex++;
  if (currentQuizQuestionIndex < activeQuizQuestions.length) {
    showQuizQuestion(currentQuizQuestionIndex);
  } else {
    // End of quiz
    const body = document.getElementById('quiz-body');
    body.innerHTML = `
      <div style="text-align:center; padding: 20px 0;">
        <span style="font-size: 3rem;">🎉</span>
        <h3 style="margin-top: 10px; margin-bottom: 6px;">Quiz Completed!</h3>
        <p style="font-size: 0.85rem; color: var(--text-secondary);">Correctly answered words have been added to your Vocab Deck.</p>
      </div>
    `;
    document.getElementById('quiz-feedback').classList.add('hidden');
    document.getElementById('btn-submit-answer').classList.add('hidden');
    document.getElementById('btn-next-question').classList.add('hidden');
  }
}
