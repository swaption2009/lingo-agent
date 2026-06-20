import pytest
import sqlite3
import os
from unittest.mock import MagicMock, patch

from app.chinese_analyzer import (
    fetch_youtube_transcript,
    analyze_lyrics_with_llm,
    analyze_youtube_video,
    DB_PATH
)

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

@patch('app.chinese_analyzer.client.models.generate_content')
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

@patch('app.chinese_analyzer.fetch_youtube_transcript')
@patch('app.chinese_analyzer.client.models.generate_content')
def test_analyze_youtube_video_uncached(mock_generate_content, mock_fetch):
    # Mock raw YouTube transcript
    mock_fetch.return_value = [
        {"text": "甜蜜蜜", "start": 10.0, "duration": 4.0}
    ]
    
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
    cursor.execute("SELECT content_id FROM media_content WHERE video_id = 'test_video_123'")
    row = cursor.fetchone()
    conn.close()
    assert row is not None
