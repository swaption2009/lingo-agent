import os
import re
import sqlite3
import google.auth
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.adk.cli.fast_api import get_fast_api_app
from google.cloud import logging as google_cloud_logging

from app.app_utils.telemetry import setup_telemetry
from app.app_utils.typing import Feedback

setup_telemetry()

try:
    _, project_id = google.auth.default()
except google.auth.exceptions.DefaultCredentialsError:
    project_id = "test-project"

logging_client = google_cloud_logging.Client()
logger = logging_client.logger(__name__)

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
session_service_uri = None
logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")
artifact_service_uri = f"gs://{logs_bucket_name}" if logs_bucket_name else None

# Initialize base ADK FastAPI app
app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=artifact_service_uri,
    allow_origins=["*"], # Allow all origins in the ADK middleware
    session_service_uri=session_service_uri,
    otel_to_cloud=True,
)
app.title = "lingo-agent"
app.description = "API for interacting with the Agent lingo-agent"

# Explicitly add CORS Middleware to allow requests from Chrome Browser Extensions (chrome-extension://)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    """Collect and log feedback.

    Args:
        feedback: The feedback data to log

    Returns:
        Success message
    """
    logger.log_struct(feedback.model_dump(), severity="INFO")
    return {"status": "success"}


# --- CHROME EXTENSION API ENDPOINTS ---

DB_PATH = "lingo_database.db"

class YoutubeAnalysisRequest(BaseModel):
    video_id: str
    title: str = ""
    force: bool = False

class VocabAddRequest(BaseModel):
    word: str
    translation: str
    context: str
    pinyin: str = None
    user_id: int = 2 # Default to user 2 (Chinese learner)

@app.get("/api/profile")
def api_get_profile(user_id: int = 2):
    """Retrieves user profile information."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, target_language, skill_level FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "user_id": row[0],
            "username": row[1],
            "target_language": row[2],
            "skill_level": row[3]
        }
    raise HTTPException(status_code=404, detail="User profile not found")

@app.post("/api/youtube/analyze")
def api_analyze_youtube(req: YoutubeAnalysisRequest):
    """Analyzes a YouTube video transcript using the Chinese Analyzer."""
    from app.chinese_analyzer import analyze_youtube_video
    try:
        res = analyze_youtube_video(req.video_id, req.title, req.force)
        if "error" in res:
            raise HTTPException(status_code=400, detail=res["error"])
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/api/vocab")
def api_get_vocab(user_id: int = 2):
    """Retrieves saved vocabulary list for user."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT vocab_id, word, translation, context_sentence, phonetic, box_number, next_review_date 
    FROM vocabulary_deck WHERE user_id = ?
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    deck = []
    for r in rows:
        deck.append({
            "vocab_id": r[0],
            "word": r[1],
            "translation": r[2],
            "context_sentence": r[3],
            "pinyin": r[4],
            "box_number": r[5],
            "next_review_date": r[6]
        })
    return {"deck": deck}

@app.post("/api/vocab")
def api_add_vocab(req: VocabAddRequest):
    """Adds a new vocabulary word/phrase."""
    from mcp_server import add_vocabulary_word
    res = add_vocabulary_word(
        word=req.word,
        translation=req.translation,
        context=req.context,
        user_id=req.user_id,
        pinyin=req.pinyin
    )
    if res.get("status") == "already_exists":
        return {"status": "already_exists", "message": res["message"]}
    return res

@app.delete("/api/vocab/{word}")
def api_delete_vocab(word: str, user_id: int = 2):
    """Deletes a vocabulary word."""
    from mcp_server import delete_vocabulary_word
    return delete_vocabulary_word(word, user_id)


# --- ADDITIONAL CRUD ENDPOINTS FOR DASHBOARD ---

class UserCreateRequest(BaseModel):
    username: str
    target_language: str
    skill_level: str

class UserUpdateRequest(BaseModel):
    username: str
    target_language: str
    skill_level: str

class MediaCreateUpdateRequest(BaseModel):
    title: str
    artist_or_movie: str
    media_type: str
    language: str
    difficulty: str
    original_text: str
    translated_text: str
    pinyin_text: str = None
    video_id: str = None
    dictionary_json: str = None
    tutorial: str = None
    source: str = None

class TimestampsUpdateRequest(BaseModel):
    timestamps: list[float]

class LyricLineItem(BaseModel):
    text: str
    pinyin: str
    translation: str

class LyricsUpdateRequest(BaseModel):
    lines: list[LyricLineItem]

class VocabManualAddRequest(BaseModel):
    user_id: int
    word: str
    translation: str
    context_sentence: str
    pinyin: str = None
    box_number: int = 1
    next_review_date: str = None

class VocabUpdateRequest(BaseModel):
    word: str
    translation: str
    context_sentence: str
    pinyin: str = None
    box_number: int = 1
    next_review_date: str = None

class QuizHistoryCreateRequest(BaseModel):
    user_id: int
    content_id: int
    score: int
    total_questions: int
    notes: str = ""
    date_taken: str = None

class QuizHistoryUpdateRequest(BaseModel):
    notes: str
    score: int = None
    total_questions: int = None


# User CRUD Endpoints


from app.config import load_language_config

@app.get("/api/config")
def get_config():
    return load_language_config()

@app.get("/api/users")
def api_get_users():
    """Retrieves all user profiles."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, target_language, skill_level FROM users")
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "user_id": r[0],
            "username": r[1],
            "target_language": r[2],
            "skill_level": r[3]
        } for r in rows
    ]

