// Lingo Karaoke App - Client-side SPA Script

document.addEventListener("DOMContentLoaded", () => {
  // --- STATE ---
  let activeUser = null;
  let allUsers = [];
  let allMedia = [];
  let activeQuizSession = null;

  // --- DOM ELEMENTS ---
  const headerUserBadge = document.getElementById("header-user-badge");
  const currentUserName = document.getElementById("current-user-name");
  const currentUserLang = document.getElementById("current-user-lang");
  const btnLogout = document.getElementById("btn-logout");

  const viewAuth = document.getElementById("view-auth");
  const viewDashboard = document.getElementById("view-dashboard");
  const viewSharedLesson = document.getElementById("view-shared-lesson");
  const btnLessonLogin = document.getElementById("btn-lesson-login");
  const btnLessonDashboard = document.getElementById("btn-lesson-dashboard");

  // Auth views
  const tabBtnLogin = document.getElementById("tab-btn-login");
  const tabBtnRegister = document.getElementById("tab-btn-register");
  const authSectionLogin = document.getElementById("auth-section-login");
  const authSectionRegister = document.getElementById("auth-section-register");
  const loginUserSelect = document.getElementById("login-user-select");
  const formLogin = document.getElementById("form-login");
  const formRegister = document.getElementById("form-register");

  // Navigation sidebar
  const sideTabs = document.querySelectorAll(".side-tab");
  const panes = document.querySelectorAll(".pane");

  // Modals
  const modalMedia = document.getElementById("modal-media");
  const modalVocab = document.getElementById("modal-vocab");
  const modalHistory = document.getElementById("modal-history");

  // --- INITIALIZE ---
  checkSession();

  // --- SESSION MANAGEMENT ---
  function checkSession() {
    const urlParams = new URLSearchParams(window.location.search);
    const lessonId = urlParams.get("lesson");

    const savedUser = localStorage.getItem("lingo_active_user");
    if (savedUser) {
      try {
        activeUser = JSON.parse(savedUser);
      } catch (e) {
        localStorage.removeItem("lingo_active_user");
      }
    }

    if (lessonId) {
      showSharedLesson(lessonId);
    } else if (activeUser) {
      showDashboard();
    } else {
      showAuth();
    }
  }

  function showAuth() {
    activeUser = null;
    viewAuth.classList.remove("hidden");
    viewDashboard.classList.add("hidden");
    if(viewSharedLesson) viewSharedLesson.classList.add("hidden");
    headerUserBadge.classList.add("hidden");
    loadUsersList();
  }

  function showDashboard() {
    viewAuth.classList.add("hidden");
    viewDashboard.classList.remove("hidden");
    if(viewSharedLesson) viewSharedLesson.classList.add("hidden");
    headerUserBadge.classList.remove("hidden");
    
    currentUserName.textContent = activeUser.username;
    currentUserLang.textContent = activeUser.target_language;

    // Switch to Stats Pane by default on login
    switchTab("stats");
  }

  // --- AUTH ROUTINES ---
  tabBtnLogin.addEventListener("click", () => {
    tabBtnLogin.classList.add("active");
    tabBtnRegister.classList.remove("active");
    authSectionLogin.classList.remove("hidden");
    authSectionRegister.classList.add("hidden");
  });

  tabBtnRegister.addEventListener("click", () => {
    tabBtnRegister.classList.add("active");
    tabBtnLogin.classList.remove("active");
    authSectionRegister.classList.remove("hidden");
    authSectionLogin.classList.add("hidden");
  });

  async function loadUsersList() {
    try {
      const response = await fetch("/api/users");
      allUsers = await response.json();
      
      loginUserSelect.innerHTML = '<option value="" disabled selected>Select user profile...</option>';
      allUsers.forEach(u => {
        const option = document.createElement("option");
        option.value = u.user_id;
        option.textContent = `${u.username} (${u.target_language} - ${u.skill_level})`;
        loginUserSelect.appendChild(option);
      });
    } catch (e) {
      console.error("Failed to load profiles:", e);
    }
  }

  formLogin.addEventListener("submit", (e) => {
    e.preventDefault();
    const userId = parseInt(loginUserSelect.value);
    const selected = allUsers.find(u => u.user_id === userId);
    if (selected) {
      activeUser = selected;
      localStorage.setItem("lingo_active_user", JSON.stringify(activeUser));
      
      const urlParams = new URLSearchParams(window.location.search);
      if(urlParams.get("lesson")) {
        showSharedLesson(urlParams.get("lesson"));
      } else {
        showDashboard();
      }
    }
  });

  formRegister.addEventListener("submit", async (e) => {
    e.preventDefault();
    const username = document.getElementById("reg-username").value.trim();
    const target_language = document.getElementById("reg-target-lang").value;
    const skill_level = document.getElementById("reg-skill-level").value;

    try {
      const response = await fetch("/api/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, target_language, skill_level })
      });
      const newUser = await response.json();
      activeUser = newUser;
      localStorage.setItem("lingo_active_user", JSON.stringify(activeUser));
      
      const urlParams = new URLSearchParams(window.location.search);
      if(urlParams.get("lesson")) {
        showSharedLesson(urlParams.get("lesson"));
      } else {
        showDashboard();
      }
    } catch (e) {
      alert("Registration failed. Please try again.");
    }
  });

  btnLogout.addEventListener("click", () => {
    localStorage.removeItem("lingo_active_user");
    showAuth();
  });

  // --- DASHBOARD NAVIGATION ---
  function switchTab(tabId) {
    sideTabs.forEach(t => {
      if (t.dataset.tab === tabId) t.classList.add("active");
      else t.classList.remove("active");
    });

    panes.forEach(p => {
      if (p.id === `pane-${tabId}`) p.classList.add("active");
      else p.classList.remove("active");
    });

    // Fetch tab-specific data
    if (tabId === "stats") loadStatsPane();
    else if (tabId === "media") loadMediaPane();
    else if (tabId === "vocab") loadVocabPane("all");
    else if (tabId === "practice") loadPracticePane();
    else if (tabId === "history") loadHistoryPane();
  }

  sideTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      switchTab(tab.dataset.tab);
    });
  });

  // --- TAB 1: PROFILE & STATISTICS ---
  async function loadStatsPane() {
    document.getElementById("stats-username").textContent = activeUser.username;
    document.getElementById("stats-lang").textContent = activeUser.target_language;
    document.getElementById("stats-level").textContent = activeUser.skill_level;

    // Load statistics
    try {
      // 1. Total Media Items
      const mediaRes = await fetch("/api/media");
      const mediaList = await mediaRes.json();
      // Filter media count by user's target language
      const userMedia = mediaList.filter(m => m.language === activeUser.target_language);
      document.getElementById("stat-total-media").textContent = userMedia.length;

      // 2. Vocabulary Deck
      const vocabRes = await fetch(`/api/vocab?user_id=${activeUser.user_id}`);
      const vocabData = await vocabRes.json();
      const deck = vocabData.deck || [];
      document.getElementById("stat-total-vocab").textContent = deck.length;

      // 3. Quiz History & Avg Score
      const quizRes = await fetch(`/api/quiz_history?user_id=${activeUser.user_id}`);
      const quizLogs = await quizRes.json();
      document.getElementById("stat-total-quizzes").textContent = quizLogs.length;

      if (quizLogs.length > 0) {
        let totalScore = 0;
        let totalQs = 0;
        quizLogs.forEach(q => {
          totalScore += q.score;
          totalQs += q.total_questions;
        });
        const percentage = Math.round((totalScore / totalQs) * 100);
        document.getElementById("stat-avg-score").textContent = `${percentage}%`;
      } else {
        document.getElementById("stat-avg-score").textContent = "0%";
      }

      // 4. Leitner Box Distribution
      const distribution = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
      deck.forEach(item => {
        const box = item.box_number || 1;
        if (distribution[box] !== undefined) distribution[box]++;
      });

      const maxCount = Math.max(...Object.values(distribution), 1);
      for (let b = 1; b <= 5; b++) {
        const count = distribution[b];
        document.getElementById(`box-count-${b}`).textContent = count;
        // calculate bar height percentage (minimum 5% to show bar)
        const heightPct = Math.max((count / maxCount) * 100, count > 0 ? 10 : 0);
        document.getElementById(`box-bar-${b}`).style.height = `${heightPct}%`;
      }

    } catch (e) {
      console.error("Error loading stats:", e);
    }
  }

  // Profile Action hooks
  document.getElementById("btn-edit-profile").addEventListener("click", () => {
    document.getElementById("profile-edit-box").classList.remove("hidden");
    document.getElementById("edit-username").value = activeUser.username;
    document.getElementById("edit-target-lang").value = activeUser.target_language;
    document.getElementById("edit-skill-level").value = activeUser.skill_level;
  });

  document.getElementById("btn-cancel-edit-profile").addEventListener("click", () => {
    document.getElementById("profile-edit-box").classList.add("hidden");
  });

  document.getElementById("form-edit-profile").addEventListener("submit", async (e) => {
    e.preventDefault();
    const username = document.getElementById("edit-username").value.trim();
    const target_language = document.getElementById("edit-target-lang").value;
    const skill_level = document.getElementById("edit-skill-level").value;

    try {
      const response = await fetch(`/api/users/${activeUser.user_id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, target_language, skill_level })
      });
      if (response.ok) {
        activeUser = await response.json();
        localStorage.setItem("lingo_active_user", JSON.stringify(activeUser));
        document.getElementById("profile-edit-box").classList.add("hidden");
        showDashboard();
      } else {
        alert("Failed to update profile.");
      }
    } catch (e) {
      alert("Error updating profile.");
    }
  });

  document.getElementById("btn-delete-profile").addEventListener("click", async () => {
    if (confirm("Are you sure you want to delete this profile? This will clear all study decks and quiz histories and cannot be undone!")) {
      try {
        const response = await fetch(`/api/users/${activeUser.user_id}`, {
          method: "DELETE"
        });
        if (response.ok) {
          alert("Profile deleted successfully.");
          showAuth();
        } else {
          alert("Failed to delete profile.");
        }
      } catch (e) {
        alert("Error deleting profile.");
      }
    }
  });


  // --- TAB 2: LYRICS & MEDIA MANAGER ---
  async function loadMediaPane() {
    try {
      const response = await fetch("/api/media");
      allMedia = await response.json();
      renderMediaTable();
    } catch (e) {
      console.error("Failed to load media:", e);
    }
  }

  function renderMediaTable() {
    const tbody = document.getElementById("media-list-rows");
    tbody.innerHTML = "";

    allMedia.forEach(m => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${escapeHTML(m.title)}</strong></td>
        <td>${escapeHTML(m.artist_or_movie)}</td>
        <td><span class="badge" style="background: rgba(255,255,255,0.05); color: #fff;">${m.media_type === 'song' ? '🎤 Song' : '🎬 Movie'}</span></td>
        <td>${escapeHTML(m.language)}</td>
        <td><span class="badge">${escapeHTML(m.difficulty)}</span></td>
        <td><code style="color: var(--color-secondary);">${escapeHTML(m.video_id || "-")}</code></td>
        <td class="action-buttons-cell">
          <button class="btn btn-primary btn-small btn-share" data-vid="${m.video_id}" title="Copy Share Link" style="background: rgba(0, 240, 255, 0.1); color: var(--accent-cyan); border: 1px solid var(--accent-cyan);">Share 🔗</button>
          <button class="btn btn-secondary btn-small btn-edit" data-id="${m.content_id}">Edit</button>
          <button class="btn btn-danger btn-small btn-delete" data-id="${m.content_id}">Delete</button>
        </td>
      `;
      tbody.appendChild(tr);
    });

    // Attach event listeners to buttons
    tbody.querySelectorAll(".btn-share").forEach(btn => {
      btn.addEventListener("click", () => {
        const vid = btn.dataset.vid;
        if (!vid || vid === "null") {
          alert("This media does not have a video ID for sharing.");
          return;
        }
        const shareUrl = `${window.location.origin}${window.location.pathname}?lesson=${vid}`;
        navigator.clipboard.writeText(shareUrl).then(() => {
          const originalText = btn.innerHTML;
          btn.innerHTML = "Copied! ✓";
          setTimeout(() => btn.innerHTML = originalText, 2000);
        }).catch(() => {
          alert("Failed to copy link: " + shareUrl);
        });
      });
    });

    tbody.querySelectorAll(".btn-edit").forEach(btn => {
      btn.addEventListener("click", () => openMediaModal(parseInt(btn.dataset.id)));
    });

    tbody.querySelectorAll(".btn-delete").forEach(btn => {
      btn.addEventListener("click", () => deleteMedia(parseInt(btn.dataset.id)));
    });
  }

  // Add/Edit Media Handlers
  document.getElementById("btn-add-media").addEventListener("click", () => openMediaModal(null));
  document.getElementById("btn-close-media-modal").addEventListener("click", () => modalMedia.close());
  document.getElementById("btn-cancel-media").addEventListener("click", () => modalMedia.close());

  async function openMediaModal(contentId) {
    const form = document.getElementById("form-media");
    form.reset();
    document.getElementById("media-form-id").value = "";

    if (contentId) {
      document.getElementById("modal-media-title").textContent = "Edit Media Content";
      try {
        const res = await fetch(`/api/media/${contentId}`);
        const m = await res.json();
        document.getElementById("media-form-id").value = m.content_id;
        document.getElementById("media-title").value = m.title;
        document.getElementById("media-artist").value = m.artist_or_movie;
        document.getElementById("media-type").value = m.media_type;
        document.getElementById("media-language").value = m.language;
        document.getElementById("media-difficulty").value = m.difficulty;
        document.getElementById("media-video-id").value = m.video_id || "";
        document.getElementById("media-original").value = m.original_text;
        document.getElementById("media-translated").value = m.translated_text;
        document.getElementById("media-pinyin").value = m.pinyin_text || "";
      } catch (e) {
        alert("Failed to load media details.");
        return;
      }
    } else {
      document.getElementById("modal-media-title").textContent = "Add New Media Content";
      // prefill active language
      document.getElementById("media-language").value = activeUser.target_language;
    }

    modalMedia.showModal();
  }

  document.getElementById("form-media").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("media-form-id").value;
    const body = {
      title: document.getElementById("media-title").value.trim(),
      artist_or_movie: document.getElementById("media-artist").value.trim(),
      media_type: document.getElementById("media-type").value,
      language: document.getElementById("media-language").value,
      difficulty: document.getElementById("media-difficulty").value,
      video_id: document.getElementById("media-video-id").value.trim() || null,
      original_text: document.getElementById("media-original").value,
      translated_text: document.getElementById("media-translated").value,
      pinyin_text: document.getElementById("media-pinyin").value.trim() || null
    };

    const method = id ? "PUT" : "POST";
    const url = id ? `/api/media/${id}` : "/api/media";

    try {
      const response = await fetch(url, {
        method: method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      if (response.ok) {
        modalMedia.close();
        loadMediaPane();
      } else {
        alert("Error saving media.");
      }
    } catch (e) {
      alert("Network error saving media.");
    }
  });

  async function deleteMedia(contentId) {
    if (confirm("Are you sure you want to delete this media item? This will remove all lyrics and dictionary caches from the database.")) {
      try {
        const response = await fetch(`/api/media/${contentId}`, { method: "DELETE" });
        if (response.ok) {
          loadMediaPane();
        } else {
          alert("Failed to delete media.");
        }
      } catch (e) {
        alert("Error deleting media.");
      }
    }
  }


  // --- TAB 3: STUDY DECK (VOCABULARLY FLASHCARDS) ---
  let activeVocabBoxFilter = "all";
  
  async function loadVocabPane(boxFilter) {
    activeVocabBoxFilter = boxFilter;
    
    // Update filter button highlight
    document.querySelectorAll(".filter-btn").forEach(btn => {
      if (btn.dataset.box === boxFilter) btn.classList.add("active");
      else btn.classList.remove("active");
    });

    try {
      const response = await fetch(`/api/vocab?user_id=${activeUser.user_id}`);
      const data = await response.json();
      const deck = data.deck || [];
      
      let filteredDeck = deck;
      if (boxFilter !== "all") {
        const boxNum = parseInt(boxFilter);
        filteredDeck = deck.filter(item => item.box_number === boxNum);
      }

      renderVocabCards(filteredDeck);
    } catch (e) {
      console.error("Failed to load vocab deck:", e);
    }
  }

  // Attach filter buttons click
  document.querySelectorAll(".filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      loadVocabPane(btn.dataset.box);
    });
  });

  function renderVocabCards(cards) {
    const container = document.getElementById("vocab-deck-cards");
    container.innerHTML = "";

    if (cards.length === 0) {
      container.innerHTML = `
        <div class="glass-panel text-center col-span-3">
          <p style="color: var(--color-text-muted);">No flashcards found in this box. Add one or play quizzes to grow your deck!</p>
        </div>
      `;
      return;
    }

    cards.forEach(card => {
      const div = document.createElement("div");
      div.className = "vocab-card glass-panel";
      div.innerHTML = `
        <div>
          <div class="vocab-card-header">
            <span class="vocab-word-large">${escapeHTML(card.word)}</span>
            <span class="vocab-box-badge box-${card.box_number || 1}">Box ${card.box_number || 1}</span>
          </div>
          ${card.pinyin ? `<div class="vocab-pinyin-line">${escapeHTML(card.pinyin)}</div>` : ""}
          <div class="vocab-defn">${escapeHTML(card.translation)}</div>
          <div class="vocab-sentence-ctx">"${escapeHTML(card.context_sentence)}"</div>
        </div>
        <div class="vocab-card-footer">
          <span class="vocab-review-date">Review: ${escapeHTML(card.next_review_date.substring(0, 10))}</span>
          <div class="vocab-card-actions">
            <button class="btn btn-secondary btn-small btn-edit-vocab" data-id="${card.vocab_id}">Edit</button>
            <button class="btn btn-danger btn-small btn-delete-vocab" data-id="${card.vocab_id}">×</button>
          </div>
        </div>
      `;
      container.appendChild(div);
    });

    // Attach card event listeners
    container.querySelectorAll(".btn-edit-vocab").forEach(btn => {
      btn.addEventListener("click", () => openVocabModal(parseInt(btn.dataset.id)));
    });
    container.querySelectorAll(".btn-delete-vocab").forEach(btn => {
      btn.addEventListener("click", () => deleteVocabCard(parseInt(btn.dataset.id)));
    });
  }

  // Add/Edit Flashcard Handlers
  document.getElementById("btn-add-vocab").addEventListener("click", () => openVocabModal(null));
  document.getElementById("btn-close-vocab-modal").addEventListener("click", () => modalVocab.close());
  document.getElementById("btn-cancel-vocab").addEventListener("click", () => modalVocab.close());

  async function openVocabModal(vocabId) {
    const form = document.getElementById("form-vocab");
    form.reset();
    document.getElementById("vocab-form-id").value = "";

    // set default date to tomorrow
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    document.getElementById("vocab-next-review").value = tomorrow.toISOString().substring(0, 10);

    if (vocabId) {
      document.getElementById("modal-vocab-title").textContent = "Edit Vocabulary Flashcard";
      try {
        // Fetch deck list and find card
        const response = await fetch(`/api/vocab?user_id=${activeUser.user_id}`);
        const data = await response.json();
        const card = data.deck.find(c => c.vocab_id === vocabId);
        
        if (card) {
          document.getElementById("vocab-form-id").value = card.vocab_id;
          document.getElementById("vocab-word").value = card.word;
          document.getElementById("vocab-pinyin").value = card.pinyin || "";
          document.getElementById("vocab-translation").value = card.translation;
          document.getElementById("vocab-context").value = card.context_sentence;
          document.getElementById("vocab-box").value = card.box_number;
          document.getElementById("vocab-next-review").value = card.next_review_date.substring(0, 10);
        }
      } catch (e) {
        alert("Failed to load flashcard details.");
        return;
      }
    } else {
      document.getElementById("modal-vocab-title").textContent = "Add Vocabulary Flashcard";
    }

    modalVocab.showModal();
  }

  document.getElementById("form-vocab").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("vocab-form-id").value;
    const body = {
      word: document.getElementById("vocab-word").value.trim(),
      translation: document.getElementById("vocab-translation").value.trim(),
      context_sentence: document.getElementById("vocab-context").value.trim(),
      pinyin: document.getElementById("vocab-pinyin").value.trim() || null,
      box_number: parseInt(document.getElementById("vocab-box").value),
      next_review_date: document.getElementById("vocab-next-review").value
    };

    try {
      if (id) {
        // Update existing via PUT
        const response = await fetch(`/api/vocab/id/${id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body)
        });
        if (response.ok) {
          modalVocab.close();
          loadVocabPane(activeVocabBoxFilter);
        } else {
          alert("Error saving changes to card.");
        }
      } else {
        // Create new manual vocab card via POST
        const response = await fetch("/api/vocab/manual", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: activeUser.user_id, ...body })
        });
        if (response.ok) {
          modalVocab.close();
          loadVocabPane(activeVocabBoxFilter);
        } else {
          alert("Error creating new card.");
        }
      }
    } catch (e) {
      alert("Network error saving flashcard.");
    }
  });

  async function deleteVocabCard(vocabId) {
    if (confirm("Remove this card from your study deck?")) {
      try {
        const response = await fetch(`/api/vocab/id/${vocabId}`, { method: "DELETE" });
        if (response.ok) {
          loadVocabPane(activeVocabBoxFilter);
        } else {
          alert("Failed to delete flashcard.");
        }
      } catch (e) {
        alert("Error deleting flashcard.");
      }
    }
  }


  // --- TAB 4: PRACTICE PLAYER & INTERACTIVE QUIZ ENGINE ---
  async function loadPracticePane() {
    document.getElementById("practice-selector").classList.remove("hidden");
    document.getElementById("practice-active-area").classList.add("hidden");
    document.getElementById("practice-results-area").classList.add("hidden");

    try {
      const response = await fetch("/api/media");
      const list = await response.json();
      
      // Filter options matching target language
      const filtered = list.filter(m => m.language === activeUser.target_language);
      const select = document.getElementById("practice-media-select");
      select.innerHTML = '<option value="" disabled selected>Select Media...</option>';
      
      filtered.forEach(m => {
        const option = document.createElement("option");
        option.value = m.content_id;
        option.textContent = `[${m.difficulty.toUpperCase()}] ${m.title} - ${m.artist_or_movie}`;
        select.appendChild(option);
      });
    } catch (e) {
      console.error("Error loading practice list:", e);
    }
  }

  document.getElementById("btn-start-practice").addEventListener("click", async () => {
    const contentId = document.getElementById("practice-media-select").value;
    if (!contentId) return alert("Please select a media item to practice!");

    try {
      const response = await fetch(`/api/media/${contentId}`);
      const media = await response.json();
      
      const vocabRes = await fetch(`/api/vocab?user_id=${activeUser.user_id}`);
      const vocabData = await vocabRes.json();
      const deck = vocabData.deck || [];
      
      generateQuizSession(media, deck);
    } catch (e) {
      alert("Failed to load practice media content.");
    }
  });

  function generateQuizSession(media, deck) {
    const originalLines = media.original_text.split("\n").map(l => l.trim()).filter(l => l.length > 0);
    const translatedLines = media.translated_text.split("\n").map(l => l.trim()).filter(l => l.length > 0);
    const pinyinLines = media.pinyin_text ? media.pinyin_text.split("\n").map(l => l.trim()) : [];

    if (originalLines.length === 0 || translatedLines.length === 0) {
      return alert("This media item does not have enough lyrics to generate a practice session.");
    }

    const totalQuestions = Math.min(3, originalLines.length);
    const questions = [];

    // Helper to cleanup lines from timestamp tags like [10.0]
    function cleanLine(text) {
      return text.replace(/^\[\d+(\.\d+)?\]/, "").trim();
    }

    // Add 1-3 vocab questions if there are cards due
    const today = new Date().toISOString().substring(0, 10);
    const dueCards = deck.filter(c => c.next_review_date <= today);
    shuffleArray(dueCards);
    const vocabToTest = dueCards.slice(0, 3);
    
    vocabToTest.forEach(card => {
      // Multiple choice for vocab translation
      const wrongOptions = deck.filter(c => c.vocab_id !== card.vocab_id).map(c => c.translation);
      shuffleArray(wrongOptions);
      const selectedWrong = wrongOptions.slice(0, 3);
      const choices = [card.translation, ...selectedWrong];
      // If we don't have enough wrong options, generate some generic ones
      while(choices.length < 4) choices.push("Incorrect translation " + choices.length);
      shuffleArray(choices);
      
      questions.push({
        type: "multiple-choice",
        prompt: `Vocabulary: What does this mean?`,
        mainText: card.word,
        helperText: card.pinyin || "",
        context: card.context_sentence,
        correctAnswer: card.translation,
        choices: choices,
        vocabCard: card // attach card object to track later
      });
    });

    for (let idx = 0; idx < totalQuestions; idx++) {
      const lineIdx = Math.floor((idx / totalQuestions) * originalLines.length);
      const origRaw = originalLines[lineIdx];
      const origClean = cleanLine(origRaw);
      const transClean = cleanLine(translatedLines[lineIdx] || "");
      const pinyinClean = pinyinLines[lineIdx] ? cleanLine(pinyinLines[lineIdx]) : "";

      const qType = idx % 2 === 0 ? "translation" : "blank";

      if (qType === "translation") {
        const wrongOptions = translatedLines
          .map(l => cleanLine(l))
          .filter(l => l !== transClean && l.length > 0);
        
        shuffleArray(wrongOptions);
        const selectedWrong = wrongOptions.slice(0, 3);
        
        const choices = [transClean, ...selectedWrong];
        shuffleArray(choices);

        questions.push({
          type: "multiple-choice",
          prompt: `Translate this sentence:`,
          mainText: origClean,
          helperText: pinyinClean,
          context: `From: ${media.title} by ${media.artist_or_movie}`,
          correctAnswer: transClean,
          choices: choices
        });
      } else {
        let words = origClean.split(/\s+/).filter(w => w.length > 0);
        let blankWord = "";
        let promptText = "";

        if (media.language === "Chinese" && origClean.length > 4) {
          const start = Math.floor(origClean.length / 2) - 1;
          blankWord = origClean.substring(start, start + 2);
          promptText = origClean.substring(0, start) + "_______" + origClean.substring(start + 2);
        } else if (words.length > 2) {
          const wordIdx = Math.floor(words.length / 2);
          blankWord = words[wordIdx].replace(/[.,\/#!$%\^&\*;:{}=\-_`~()]/g,"");
          words[wordIdx] = "_______";
          promptText = words.join(" ");
        } else {
          questions.push({
            type: "text",
            prompt: `Translate this sentence to English:`,
            mainText: origClean,
            helperText: pinyinClean,
            context: transClean,
            correctAnswer: transClean
          });
          continue;
        }

        questions.push({
          type: "text",
          prompt: `Fill in the missing part:`,
          mainText: promptText,
          helperText: pinyinClean,
          context: transClean,
          correctAnswer: blankWord
        });
      }
    }

    shuffleArray(questions);

    activeQuizSession = {
      mediaId: media.content_id,
      mediaTitle: media.title,
      questions: questions,
      currentIndex: 0,
      score: 0,
      vocabResults: [] // To store which cards were right/wrong
    };

    document.getElementById("practice-selector").classList.add("hidden");
    document.getElementById("practice-active-area").classList.remove("hidden");
    showQuestion(0);
  }

  function showQuestion(index) {
    const q = activeQuizSession.questions[index];
    
    document.getElementById("quiz-progress-text").textContent = `Question ${index + 1} of ${activeQuizSession.questions.length}`;
    document.getElementById("quiz-question-prompt").textContent = q.mainText;
    
    if (q.helperText) {
      document.getElementById("quiz-question-pinyin").textContent = q.helperText;
      document.getElementById("quiz-question-pinyin").classList.remove("hidden");
    } else {
      document.getElementById("quiz-question-pinyin").classList.add("hidden");
    }

    document.getElementById("quiz-question-context").innerHTML = `<strong>Context:</strong> ${escapeHTML(q.context || "")}`;

    // Reset feedback
    const feedbackBox = document.getElementById("quiz-feedback-banner");
    feedbackBox.classList.add("hidden");

    // Render Options
    const optionsContainer = document.getElementById("quiz-options");
    optionsContainer.innerHTML = "";

    if (q.type === "multiple-choice") {
      q.choices.forEach(choice => {
        const btn = document.createElement("button");
        btn.className = "quiz-option-btn";
        btn.textContent = choice;
        btn.addEventListener("click", () => {
          optionsContainer.querySelectorAll(".quiz-option-btn").forEach(b => b.classList.remove("selected"));
          btn.classList.add("selected");
        });
        optionsContainer.appendChild(btn);
      });
    } else {
      // Text Input
      const input = document.createElement("input");
      input.type = "text";
      input.id = "quiz-text-answer";
      input.className = "form-input quiz-option-text-input";
      input.placeholder = "Type your answer here...";
      optionsContainer.appendChild(input);
    }

    // Toggle check/next buttons
    document.getElementById("btn-submit-quiz-answer").classList.remove("hidden");
    document.getElementById("btn-next-quiz-question").classList.add("hidden");
  }

  document.getElementById("btn-submit-quiz-answer").addEventListener("click", () => {
    const q = activeQuizSession.questions[activeQuizSession.currentIndex];
    let userAnswer = "";

    if (q.type === "multiple-choice") {
      const selectedBtn = document.getElementById("quiz-options").querySelector(".quiz-option-btn.selected");
      if (!selectedBtn) return alert("Please select an option!");
      userAnswer = selectedBtn.textContent.trim();
    } else {
      const input = document.getElementById("quiz-text-answer");
      userAnswer = input.value.trim();
      if (!userAnswer) return alert("Please enter your answer!");
    }

    // Check correctness
    const isCorrect = userAnswer.toLowerCase() === q.correctAnswer.toLowerCase();
    if (isCorrect) {
      activeQuizSession.score++;
    }
    
    if (q.vocabCard) {
      activeQuizSession.vocabResults.push({ card: q.vocabCard, isCorrect });
    }

    // Display Feedback
    const feedbackBox = document.getElementById("quiz-feedback-banner");
    const status = document.getElementById("quiz-feedback-status");
    const desc = document.getElementById("quiz-feedback-explanation");

    feedbackBox.className = "quiz-feedback-box " + (isCorrect ? "correct" : "incorrect");
    status.textContent = isCorrect ? "✨ Correct!" : "❌ Incorrect";
    desc.innerHTML = `Your Answer: <strong>${escapeHTML(userAnswer)}</strong><br>Correct Answer: <strong>${escapeHTML(q.correctAnswer)}</strong>`;
    feedbackBox.classList.remove("hidden");

    // Toggle action buttons
    document.getElementById("btn-submit-quiz-answer").classList.add("hidden");
    document.getElementById("btn-next-quiz-question").classList.remove("hidden");
  });

  document.getElementById("btn-next-quiz-question").addEventListener("click", () => {
    activeQuizSession.currentIndex++;
    if (activeQuizSession.currentIndex < activeQuizSession.questions.length) {
      showQuestion(activeQuizSession.currentIndex);
    } else {
      // Completed quiz! Show results view
      showQuizResults();
    }
  });

  function showQuizResults() {
    document.getElementById("practice-active-area").classList.add("hidden");
    document.getElementById("practice-results-area").classList.remove("hidden");
    
    const score = activeQuizSession.score;
    const total = activeQuizSession.questions.length;
    document.getElementById("quiz-results-score").textContent = `${score}/${total}`;
    document.getElementById("quiz-results-notes").value = `Finished practice session for '${activeQuizSession.mediaTitle}'. Scored ${score} out of ${total}.`;
  }

  // Save Quiz session to History CRUD
  document.getElementById("btn-save-quiz-notes").addEventListener("click", async () => {
    const notes = document.getElementById("quiz-results-notes").value.trim();
    
    const body = {
      user_id: activeUser.user_id,
      content_id: activeQuizSession.mediaId,
      score: activeQuizSession.score,
      total_questions: activeQuizSession.questions.length,
      notes: notes
    };

    try {
      const response = await fetch("/api/quiz_history", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      
      // Also update spaced repetition for tested vocab
      if(activeQuizSession.vocabResults && activeQuizSession.vocabResults.length > 0) {
        for(let r of activeQuizSession.vocabResults) {
          let c = r.card;
          let newBox = r.isCorrect ? Math.min(5, c.box_number + 1) : Math.max(1, c.box_number - 1);
          
          let nextDate = new Date();
          if(newBox === 1) nextDate.setDate(nextDate.getDate() + 1);
          else if(newBox === 2) nextDate.setDate(nextDate.getDate() + 2);
          else if(newBox === 3) nextDate.setDate(nextDate.getDate() + 7);
          else if(newBox === 4) nextDate.setDate(nextDate.getDate() + 14);
          else nextDate.setMonth(nextDate.getMonth() + 1);
          
          await fetch(`/api/vocab/id/${c.vocab_id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              word: c.word,
              translation: c.translation,
              context_sentence: c.context_sentence,
              pinyin: c.pinyin,
              box_number: newBox,
              next_review_date: nextDate.toISOString().substring(0, 10)
            })
          });
        }
      }

      if (response.ok) {
        switchTab("history");
      } else {
        alert("Failed to log results. Exiting to dashboard.");
        switchTab("stats");
      }
    } catch (e) {
      switchTab("stats");
    }
  });

  document.getElementById("btn-exit-quiz").addEventListener("click", () => {
    switchTab("stats");
  });


  // --- TAB 5: STUDY & QUIZ HISTORY LOGS ---
  let allHistory = [];

  async function loadHistoryPane() {
    try {
      const response = await fetch(`/api/quiz_history?user_id=${activeUser.user_id}`);
      allHistory = await response.json();
      renderHistoryTable();
    } catch (e) {
      console.error("Failed to load history:", e);
    }
  }

  function renderHistoryTable() {
    const tbody = document.getElementById("history-list-rows");
    tbody.innerHTML = "";

    if (allHistory.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" class="text-center" style="color: var(--color-text-muted); padding: 2rem;">No study sessions logged yet. Complete a quiz to log your first session!</td>
        </tr>
      `;
      return;
    }

    allHistory.forEach(item => {
      const accuracy = Math.round((item.score / item.total_questions) * 100);
      const date = new Date(item.date_taken).toLocaleDateString(undefined, {
        year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
      });

      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${date}</td>
        <td><strong>${escapeHTML(item.media_title)}</strong></td>
        <td>${item.score} / ${item.total_questions}</td>
        <td><span class="badge" style="background: rgba(16, 185, 129, 0.15); color: var(--color-success);">${accuracy}%</span></td>
        <td style="max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHTML(item.notes || "-")}</td>
        <td class="action-buttons-cell">
          <button class="btn btn-secondary btn-small btn-edit-history" data-id="${item.quiz_id}">Edit Notes</button>
          <button class="btn btn-danger btn-small btn-delete-history" data-id="${item.quiz_id}">×</button>
        </td>
      `;
      tbody.appendChild(tr);
    });

    tbody.querySelectorAll(".btn-edit-history").forEach(btn => {
      btn.addEventListener("click", () => openHistoryModal(parseInt(btn.dataset.id)));
    });

    tbody.querySelectorAll(".btn-delete-history").forEach(btn => {
      btn.addEventListener("click", () => deleteHistoryRecord(parseInt(btn.dataset.id)));
    });
  }

  // Edit Notes dialog hooks
  document.getElementById("btn-close-history-modal").addEventListener("click", () => modalHistory.close());
  document.getElementById("btn-cancel-history").addEventListener("click", () => modalHistory.close());

  async function openHistoryModal(quizId) {
    const item = allHistory.find(h => h.quiz_id === quizId);
    if (!item) return;

    document.getElementById("history-form-id").value = item.quiz_id;
    document.getElementById("history-notes").value = item.notes || "";
    modalHistory.showModal();
  }

  document.getElementById("form-history").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("history-form-id").value;
    const notes = document.getElementById("history-notes").value.trim();

    try {
      const response = await fetch(`/api/quiz_history/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes })
      });
      if (response.ok) {
        modalHistory.close();
        loadHistoryPane();
      } else {
        alert("Failed to save notes.");
      }
    } catch (e) {
      alert("Error saving notes.");
    }
  });

  async function deleteHistoryRecord(quizId) {
    if (confirm("Delete this session record? This removes it from your analytics and logs.")) {
      try {
        const response = await fetch(`/api/quiz_history/${quizId}`, { method: "DELETE" });
        if (response.ok) {
          loadHistoryPane();
        } else {
          alert("Failed to delete history record.");
        }
      } catch (e) {
        alert("Error deleting record.");
      }
    }
  }

  // --- GENERAL HELPERS ---
  function shuffleArray(array) {
    for (let i = array.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [array[i], array[j]] = [array[j], array[i]];
    }
  }

  function escapeHTML(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

});
// This code will be injected into app.js
let ytPlayer = null;
let currentLessonData = null;

