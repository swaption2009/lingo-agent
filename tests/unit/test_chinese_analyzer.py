import json
import os
import sqlite3
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from app.chinese_analyzer import (
    DB_PATH,
    analyze_lyrics_with_llm,
    analyze_youtube_video,
    fetch_youtube_transcript,
)

# Schema with the new metadata columns (timestamps live inside the *_text columns).
_NEW_SCHEMA = """
CREATE TABLE media_content (
    content_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    artist_or_movie TEXT NOT NULL,
    media_type TEXT NOT NULL,
    language TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    original_text TEXT NOT NULL,
    translated_text TEXT NOT NULL,
    pinyin_text TEXT,
    video_id TEXT,
    dictionary_json TEXT,
    tutorial TEXT,
    source TEXT
)
"""

# Original schema before the dictionary_json / tutorial / source columns existed.
_LEGACY_SCHEMA = """
CREATE TABLE media_content (
    content_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    artist_or_movie TEXT NOT NULL,
    media_type TEXT NOT NULL,
    language TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    original_text TEXT NOT NULL,
    translated_text TEXT NOT NULL,
    pinyin_text TEXT,
    video_id TEXT
)
"""


def _make_temp_db(monkeypatch, schema: str) -> str:
    """Create an isolated temp DB with the given schema and point the analyzer at it."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.executescript(schema)
    conn.commit()
    conn.close()
    monkeypatch.setattr("app.chinese_analyzer.DB_PATH", path)
    return path


@pytest.fixture
def temp_db(monkeypatch):
    path = _make_temp_db(monkeypatch, _NEW_SCHEMA)
    yield path
    os.remove(path)


@pytest.fixture
def temp_db_legacy(monkeypatch):
    path = _make_temp_db(monkeypatch, _LEGACY_SCHEMA)
    yield path
    os.remove(path)


@pytest.fixture(scope="module", autouse=True)
def init_test_db():
    # Make sure database is seeded before running tests
    if not os.path.exists(DB_PATH):
        import init_db

        init_db.initialize_database()
    yield


def test_fetch_youtube_transcript_error():
    # Verify that an invalid video ID returns an empty list and handles exceptions gracefully
    res = fetch_youtube_transcript("invalid_id_123")
    assert isinstance(res, list)
    assert len(res) == 0


@patch("app.chinese_analyzer.client.models.generate_content")
def test_analyze_lyrics_with_llm(mock_generate_content):
    # Mock Gemini response
    mock_response = MagicMock()
    mock_response.text = """
    {
      "lines": [
        {
          "text": "[10.0]甜蜜蜜 你笑得甜蜜蜜",
          "pinyin": "[10.0]tián mì mì, nǐ xiào de tián mì mì",
          "translation": "[10.0]Sweetly, you smile so sweetly"
        }
      ],
      "dictionary": [
        {
          "word": "甜蜜蜜",
          "pinyin": "tiánmìmì",
          "translation": "sweetly",
          "explanation": "To describe something very sweet"
        }
      ],
      "tutorial": "A classic beginner Chinese song."
    }
    """
    mock_generate_content.return_value = mock_response

    res = analyze_lyrics_with_llm("甜蜜蜜...", "Tian Mi Mi")
    assert "lines" in res
    assert len(res["lines"]) == 1
    assert res["lines"][0]["text"] == "[10.0]甜蜜蜜 你笑得甜蜜蜜"
    assert len(res["dictionary"]) == 1
    assert res["dictionary"][0]["word"] == "甜蜜蜜"
    assert "tutorial" in res
    assert res["tutorial"] == "A classic beginner Chinese song."


@patch("app.chinese_analyzer.fetch_youtube_transcript")
@patch("app.chinese_analyzer.client.models.generate_content")
def test_analyze_youtube_video_uncached(mock_generate_content, mock_fetch):
    # Mock raw YouTube transcript
    mock_fetch.return_value = [{"text": "甜蜜蜜", "start": 10.0, "duration": 4.0}]

    # Mock Gemini response
    mock_response = MagicMock()
    mock_response.text = """
    {
      "lines": [
        {
          "text": "[10.0]甜蜜蜜",
          "pinyin": "[10.0]tián mì mì",
          "translation": "[10.0]Sweetly"
        }
      ],
      "dictionary": [
        {
          "word": "甜蜜蜜",
          "pinyin": "tiánmìmì",
          "translation": "sweetly",
          "explanation": "sweet"
        }
      ],
      "tutorial": "Tutorial test."
    }
    """
    mock_generate_content.return_value = mock_response

    # Ensure it's not in the DB first
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM media_content WHERE video_id = 'test_video_123'")
    conn.commit()
    conn.close()

    # Call analysis (triggers uncached route)
    res = analyze_youtube_video("test_video_123", "Test Song Title")

    assert res["title"] == "Test Song Title"
    assert len(res["lines"]) == 1
    assert res["lines"][0]["text"] == "[10.0]甜蜜蜜"
    assert res["dictionary"][0]["word"] == "甜蜜蜜"

    # Verify cached entry is now in DB
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT content_id FROM media_content WHERE video_id = 'test_video_123'"
    )
    row = cursor.fetchone()
    conn.close()
    assert row is not None


# --- Bug fix: transcription accuracy & caching ---


@patch("app.chinese_analyzer.fetch_youtube_transcript")
@patch("app.chinese_analyzer.client.models.generate_content")
def test_uncached_preserves_transcript_timestamps_and_sets_source(
    mock_generate, mock_fetch, temp_db
):
    """The real transcript timestamps must reach the LLM so karaoke can sync,
    and a captioned video must be labelled source='captions'."""
    mock_fetch.return_value = [
        {"text": "甜蜜蜜", "start": 10.0, "duration": 4.0},
        {"text": "你笑得甜蜜蜜", "start": 18.0, "duration": 5.0},
    ]
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(
        {
            "lines": [
                {
                    "text": "[10.0]甜蜜蜜",
                    "pinyin": "[10.0]tián mì mì",
                    "translation": "[10.0]Sweet",
                }
            ],
            "dictionary": [
                {
                    "word": "甜蜜蜜",
                    "pinyin": "tiánmìmì",
                    "translation": "sweet",
                    "explanation": "x",
                }
            ],
            "tutorial": "t",
        }
    )
    mock_generate.return_value = mock_resp

    res = analyze_youtube_video("vid_ts_1", "Tian Mi Mi")

    prompt = mock_generate.call_args.kwargs["contents"]
    assert "[10.0]甜蜜蜜" in prompt
    assert "[18.0]你笑得甜蜜蜜" in prompt
    assert res["source"] == "captions"


def test_cache_hit_preserves_timestamps_and_skips_llm(temp_db):
    """A cached song must return its stored, timestamped lines and stored
    dictionary/tutorial WITHOUT re-running the (slow, non-deterministic) LLM."""
    conn = sqlite3.connect(temp_db)
    conn.execute(
        """
        INSERT INTO media_content
            (title, artist_or_movie, media_type, language, difficulty,
             original_text, translated_text, pinyin_text, video_id,
             dictionary_json, tutorial, source)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            "甜蜜蜜",
            "Teresa Teng",
            "song",
            "Chinese",
            "beginner",
            "[10.0]甜蜜蜜\n[18.0]好像花儿开在春风里",
            "[10.0]Sweet\n[18.0]Like flowers blooming",
            "[10.0]tián mì mì\n[18.0]hǎo xiàng huā er",
            "vid_cache_1",
            json.dumps(
                [
                    {
                        "word": "甜蜜蜜",
                        "pinyin": "tiánmìmì",
                        "translation": "sweet",
                        "explanation": "x",
                    }
                ]
            ),
            "Cached tutorial.",
            "captions",
        ),
    )
    conn.commit()
    conn.close()

    with patch("app.chinese_analyzer.client.models.generate_content") as mock_gen:
        res = analyze_youtube_video("vid_cache_1", "甜蜜蜜")
        mock_gen.assert_not_called()

    assert res["lines"][0]["text"] == "[10.0]甜蜜蜜"
    assert res["lines"][0]["pinyin"] == "[10.0]tián mì mì"
    assert res["lines"][1]["text"] == "[18.0]好像花儿开在春风里"
    assert res["dictionary"][0]["word"] == "甜蜜蜜"
    assert res["tutorial"] == "Cached tutorial."
    assert res["source"] == "captions"


