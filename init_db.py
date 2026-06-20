import os
import sqlite3

DB_PATH = "lingo_database.db"


def initialize_database():
    print(f"Initializing database at: {DB_PATH}")

    # Remove existing DB if any to start fresh
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except Exception as e:
            print(f"Warning: could not remove database file: {e}")

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

    # Create media_content table with pinyin_text and video_id support.
    # dictionary_json / tutorial / source cache the full analysis so that a repeat
    # view of the same video is a pure DB read (no LLM call) and keeps its timing.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS media_content (
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
    """)

    # Create vocabulary_deck table with pinyin support
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vocabulary_deck (
        vocab_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        word TEXT NOT NULL,
        translation TEXT NOT NULL,
        context_sentence TEXT NOT NULL,
        pinyin TEXT,
        box_number INTEGER DEFAULT 1,
        next_review_date TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    """)

    # Create quiz_history table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quiz_history (
        quiz_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        content_id INTEGER NOT NULL,
        score INTEGER NOT NULL,
        total_questions INTEGER NOT NULL,
        notes TEXT,
        date_taken TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(user_id),
        FOREIGN KEY(content_id) REFERENCES media_content(content_id)
    )
    """)

    # Insert default users
    # We will seed two users: user 1 is our Spanish learner (for backwards compatibility/existing tests),
    # and user 2 is a Chinese learner.
    cursor.execute("""
    INSERT INTO users (user_id, username, target_language, skill_level)
    VALUES (1, 'learner', 'Spanish', 'beginner')
    """)

    cursor.execute("""
    INSERT INTO users (user_id, username, target_language, skill_level)
    VALUES (2, 'chinese_learner', 'Chinese', 'beginner')
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
            "To dance the bamba\nTo dance the bamba you need a little bit of grace\nA little bit of grace and another little thing\nOh up and up\nOh up and up, for you I will be, for you I will be\nI am not a sailor\nI am not a sailor, I am a captain, I am a captain\nBamba, bamba",
            None,
            None,
        ),
        # Song 2: De Música Ligera
        (
            "De Música Ligera",
            "Soda Stereo",
            "song",
            "Spanish",
            "intermediate",
            "Ella durmió al calor de las masas\nY yo desperté queriendo soñarla\nAlgún tiempo atrás pensé en escribirle\nY nunca sorteé las trampas del amor\nDe música ligera\nNada nos libra, nada más queda",
            "She slept in the heat of the masses\nAnd I woke up wanting to dream of her\nSome time ago I thought of writing to her\nAnd I never avoided the traps of love\nOf light music\nNothing frees us, nothing else remains",
            None,
            None,
        ),
        # Movie scene 1: Pan's Labyrinth
        (
            "El Laberinto del Fauno (Pan's Labyrinth)",
            "Guillermo del Toro",
            "movie",
            "Spanish",
            "beginner",
            "El capitán no es mi padre.\nMi padre era sastre. Se perdió en la guerra.",
            "The captain is not my father.\nMi father was a tailor. He was lost in the war.",
            None,
            None,
        ),
        # Movie scene 2: Roma
        (
            "Roma",
            "Alfonso Cuarón",
            "movie",
            "Spanish",
            "intermediate",
            "Estamos solas. No importa lo que te digan, siempre estamos solas.",
            "We are alone. No matter what they tell you, we are always alone.",
            None,
            None,
        ),
        # Chinese Song 1: 甜蜜蜜 (Tian Mi Mi)
        (
            "甜蜜蜜 (Tian Mi Mi)",
            "Teresa Teng",
            "song",
            "Chinese",
            "beginner",
            "[10.0]甜蜜蜜 你笑得甜蜜蜜\n[18.0]好像花儿开在春风里\n[23.0]开在春风里\n[28.0]在哪里 在哪里见过你\n[37.0]你的笑容这样熟悉\n[42.0]我一时想不起\n[48.0]啊 在梦里",
            "[10.0]Sweetly, you smile so sweetly\n[18.0]As if flowers blooming in the spring breeze\n[23.0]Blooming in the spring breeze\n[28.0]Where, oh where have I seen you?\n[37.0]Your smile is so familiar\n[42.0]I cannot remember for the moment\n[48.0]Ah, in my dreams",
            "[10.0]tián mì mì, nǐ xiào de tián mì mì\n[18.0]hǎo xiàng huā er kāi zài chūn fēng lǐ\n[23.0]kāi zài chūn fēng lǐ\n[28.0]zài nǎ lǐ, zài nǎ lǐ jiàn guò nǐ\n[37.0]nǐ de xiào róng zhè yàng shú xī\n[42.0]wǒ yī shí xiǎng bù qǐ\n[48.0]ā, zài mèng lǐ",
            "Y3v7XW4sKk8",
        ),
        # Chinese Song 2: 童话 (Tong Hua)
        (
            "童话 (Tong Hua)",
            "Michael Wong",
            "song",
            "Chinese",
            "intermediate",
            "[9.0]忘了有多久 再没听到你\n[16.0]对我说你最爱的故事\n[23.0]我想了很久 我开始慌了\n[30.0]是不是我又做错了什么\n[36.0]你哭着对我说 童话里都是骗人的\n[45.0]我不可能是你的王子\n[52.0]也许你不会懂 从你说爱我以后\n[59.0]我的天空 星星都亮了",
            "[9.0]Forgotten how long it's been since I last heard you\n[16.0]Tell me your favorite story\n[23.0]I thought for a long time, I started to panic\n[30.0]Did I do something wrong again?\n[36.0]You cried and told me that fairy tales are all lies\n[45.0]I could never be your prince\n[52.0]Perhaps you wouldn't understand, ever since you said you loved me\n[59.0]In my sky, the stars have all lit up",
            "[9.0]wàng le yǒu duō jiǔ, zài méi tīng dào nǐ\n[16.0]duì wǒ shuō nǐ zuì ài de gù shì\n[23.0]wǒ xiǎng le hěn jiǔ, wǒ kāi shǐ huāng le\n[30.0]shì bú shì wǒ yòu zuò cuò le shén me\n[36.0]nǐ kū zhe duì wǒ shuō, tóng huà lǐ dōu shì piàn rén de\n[45.0]wǒ bù kě néng shì nǐ de wáng zǐ\n[52.0]yě xǔ nǐ bú huì dǒng, cóng nǐ shuō ài wǒ yǐ hòu\n[59.0]wǒ de tiān kōng, xīng xīng dōu liàng le",
            "a8SshSgY5H4",
        ),
    ]

    cursor.executemany(
        """
    INSERT INTO media_content (title, artist_or_movie, media_type, language, difficulty, original_text, translated_text, pinyin_text, video_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        samples,
    )

    # Insert default quiz histories
    quiz_samples = [
        (1, 1, 3, 3, "Perfect score! Verb conjugation was easy.", "2026-06-20T12:00:00Z"),
        (2, 5, 2, 3, "Needs more study on pinyin tones", "2026-06-20T15:30:00Z")
    ]
    cursor.executemany(
        """
    INSERT INTO quiz_history (user_id, content_id, score, total_questions, notes, date_taken)
    VALUES (?, ?, ?, ?, ?, ?)
    """,
        quiz_samples,
    )

    conn.commit()
    conn.close()
    print("Database initialized and seeded successfully.")


if __name__ == "__main__":
    initialize_database()