async function showSharedLesson(videoId) {
  viewAuth.classList.add("hidden");
  viewDashboard.classList.add("hidden");
  viewSharedLesson.classList.remove("hidden");
  headerUserBadge.classList.add("hidden"); // Optional: Keep hidden or show logged-in user

  if (activeUser) {
    headerUserBadge.classList.remove("hidden");
    btnLessonLogin.classList.add("hidden");
    btnLessonDashboard.classList.remove("hidden");
  } else {
    btnLessonLogin.classList.remove("hidden");
    btnLessonDashboard.classList.add("hidden");
  }

  btnLessonDashboard.onclick = () => {
    window.history.pushState({}, document.title, window.location.pathname);
    showDashboard();
  };
  btnLessonLogin.onclick = () => {
    viewSharedLesson.classList.add("hidden");
    showAuth();
  };

  try {
    const res = await fetch(`/api/share/${videoId}`);
    if (!res.ok) throw new Error("Lesson not found");
    const data = await res.json();
    currentLessonData = data;
    
    document.getElementById("lesson-title").textContent = data.title;
    document.getElementById("lesson-tutorial-content").innerHTML = data.tutorial.replace(/\n/g, '<br>');
    
    // Process lyrics
    const originalLines = data.original_text.split('\n');
    const pinyinLines = (data.pinyin_text || "").split('\n');
    const transLines = (data.translated_text || "").split('\n');
    
    const lyricsBox = document.getElementById("lesson-lyrics-box");
    lyricsBox.innerHTML = "";
    
    const linesData = [];
    
    for(let i=0; i<originalLines.length; i++) {
      let orig = originalLines[i];
      let timeMatch = orig.match(/^\[([\d\.]+)\](.*)/);
      let t = 0;
      let text = orig;
      if (timeMatch) {
        t = parseFloat(timeMatch[1]);
        text = timeMatch[2];
      }
      
      let pinyin = pinyinLines[i] || "";
      if(pinyin.startsWith("[")) pinyin = pinyin.replace(/^\[[\d\.]+\]/, "");
      
      let trans = transLines[i] || "";
      if(trans.startsWith("[")) trans = trans.replace(/^\[[\d\.]+\]/, "");
      
      linesData.push({ time: t, text, pinyin, trans });
      
      const div = document.createElement("div");
      div.className = "lyric-line";
      div.style.padding = "10px";
      div.style.borderBottom = "1px solid var(--bg-glass-border)";
      div.style.cursor = "pointer";
      div.dataset.time = t;
      div.innerHTML = `
        <div style="font-size: 1.2rem; font-weight: 500;">${text}</div>
        <div style="font-size: 0.9rem; color: var(--accent-cyan);">${pinyin}</div>
        <div style="font-size: 0.85rem; color: var(--text-secondary);">${trans}</div>
      `;
      div.onclick = () => {
        if(ytPlayer && ytPlayer.seekTo) {
          ytPlayer.seekTo(t, true);
          ytPlayer.playVideo();
        }
      };
      lyricsBox.appendChild(div);
    }
    
    // Highlight loop
    setInterval(() => {
      if(!ytPlayer || !ytPlayer.getCurrentTime) return;
      const ct = ytPlayer.getCurrentTime();
      let activeIndex = -1;
      for(let i=0; i<linesData.length; i++){
        if(ct >= linesData[i].time) activeIndex = i;
      }
      const children = lyricsBox.children;
      for(let i=0; i<children.length; i++){
        if(i === activeIndex) {
          children[i].style.background = "rgba(0, 240, 255, 0.1)";
          children[i].style.borderLeft = "3px solid var(--accent-cyan)";
          // Simple auto-scroll
          if(children[i].offsetTop > lyricsBox.scrollTop + lyricsBox.clientHeight - 100) {
            lyricsBox.scrollTop = children[i].offsetTop - 100;
          }
        } else {
          children[i].style.background = "none";
          children[i].style.borderLeft = "none";
        }
      }
    }, 500);
    
    // Process vocabulary
    const vocabBox = document.getElementById("lesson-vocab-box");
    vocabBox.innerHTML = "";
    let dictionary = [];
    try { dictionary = JSON.parse(data.dictionary_json); } catch(e){}
    
    dictionary.forEach(v => {
      const vdiv = document.createElement("div");
      vdiv.className = "vocab-item glass-panel";
      vdiv.style.padding = "10px";
      vdiv.style.marginBottom = "10px";
      vdiv.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <div>
            <strong style="font-size: 1.1rem;">${v.word}</strong> <span style="color:var(--accent-pink);">${v.pinyin}</span>
            <div style="font-size:0.85rem;">${v.translation}</div>
          </div>
          <button class="btn btn-secondary btn-sm save-vocab-btn" style="padding: 4px 8px; font-size: 0.7rem;">Save Word</button>
        </div>
      `;
      const saveBtn = vdiv.querySelector(".save-vocab-btn");
      saveBtn.onclick = () => {
        if(!activeUser) {
          alert("Please login or register to save vocabulary.");
          viewSharedLesson.classList.add("hidden");
          showAuth();
          return;
        }
        // Save word logic
        fetch("/api/vocab/manual", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            user_id: activeUser.user_id,
            word: v.word,
            translation: v.translation,
            context_sentence: `From ${data.title}: ${v.explanation || ''}`,
            pinyin: v.pinyin,
            box_number: 1
          })
        }).then(r => r.json()).then(res => {
          saveBtn.textContent = "Saved ✓";
          saveBtn.disabled = true;
        }).catch(err => alert("Error saving word"));
      };
      vocabBox.appendChild(vdiv);
    });

    // Init YouTube Player
    const container = document.getElementById("youtube-player-container");
    container.innerHTML = `<div id="yt-player"></div>`;
    
    // Check if YT API is ready
    if(window.YT && window.YT.Player) {
      ytPlayer = new YT.Player('yt-player', {
        height: '100%',
        width: '100%',
        videoId: videoId,
        playerVars: { 'playsinline': 1 },
        events: {
          'onReady': (e) => { e.target.playVideo(); }
        }
      });
    } else {
      window.onYouTubeIframeAPIReady = () => {
        ytPlayer = new YT.Player('yt-player', {
          height: '100%',
          width: '100%',
          videoId: videoId,
          playerVars: { 'playsinline': 1 },
          events: {
            'onReady': (e) => { e.target.playVideo(); }
          }
        });
      };
    }

  } catch (err) {
    console.error(err);
    document.getElementById("lesson-title").textContent = "Lesson not found or error loading.";
  }
}
