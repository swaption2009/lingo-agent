# LingoKaraoke (Track: Agents for Good - Education)

An interactive, multi-agent Chinese language tutoring system built with the **Google Antigravity SDK** (ADK) and **gemini-agents-cli** skills. The project matches the **Agents for Good** track (Advancing Education) by helping users learn Chinese through their favorite YouTube music videos (Karaoke).

---

## 🌐 Landing Page

A promotional landing page for LingoKaraoke lives in [`landing/`](landing/) — a self-contained static site (HTML/CSS/vanilla JS, no build step, WebP-optimized screenshots).

* **Live (GitHub Pages):** `https://swaption2009.github.io/lingo-agent/` — enable once via **Settings → Pages → Source: "GitHub Actions"**. The [`deploy-pages.yml`](.github/workflows/deploy-pages.yml) workflow then republishes `landing/` on every push to `main`.
* **Local:** open `landing/index.html` directly, serve it with `python3 -m http.server -d landing`, or view it through the FastAPI backend at `http://localhost:8001/landing/` (the root `/` is reserved by the ADK dev UI).

---

## 🏗️ Architecture & Multi-Agent Design

The system implements a cooperative multi-agent architecture with three specialized agents:

```mermaid
graph TD
    User([User]) <--> LingoHost[LingoHost Orchestrator]
    LingoHost <--> MCPServer[MCP Server: LingoMCP]
    LingoHost --> ParserAgent[LingoParser Agent]
    LingoHost --> CoachAgent[LingoCoach Agent]
    ParserAgent -.-> SkillParser[Skill: lyric-analyzer]
    CoachAgent -.-> SkillQuiz[Skill: quiz-generator]
```

1. **`lingo_host` (Orchestrator)**: Main entry point. Greets the user, retrieves their Chinese learner profile, searches the database for songs, and coordinates lesson handoffs.
2. **`lingo_parser` (Segmentation Sub-agent)**: Segments Chinese lyrics line-by-line, generates translations, selects focus vocabulary, and automatically structures Hanyu Pinyin with tone marks using the `lyric-analyzer` Skill.
3. **`lingo_coach` (Quiz & Vocabulary Sub-agent)**: Explains the grammar context, generates interactive quizzes using the `quiz-generator` Skill, evaluates user answers, and logs learned words with tone-marked Hanyu Pinyin to their spaced repetition deck.

---

## 🌟 Core Concepts Implemented

### 1. Custom Stdio MCP Server (`mcp_server.py`) & SQLite Cache
Built using FastMCP to connect agents to a local SQLite database (`lingo_database.db`). Exposes tools:
* `get_user_profile(user_id)`: Fetches target language (Chinese) and skill level.
* `search_learning_media(query, language)`: Searches matching Chinese songs.
* `get_media_content(content_id)`: Fetches original lyrics, translations, and Pinyin.
* `add_vocabulary_word(word, translation, context, pinyin)`: Adds Chinese words (with Hanyu Pinyin) to the user's spaced-repetition deck.
* `delete_vocabulary_word(word)`: Clears a card.
* `reset_vocab_deck()`: Resets learner progress.
* `mcp_analyze_youtube_video(video_id, title)`: Performs automated transcription, translation, and Hanyu Pinyin structuring of YouTube videos.

### 2. Intelligent Chinese Lyrics & Video Analyzer (`app/chinese_analyzer.py`)
Processes YouTube watch page content:
* **Captions Integration**: Fetches captions via `youtube-transcript-api` and prefixes lines with timing metadata, e.g. `[12.5]`.
* **Grounded Search Fallback**: For videos without captions, uses Gemini with the Google Search Grounding Tool to retrieve real, verbatim Chinese lyrics from the web (avoiding hallucinations).
* **Timing-Preserving Caching**: Zips stored newline-delimited lyrics, translations, and Pinyin, maintaining original `[seconds]` timing prefixes for real-time highlighting.
* **In-Place DB Migrations**: Idempotently alters older SQLite database schemas at runtime using `ALTER TABLE` to append post-release metadata fields.

### 3. Modular Agent Skills (`.agents/skills/`)
Implements procedural knowledge and templates:
* **`lyric-analyzer`**: Instruction playbooks for lyric breakdown, Hanyu Pinyin alignment, and vocabulary selection.
* **`quiz-generator`**: Gherkin-aligned instructions for producing fill-in-the-blank, multiple-choice, and translation quizzes.

### 4. Vibe Diff Safety Hook (`app/agent.py`)
Intercepts high-stakes database modifications (`add_vocabulary_word`, `delete_vocabulary_word`, `reset_vocab_deck`) and directory traversal attempts:
* Displays a **Vibe Diff** summary highlighting the requested change.
* Prompts for terminal confirmation: `Do you approve this database change? (y/N)`.
* Automatically bypasses interactive prompts in non-interactive (automated test) environments to prevent execution hangs.

---

## 🚀 Quick Start & Local Run

### Prerequisites
* **uv**: Python package manager.
* **agents-cli**: Google Agents CLI (`uv tool install google-agents-cli`).

### Setup & Installation
1. Initialize the SQLite database with sample Chinese Karaoke songs ("甜蜜蜜", "童话"):
   ```bash
   uv run init_db.py
   ```
2. Start the interactive console playground:
   ```bash
   agents-cli playground
   ```
3. (Optional) Run the CLI directly:
   ```bash
   agents-cli run "Search for 甜蜜蜜 and start practicing it"
   ```

### 🖥️ Running the Backend Server
The Chrome Extension frontend communicates with a local FastAPI backend server. To launch the backend:
1. Start the FastAPI server using `uvicorn` on port `8001` (to match the extension's configured port):
   ```bash
   uv run uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8001 --reload
   ```
2. Access the administrative/monitoring dashboard by navigating to:
   ```
   http://localhost:8001/dashboard
   ```

### 🧩 Installing the Chrome Extension (Frontend)
To install the companion Chrome Extension:
1. Open Google Chrome and navigate to `chrome://extensions/`.
2. Enable **Developer mode** using the toggle switch in the top-right corner.
3. Click the **Load unpacked** button in the top-left corner.
4. Select the `chrome_extension` folder located in the root of this project directory.
5. Pin the extension to your Chrome toolbar.
6. Open any YouTube video page (e.g. Chinese Karaoke or music videos) and click the extension icon to launch the **Lingo Karaoke** interactive learning panel in Chrome's side panel!

---

## 🧪 Verification & Testing

### 1. Unit & Integration Tests
Run the entire test suite with pytest:
```bash
uv run pytest
```
*(All 24 unit and e2e integration tests pass successfully).*

### 2. Trajectory Evaluations
Run the ADK evaluation suite to test greeting flows, Chinese search routing, and vocabulary logging:
```bash
agents-cli eval run --evalset tests/eval/evalsets/lingo_agent.evalset.json --config tests/eval/eval_config.json
```
*(All 3 evaluation cases pass with a perfect 1.0 trajectory and response quality score).*