@patch("app.chinese_analyzer.fetch_lyrics_via_web_search")
@patch("app.chinese_analyzer.fetch_youtube_transcript")
@patch("app.chinese_analyzer.client.models.generate_content")
def test_no_transcript_falls_back_to_web_search(
    mock_gen, mock_fetch, mock_web, temp_db
):
    """When a video has no captions, fetch the real lyrics from the web
    (not hallucinated) and label the result source='web_search'."""
    mock_fetch.return_value = []
    mock_web.return_value = "像鱼儿\n在如梦的深海里畅游"
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(
        {
            "lines": [
                {
                    "text": "像鱼儿",
                    "pinyin": "xiàng yú ér",
                    "translation": "Like a fish",
                }
            ],
            "dictionary": [],
            "tutorial": "t",
        }
    )
    mock_gen.return_value = mock_resp

    res = analyze_youtube_video("vid_nocap_1", "像鱼 Wang Er Lang")

    mock_web.assert_called_once()
    assert "像鱼" in mock_web.call_args.args[0]
    assert res["source"] == "web_search"
    assert res["lines"][0]["text"] == "像鱼儿"


@patch("app.chinese_analyzer.client.models.generate_content")
def test_fetch_lyrics_via_web_search_uses_google_search_tool(mock_gen):
    """The web-search helper must enable the Google Search grounding tool so it
    retrieves real lyrics instead of inventing them."""
    from app.chinese_analyzer import fetch_lyrics_via_web_search

    mock_resp = MagicMock()
    mock_resp.text = "像鱼儿\n在如梦的深海里畅游"
    mock_gen.return_value = mock_resp

    out = fetch_lyrics_via_web_search("像鱼 Wang Er Lang")

    assert out == "像鱼儿\n在如梦的深海里畅游"
    config = mock_gen.call_args.kwargs["config"]
    assert getattr(config, "tools", None), (
        "Expected a google_search grounding tool to be configured"
    )


def test_ensure_schema_adds_missing_columns(temp_db_legacy):
    """Existing databases created before this change must be migrated in place."""
    from app.chinese_analyzer import _ensure_schema

    conn = sqlite3.connect(temp_db_legacy)
    _ensure_schema(conn)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(media_content)").fetchall()]
    conn.close()

    assert "dictionary_json" in cols
    assert "tutorial" in cols
    assert "source" in cols