@app.post("/api/users")
def api_create_user(req: UserCreateRequest):
    """Creates a new user profile."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (username, target_language, skill_level) VALUES (?, ?, ?)",
        (req.username, req.target_language, req.skill_level)
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {
        "user_id": user_id,
        "username": req.username,
        "target_language": req.target_language,
        "skill_level": req.skill_level
    }

@app.put("/api/users/{user_id}")
def api_update_user(user_id: int, req: UserUpdateRequest):
    """Updates a user profile."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET username = ?, target_language = ?, skill_level = ? WHERE user_id = ?",
        (req.username, req.target_language, req.skill_level, user_id)
    )
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    conn.commit()
    conn.close()
    return {
        "user_id": user_id,
        "username": req.username,
        "target_language": req.target_language,
        "skill_level": req.skill_level
    }

@app.delete("/api/users/{user_id}")
def api_delete_user(user_id: int):
    """Deletes a user profile and cleans up their vocabulary deck and quiz history."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Delete quiz history
    cursor.execute("DELETE FROM quiz_history WHERE user_id = ?", (user_id,))
    # Delete vocab deck
    cursor.execute("DELETE FROM vocabulary_deck WHERE user_id = ?", (user_id,))
    # Delete user
    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"User {user_id} and all their study data deleted."}


# Media Content CRUD Endpoints

@app.get("/api/media")
def api_get_all_media():
    """Retrieves all media content items."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT content_id, title, artist_or_movie, media_type, language, difficulty, video_id 
        FROM media_content
    """)
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "content_id": r[0],
            "title": r[1],
            "artist_or_movie": r[2],
            "media_type": r[3],
            "language": r[4],
            "difficulty": r[5],
            "video_id": r[6]
        } for r in rows
    ]

@app.get("/api/media/{content_id}")
def api_get_media_detail(content_id: int):
    """Retrieves detailed media content by ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT content_id, title, artist_or_movie, media_type, language, difficulty, 
               original_text, translated_text, phonetic_text, video_id, dictionary_json, tutorial, source
        FROM media_content WHERE content_id = ?
    """, (content_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Media content not found")
    return {
        "content_id": row[0],
        "title": row[1],
        "artist_or_movie": row[2],
        "media_type": row[3],
        "language": row[4],
        "difficulty": row[5],
        "original_text": row[6],
        "translated_text": row[7],
        "pinyin_text": row[8],
        "video_id": row[9],
        "dictionary_json": row[10],
        "tutorial": row[11],
        "source": row[12]
    }

@app.post("/api/media")
def api_create_media(req: MediaCreateUpdateRequest):
    """Creates new media content."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO media_content (title, artist_or_movie, media_type, language, difficulty, 
                                   original_text, translated_text, phonetic_text, video_id, dictionary_json, tutorial, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        req.title, req.artist_or_movie, req.media_type, req.language, req.difficulty,
        req.original_text, req.translated_text, req.pinyin_text, req.video_id,
        req.dictionary_json, req.tutorial, req.source
    ))
    content_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"content_id": content_id, **req.model_dump()}

@app.put("/api/media/{content_id}")
def api_update_media(content_id: int, req: MediaCreateUpdateRequest):
    """Updates existing media content."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE media_content 
        SET title = ?, artist_or_movie = ?, media_type = ?, language = ?, difficulty = ?, 
            original_text = ?, translated_text = ?, phonetic_text = ?, video_id = ?, 
            dictionary_json = ?, tutorial = ?, source = ?
        WHERE content_id = ?
    """, (
        req.title, req.artist_or_movie, req.media_type, req.language, req.difficulty,
        req.original_text, req.translated_text, req.pinyin_text, req.video_id,
        req.dictionary_json, req.tutorial, req.source, content_id
    ))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Media content not found")
    conn.commit()
    conn.close()
    return {"content_id": content_id, **req.model_dump()}

