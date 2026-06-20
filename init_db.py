import sqlite3
import os

DB_PATH = "lingo_database.db"

def initialize_database():
    print(f"Initializing database at: {DB_PATH}")
    
    # Remove existing DB if any to start fresh
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        target_language TEXT NOT NULL,
        skill_level TEXT NOT NULL
    )
    """)
    
    # Create media_content table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS media_content (
        content_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        artist_or_movie TEXT NOT NULL,
        media_type TEXT NOT NULL,
        language TEXT NOT NULL,
        difficulty TEXT NOT NULL,
        original_text TEXT NOT NULL,
        translated_text TEXT NOT NULL
    )
    """)
    
    # Create vocabulary_deck table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vocabulary_deck (
        vocab_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        word TEXT NOT NULL,
        translation TEXT NOT NULL,
        context_sentence TEXT NOT NULL,
        box_number INTEGER DEFAULT 1,
        next_review_date TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    """)
    
    # Insert default user
    cursor.execute("""
    INSERT INTO users (user_id, username, target_language, skill_level)
    VALUES (1, 'learner', 'Spanish', 'beginner')
    """)
    
    # Sample content list
    samples = [
        # Song 1: La Bamba
        (
            "La Bamba",
            "Ritchie Valens",
            "song",
            "Spanish",
            "beginner",
            "Para bailar la bamba\nPara bailar la bamba se necesita una poca de gracia\nUna poca de gracia y otra cosita\nAy arriba y arriba\nAy arriba y arriba, por ti seré, por ti seré\nYo no soy marinero\nYo no soy marinero, soy capitán, soy capitán\nBamba, bamba",
            "To dance the bamba\nTo dance the bamba you need a little bit of grace\nA little bit of grace and another little thing\nOh up and up\nOh up and up, for you I will be, for you I will be\nI am not a sailor\nI am not a sailor, I am a captain, I am a captain\nBamba, bamba"
        ),
        # Song 2: De Música Ligera
        (
            "De Música Ligera",
            "Soda Stereo",
            "song",
            "Spanish",
            "intermediate",
            "Ella durmió al calor de las masas\nY yo desperté queriendo soñarla\nAlgún tiempo atrás pensé en escribirle\nY nunca sorteé las trampas del amor\nDe música ligera\nNada nos libra, nada más queda",
            "She slept in the heat of the masses\nAnd I woke up wanting to dream of her\nSome time ago I thought of writing to her\nAnd I never avoided the traps of love\nOf light music\nNothing frees us, nothing else remains"
        ),
        # Movie scene 1: Pan's Labyrinth
        (
            "El Laberinto del Fauno (Pan's Labyrinth)",
            "Guillermo del Toro",
            "movie",
            "Spanish",
            "beginner",
            "El capitán no es mi padre.\nMi padre era sastre. Se perdió en la guerra.",
            "The captain is not my father.\nMy father was a tailor. He was lost in the war."
        ),
        # Movie scene 2: Roma
        (
            "Roma",
            "Alfonso Cuarón",
            "movie",
            "Spanish",
            "intermediate",
            "Estamos solas. No importa lo que te digan, siempre estamos solas.",
            "We are alone. No matter what they tell you, we are always alone."
        )
    ]
    
    cursor.executemany("""
    INSERT INTO media_content (title, artist_or_movie, media_type, language, difficulty, original_text, translated_text)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, samples)
    
    conn.commit()
    conn.close()
    print("Database initialized and seeded successfully.")

if __name__ == "__main__":
    initialize_database()
