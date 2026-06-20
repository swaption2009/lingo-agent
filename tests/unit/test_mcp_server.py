import pytest
import sqlite3
import os
import datetime
from mcp_server import (
    get_user_profile,
    search_learning_media,
    get_media_content,
    add_vocabulary_word,
    get_vocab_deck,
    DB_PATH
)

# Use the active database initialized by init_db.py for testing
@pytest.fixture(scope="module", autouse=True)
def setup_db():
    # Verify DB exists
    if not os.path.exists(DB_PATH):
        # Initialize if missing
        import init_db
        init_db.initialize_database()
    yield

def test_get_user_profile():
    profile = get_user_profile(1)
    assert "user_id" in profile
    assert profile["username"] == "learner"
    assert profile["target_language"] == "Spanish"
    assert profile["skill_level"] == "beginner"

def test_search_learning_media():
    search_res = search_learning_media("Bamba", "Spanish")
    assert "results" in search_res
    results = search_res["results"]
    assert len(results) >= 1
    assert any(r["title"] == "La Bamba" for r in results)
    assert any(r["artist_or_movie"] == "Ritchie Valens" for r in results)

def test_get_media_content():
    # Find La Bamba content_id
    search_res = search_learning_media("Bamba", "Spanish")
    content_id = search_res["results"][0]["content_id"]
    
    content = get_media_content(content_id)
    assert "title" in content
    assert content["title"] == "La Bamba"
    assert "original_text" in content
    assert "Para bailar la bamba" in content["original_text"]
    assert "translated_text" in content
    assert "To dance the bamba" in content["translated_text"]

def test_add_and_get_vocabulary():
    # Fresh connection to delete existing "bailar" for testing if any
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM vocabulary_deck WHERE user_id = 1 AND word = 'bailar'")
    conn.commit()
    conn.close()
    
    # Add word
    add_res = add_vocabulary_word("bailar", "to dance", "Para bailar la bamba", 1)
    assert add_res["status"] == "success"
    
    # Verify in deck
    deck_res = get_vocab_deck(1)
    assert "deck" in deck_res
    deck = deck_res["deck"]
    assert any(d["word"] == "bailar" and d["translation"] == "to dance" for d in deck)
    
    # Add duplicate should return already exists
    dup_res = add_vocabulary_word("bailar", "to dance", "Para bailar la bamba", 1)
    assert dup_res["status"] == "already_exists"

def test_delete_and_reset_vocabulary():
    # Ensure word exists
    add_vocabulary_word("bailar", "to dance", "Para bailar la bamba", 1)
    
    # Delete word
    from mcp_server import delete_vocabulary_word, reset_vocab_deck
    del_res = delete_vocabulary_word("bailar", 1)
    assert del_res["status"] == "success"
    
    # Verify not in deck
    deck_res = get_vocab_deck(1)
    deck = deck_res["deck"]
    assert not any(d["word"] == "bailar" for d in deck)
    
    # Add another word and reset deck
    add_vocabulary_word("bailar", "to dance", "Para bailar la bamba", 1)
    reset_res = reset_vocab_deck(1)
    assert reset_res["status"] == "success"
    
    # Verify deck is empty
    deck_res = get_vocab_deck(1)
    assert len(deck_res["deck"]) == 0

