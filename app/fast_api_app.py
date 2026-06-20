import os
import sqlite3
import google.auth
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.adk.cli.fast_api import get_fast_api_app
from google.cloud import logging as google_cloud_logging

from app.app_utils.telemetry import setup_telemetry
from app.app_utils.typing import Feedback

setup_telemetry()
_, project_id = google.auth.default()
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
        res = analyze_youtube_video(req.video_id, req.title)
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
    SELECT vocab_id, word, translation, context_sentence, pinyin, box_number, next_review_date 
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


# Main execution
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
