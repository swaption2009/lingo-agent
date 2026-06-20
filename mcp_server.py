import sqlite3
import datetime
import os
from fastmcp import FastMCP

# Define MCP server named LingoMCP
mcp = FastMCP("LingoMCP")
DB_PATH = "lingo_database.db"

@mcp.tool()
def get_user_profile(user_id: int = 1) -> dict:
    """Retrieves user profile information including target language and skill level.
    
    Args:
        user_id: The ID of the user. Defaults to 1.
    """
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
    return {"error": "User not found"}

@mcp.tool()
def search_learning_media(query: str, language: str = "Spanish") -> dict:
    """Searches for songs or movies available in the database for learning.
    
    Args:
        query: The search query (e.g., song title, artist, or movie name).
        language: The target language. Defaults to 'Spanish'.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT content_id, title, artist_or_movie, media_type, difficulty 
    FROM media_content 
    WHERE language = ? AND (title LIKE ? OR artist_or_movie LIKE ?)
    """, (language, f"%{query}%", f"%{query}%"))
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        results.append({
            "content_id": r[0],
            "title": r[1],
            "artist_or_movie": r[2],
            "media_type": r[3],
            "difficulty": r[4]
        })
    return {"results": results}

@mcp.tool()
def get_media_content(content_id: int) -> dict:
    """Retrieves the full content lines and line-by-line translations for a specific song or movie.
    
    Args:
        content_id: The unique ID of the media content.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT content_id, title, artist_or_movie, media_type, original_text, translated_text 
    FROM media_content WHERE content_id = ?
    """, (content_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "content_id": row[0],
            "title": row[1],
            "artist_or_movie": row[2],
            "media_type": row[3],
            "original_text": row[4],
            "translated_text": row[5]
        }
    return {"error": "Content not found"}

@mcp.tool()
def add_vocabulary_word(word: str, translation: str, context: str, user_id: int = 1) -> dict:
    """Adds a newly learned word or phrase to the user's flashcard deck for spaced repetition.
    
    Args:
        word: The foreign word or phrase learned.
        translation: The native language translation.
        context: The line or sentence where the word was encountered.
        user_id: The ID of the user. Defaults to 1.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Calculate next review date (tomorrow)
    next_review = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    
    # Check if word already exists in deck for this user
    cursor.execute("SELECT vocab_id FROM vocabulary_deck WHERE user_id = ? AND word = ?", (user_id, word))
    existing = cursor.fetchone()
    
    if existing:
        conn.close()
        return {"status": "already_exists", "message": f"'{word}' is already in your vocabulary deck."}
        
    cursor.execute("""
    INSERT INTO vocabulary_deck (user_id, word, translation, context_sentence, box_number, next_review_date)
    VALUES (?, ?, ?, ?, 1, ?)
    """, (user_id, word, translation, context, next_review))
    conn.commit()
    conn.close()
    return {
        "status": "success", 
        "message": f"Added '{word}' to your flashcard deck.",
        "word": word,
        "translation": translation,
        "next_review_date": next_review
    }

@mcp.tool()
def get_vocab_deck(user_id: int = 1) -> dict:
    """Retrieves the list of flashcards currently saved in the user's vocabulary deck.
    
    Args:
        user_id: The ID of the user. Defaults to 1.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT vocab_id, word, translation, context_sentence, box_number, next_review_date 
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
            "box_number": r[4],
            "next_review_date": r[5]
        })
    return {"deck": deck}

@mcp.tool()
def delete_vocabulary_word(word: str, user_id: int = 1) -> dict:
    """Deletes a specific word from the user's vocabulary deck.
    
    Args:
        word: The foreign word to delete.
        user_id: The ID of the user. Defaults to 1.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM vocabulary_deck WHERE user_id = ? AND word = ?", (user_id, word))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Deleted '{word}' from your vocabulary deck."}

@mcp.tool()
def reset_vocab_deck(user_id: int = 1) -> dict:
    """Resets (clears) all vocabulary words in the user's deck.
    
    Args:
        user_id: The ID of the user. Defaults to 1.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM vocabulary_deck WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "All vocabulary words cleared."}

if __name__ == "__main__":
    mcp.run()
