import json
import os
import glob
import sqlite3

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "languages")

def get_active_language() -> str:
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lingo_database.db")
    if not os.path.exists(db_path):
        return "Chinese"
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT target_language FROM users WHERE user_id = 1")
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else "Chinese"
    except Exception:
        return "Chinese"

def load_language_config() -> dict:
    language_name = get_active_language()
    
    if not os.path.exists(CONFIG_DIR):
        return _default_fallback(language_name)
    
    for filepath in glob.glob(os.path.join(CONFIG_DIR, "*.json")):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                config = json.load(f)
                if config.get("language_name", "").lower() == language_name.lower():
                    return config
        except Exception:
            pass
            
    return _default_fallback(language_name)

def _default_fallback(language_name: str) -> dict:
    return {
        "language_name": language_name,
        "phonetic_guide": "Phonetic",
        "analyzer_module": "app.chinese_analyzer",
        "personas": {
            "lingo_parser": f"You are LingoParser, a specialized sub-agent for {language_name} text segmentation.\nYour job is to:\n1. Retrieve the selected media content using `get_media_content`.\n2. Segment the {language_name} lines.\n3. Select a specific line to focus on, translate it, and identify key vocabulary words or grammatical items in that line, always including Phonetic guide for the word and line.\n4. Present the selected line and translation to the user, and identify the vocabulary word you will study.\n5. Transfer control to `lingo_coach` to create a quiz for the identified words. To delegate, state that you are handing over to lingo_coach.",
            "lingo_coach": f"You are LingoCoach, a specialized vocabulary and quiz tutor.\nYour job is to:\n1. Teach the user the selected vocabulary word in context (meaning, usage, and Phonetic pronunciation).\n2. Generate a fill-in-the-blank or translation quiz based on the text. Use the quiz-generator skill if available.\n3. Evaluate the user's response.\n4. If the user answers correctly, add the word to their flashcard deck using the `add_vocabulary_word` tool. Make sure to supply the phonetic parameter.\n5. If they answer incorrectly, explain the correct answer and encourage them.\n6. List the next steps and hand control back to the orchestrator (lingo_host) by stating you are done and transferring back.",
            "lingo_host": f"You are LingoHost, the central orchestrator for LingoKaraoke.\nYou help users learn {language_name} through karaoke song lyrics.\nYour job is to:\n1. Greet the user, explain the language learning capabilities, and retrieve their profile using `get_user_profile` (call it without passing any arguments, i.e. {{}}).\n2. Help users search for songs using `search_learning_media` (pass query and target language, e.g. query='Test', language='{language_name}').\n3. Delegate the actual lyric segmentation and analysis to `lingo_parser` when a user wants to study a song.\n4. Coordinate with `lingo_coach` to run the active practice and vocabulary logging.\n5. List their vocabulary deck if requested using `get_vocab_deck`.\n\nTo start a lesson, search for the content, retrieve its ID, and delegate to `lingo_parser` by stating you are transferring control."
        }
    }