@app.delete("/api/media/{content_id}")
def api_delete_media(content_id: int):
    """Deletes media content from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM media_content WHERE content_id = ?", (content_id,))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Media content not found")
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Media content {content_id} deleted."}

@app.put("/api/media/{content_id}/timestamps")
def api_update_media_timestamps(content_id: int, req: TimestampsUpdateRequest):
    """Updates the start timestamps of the lyrics lines for a given media content."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT original_text, pinyin_text, translated_text 
        FROM media_content WHERE content_id = ?
    """, (content_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Media content not found")
    
    original_text, pinyin_text, translated_text = row
    
    orig_lines = original_text.split("\n")
    pinyin_lines = pinyin_text.split("\n") if pinyin_text else []
    trans_lines = translated_text.split("\n") if translated_text else []
    
    def strip_timestamp(text: str) -> str:
        # Match e.g., "[12.34]"
        match = re.match(r"^\[[\d.]+\](.*)", text)
        if match:
            return match.group(1)
        return text

    new_orig = []
    new_pinyin = []
    new_trans = []
    
    for i in range(len(orig_lines)):
        t = req.timestamps[i] if i < len(req.timestamps) else None
        
        orig_clean = strip_timestamp(orig_lines[i])
        pinyin_clean = strip_timestamp(pinyin_lines[i]) if i < len(pinyin_lines) else ""
        trans_clean = strip_timestamp(trans_lines[i]) if i < len(trans_lines) else ""
        
        if t is not None:
            new_orig.append(f"[{t:.1f}]{orig_clean}")
            if pinyin_clean or i < len(pinyin_lines):
                new_pinyin.append(f"[{t:.1f}]{pinyin_clean}")
            if trans_clean or i < len(trans_lines):
                new_trans.append(f"[{t:.1f}]{trans_clean}")
        else:
            new_orig.append(orig_clean)
            if pinyin_clean or i < len(pinyin_lines):
                new_pinyin.append(pinyin_clean)
            if trans_clean or i < len(trans_lines):
                new_trans.append(trans_clean)
                
    new_original_text = "\n".join(new_orig)
    new_pinyin_text = "\n".join(new_pinyin)
    new_translated_text = "\n".join(new_trans)
    
    cursor.execute("""
        UPDATE media_content
        SET original_text = ?, phonetic_text = ?, translated_text = ?
        WHERE content_id = ?
    """, (new_original_text, new_pinyin_text, new_translated_text, content_id))
    
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Timestamps updated successfully"}

@app.get("/api/media/check/{video_id}")
def api_check_media_exists(video_id: str):
    """Checks if lyrics/analysis already exist for a given YouTube video ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT content_id, title 
        FROM media_content WHERE video_id = ?
    """, (video_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"exists": True, "content_id": row[0], "title": row[1]}
    return {"exists": False}

@app.put("/api/media/{content_id}/lyrics")
def api_update_media_lyrics(content_id: int, req: LyricsUpdateRequest):
    """Updates the entire lyrics list (adding, deleting, duplicating, or reordering lines) for a given media content."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT content_id FROM media_content WHERE content_id = ?", (content_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Media content not found")
        
    original_text = "\n".join(line.text for line in req.lines)
    pinyin_text = "\n".join(line.pinyin for line in req.lines)
    translated_text = "\n".join(line.translation for line in req.lines)
    
    cursor.execute("""
        UPDATE media_content
        SET original_text = ?, phonetic_text = ?, translated_text = ?
        WHERE content_id = ?
    """, (original_text, pinyin_text, translated_text, content_id))
    
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Lyrics updated successfully"}


# Vocabulary Deck Additional CRUD Endpoints

@app.post("/api/vocab/manual")
def api_add_vocab_manual(req: VocabManualAddRequest):
    """Manually adds a vocabulary card with customizable spaced repetition properties."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if word already exists in deck for this user
    cursor.execute("SELECT vocab_id FROM vocabulary_deck WHERE user_id = ? AND word = ?", (req.user_id, req.word))
    existing = cursor.fetchone()
    
    import datetime
    next_review = req.next_review_date or (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    
    if existing:
        cursor.execute("""
            UPDATE vocabulary_deck 
            SET translation = ?, context_sentence = ?, phonetic = ?, box_number = ?, next_review_date = ?
            WHERE vocab_id = ?
        """, (req.translation, req.context_sentence, req.pinyin, req.box_number, next_review, existing[0]))
        vocab_id = existing[0]
        status = "updated"
    else:
        cursor.execute("""
            INSERT INTO vocabulary_deck (user_id, word, translation, context_sentence, phonetic, box_number, next_review_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (req.user_id, req.word, req.translation, req.context_sentence, req.pinyin, req.box_number, next_review))
        vocab_id = cursor.lastrowid
        status = "created"
        
    conn.commit()
    conn.close()
    return {
        "status": "success",
        "action": status,
        "vocab_id": vocab_id,
        "user_id": req.user_id,
        "word": req.word,
        "translation": req.translation,
        "context_sentence": req.context_sentence,
        "pinyin": req.pinyin,
        "box_number": req.box_number,
        "next_review_date": next_review
    }

@app.put("/api/vocab/id/{vocab_id}")
def api_update_vocab_by_id(vocab_id: int, req: VocabUpdateRequest):
    """Updates a specific vocabulary card properties by ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE vocabulary_deck 
        SET word = ?, translation = ?, context_sentence = ?, phonetic = ?, box_number = ?, next_review_date = ?
        WHERE vocab_id = ?
    """, (req.word, req.translation, req.context_sentence, req.pinyin, req.box_number, req.next_review_date, vocab_id))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Vocabulary card not found")
    conn.commit()
    conn.close()
    return {"vocab_id": vocab_id, **req.model_dump()}

