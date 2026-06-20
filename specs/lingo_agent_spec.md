# Behavior-Driven Development (BDD) Specification: LingoKaraoke & CinemaLingo

This specification details the expected behavior of the language learning agent and the database structure supporting it.

---

## Database Schema (YAML Representation)

The database `lingo_database.db` contains tables for tracking users, learning content (songs and movies), and their personal vocabulary flashcard decks.

```yaml
database_schema:
  tables:
    - name: users
      columns:
        - name: user_id
          type: INTEGER
          constraints: [PRIMARY KEY, AUTOINCREMENT]
        - name: username
          type: TEXT
          constraints: [NOT NULL]
        - name: target_language
          type: TEXT
          constraints: [NOT NULL]
        - name: skill_level
          type: TEXT
          constraints: [NOT NULL]
          description: "e.g., 'beginner', 'intermediate', 'advanced'"

    - name: media_content
      columns:
        - name: content_id
          type: INTEGER
          constraints: [PRIMARY KEY, AUTOINCREMENT]
        - name: title
          type: TEXT
          constraints: [NOT NULL]
        - name: artist_or_movie
          type: TEXT
          constraints: [NOT NULL]
        - name: media_type
          type: TEXT
          constraints: [NOT NULL]
          description: "'song' for Karaoke or 'movie' for Cinema dialogues"
        - name: language
          type: TEXT
          constraints: [NOT NULL]
        - name: difficulty
          type: TEXT
          constraints: [NOT NULL]
        - name: original_text
          type: TEXT
          constraints: [NOT NULL]
          description: "The full lyrics or dialogue script lines, delimited by newlines"
        - name: translated_text
          type: TEXT
          constraints: [NOT NULL]
          description: "The line-by-line translation, matching original_text line-by-line"

    - name: vocabulary_deck
      columns:
        - name: vocab_id
          type: INTEGER
          constraints: [PRIMARY KEY, AUTOINCREMENT]
        - name: user_id
          type: INTEGER
          constraints: [FOREIGN KEY REFERENCES users(user_id)]
        - name: word
          type: TEXT
          constraints: [NOT NULL]
        - name: translation
          type: TEXT
          constraints: [NOT NULL]
          description: "Meaning of the word"
        - name: context_sentence
          type: TEXT
          constraints: [NOT NULL]
          description: "The song or dialogue line where the word was encountered"
        - name: box_number
          type: INTEGER
          constraints: [DEFAULT 1]
          description: "Spaced repetition box number (1 to 5)"
        - name: next_review_date
          type: TEXT
          constraints: [NOT NULL]
          description: "ISO date string for when the word should be reviewed next"
```

---

## Scenarios

### Scenario 1: Learning vocabulary from a Spanish song (LingoKaraoke)
* **Given** the user profile indicates `target_language` is "Spanish" and `skill_level` is "beginner".
* **When** the user says "I want to practice Spanish with the song La Bamba".
* **Then** the agent should query the MCP server to search for "La Bamba".
* **And** retrieve the lyrics:
  ```
  Para bailar la bamba
  Para bailar la bamba se necesita una poca de gracia
  ```
* **And** segment the lines, presenting the first line with its translation:
  * *Original*: "Para bailar la bamba"
  * *Translation*: "To dance the bamba"
* **And** generate a fill-in-the-blank quiz for the key verb:
  * "Fill in the blank: 'Para _______ la bamba' (Meaning: to dance)"
* **And** wait for the user's input.
* **When** the user inputs "bailar",
* **Then** the agent should confirm it is correct.
* **And** automatically call the MCP tool `add_vocabulary_word` to save the word "bailar" to the user's flashcard deck.

### Scenario 2: Practice grammar from a movie scene dialogue (CinemaLingo)
* **Given** the user profile indicates `target_language` is "Spanish".
* **When** the user says "I want to learn using a movie scene".
* **Then** the agent should search the database for movie scenes in Spanish.
* **And** present the scene "Pan's Labyrinth" with the dialogue line:
  * *Original*: "El capitán no es mi padre."
  * *Translation*: "The captain is not my father."
* **And** query the user:
  * "Translate this sentence to English: 'El capitán no es mi padre.'"
* **And** wait for the user's response.
* **When** the user responds with "The captain is not my father",
* **Then** the agent should validate the translation as correct and reward the user.

### Scenario 3: Checking user learning progress
* **Given** the user is logged in.
* **When** the user says "What is in my vocabulary deck?" or "Show my progress".
* **Then** the agent should call the MCP tool `get_user_profile` and list the words currently saved in their `vocabulary_deck` along with their review status.