@app.delete("/api/vocab/id/{vocab_id}")
def api_delete_vocab_by_id(vocab_id: int):
    """Deletes a vocabulary card by ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM vocabulary_deck WHERE vocab_id = ?", (vocab_id,))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Vocabulary card not found")
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Vocabulary card {vocab_id} deleted."}


# Quiz History CRUD Endpoints

@app.get("/api/quiz_history")
def api_get_quiz_history(user_id: int = 2):
    """Retrieves quiz history logs for a user, including media title."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT q.quiz_id, q.user_id, q.content_id, m.title, q.score, q.total_questions, q.notes, q.date_taken
        FROM quiz_history q
        JOIN media_content m ON q.content_id = m.content_id
        WHERE q.user_id = ?
        ORDER BY q.date_taken DESC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "quiz_id": r[0],
            "user_id": r[1],
            "content_id": r[2],
            "media_title": r[3],
            "score": r[4],
            "total_questions": r[5],
            "notes": r[6],
            "date_taken": r[7]
        } for r in rows
    ]

@app.post("/api/quiz_history")
def api_create_quiz_history(req: QuizHistoryCreateRequest):
    """Logs a new quiz result."""
    import datetime
    date_taken = req.date_taken or datetime.datetime.now().isoformat()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO quiz_history (user_id, content_id, score, total_questions, notes, date_taken)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (req.user_id, req.content_id, req.score, req.total_questions, req.notes, date_taken))
    quiz_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {
        "quiz_id": quiz_id,
        "user_id": req.user_id,
        "content_id": req.content_id,
        "score": req.score,
        "total_questions": req.total_questions,
        "notes": req.notes,
        "date_taken": date_taken
    }

@app.put("/api/quiz_history/{quiz_id}")
def api_update_quiz_history(quiz_id: int, req: QuizHistoryUpdateRequest):
    """Updates a quiz history record (e.g. notes)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if req.score is not None and req.total_questions is not None:
        cursor.execute("""
            UPDATE quiz_history SET notes = ?, score = ?, total_questions = ? WHERE quiz_id = ?
        """, (req.notes, req.score, req.total_questions, quiz_id))
    else:
        cursor.execute("""
            UPDATE quiz_history SET notes = ? WHERE quiz_id = ?
        """, (req.notes, quiz_id))
        
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Quiz history record not found")
    conn.commit()
    conn.close()
    return {"quiz_id": quiz_id, "status": "success", "notes": req.notes}

@app.delete("/api/quiz_history/{quiz_id}")
def api_delete_quiz_history(quiz_id: int):
    """Deletes a quiz history record."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM quiz_history WHERE quiz_id = ?", (quiz_id,))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Quiz history record not found")
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Quiz history record {quiz_id} deleted."}


# Serve Frontend Static HTML
@app.get("/dashboard", response_class=HTMLResponse)
def read_index():
    try:
        with open("app/frontend/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Dashboard Frontend File Not Found</h1><p>Ensure the app/frontend/index.html file exists.</p>")

# Mount static files
app.mount("/dashboard-assets", StaticFiles(directory="app/frontend"), name="dashboard-assets")

# Serve the marketing landing page (also published to GitHub Pages) for local one-server demos.
# NOTE: the ADK dev UI reserves "/" (it redirects to /dev-ui), so the landing is mounted at
# /landing. With html=True the page's relative asset paths resolve against the /landing/ base.
app.mount("/landing", StaticFiles(directory="landing", html=True), name="landing")


# Main execution
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
