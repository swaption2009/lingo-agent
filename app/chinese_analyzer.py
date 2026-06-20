import json
import sqlite3

from google import genai
from google.genai import types
from youtube_transcript_api import YouTubeTranscriptApi

DB_PATH = "lingo_database.db"

# Initialize Google GenAI client (uses Vertex AI if GOOGLE_GENAI_USE_VERTEXAI is True)
client = genai.Client()

# Columns added after the first release. Older databases are migrated in place so
# they keep working without re-running init_db (which would wipe cached analyses).
_EXTRA_COLUMNS = {
    "dictionary_json": "TEXT",  # cached vocabulary so we never re-run the LLM on a hit
    "tutorial": "TEXT",  # cached grammar tutorial
    "source": "TEXT",  # provenance of the lyrics: 'captions' or 'web_search'
}


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Idempotently add columns introduced after the first release.

    Using ALTER TABLE keeps existing cached rows intact; CREATE TABLE in init_db
    only covers fresh databases, so live databases need this in-place migration.
    """
    existing = {row[1] for row in conn.execute("PRAGMA table_info(media_content)")}
    for column, col_type in _EXTRA_COLUMNS.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE media_content ADD COLUMN {column} {col_type}")
    conn.commit()


def _rows_to_lines(
    original_text: str, pinyin_text: str, translated_text: str
) -> list[dict]:
    """Zip the stored newline-delimited columns back into per-line dicts.

    Crucially this preserves any leading ``[seconds]`` timestamp on each line so a
    cached song still syncs to the video (the previous code discarded them).
    """
    orig_lines = original_text.split("\n")
    trans_lines = translated_text.split("\n")
    pinyin_lines = pinyin_text.split("\n") if pinyin_text else []
    lines = []
    for i, text in enumerate(orig_lines):
        lines.append(
            {
                "text": text,
                "pinyin": pinyin_lines[i] if i < len(pinyin_lines) else "",
                "translation": trans_lines[i] if i < len(trans_lines) else "",
            }
        )
    return lines


def fetch_youtube_transcript(video_id: str) -> list[dict]:
    """Fetches the transcript for a given YouTube video ID.
    Returns a list of dicts with 'text', 'start', and 'duration' keys.
    """
    try:
        # Try Chinese and English transcripts
        transcript = YouTubeTranscriptApi().fetch(
            video_id, languages=["zh-CN", "zh-TW", "zh", "en"]
        )
        return [
            {"text": snippet.text, "start": snippet.start, "duration": snippet.duration}
            for snippet in transcript
        ]
    except Exception as e:
        print(f"Error fetching YouTube transcript for {video_id}: {e}")
        return []


def analyze_lyrics_with_llm(transcript_text: str, title: str = "") -> dict:
    """Uses Gemini to clean the raw transcript, segment into verses/lines,
    generate Hanyu Pinyin with tone marks, translate to English,
    extract key vocabulary, and generate a summary tutorial.
    """
    prompt = f"""
You are a professional Chinese language teacher.
Analyze the following YouTube video transcript (Title: '{title}').
Perform the following tasks:
1. Correct any transcription errors in the raw Chinese text.
2. Segment the text into clean, sequential line-by-line sentences/verses.
3. For each line, generate the Hanyu Pinyin with correct tone marks.
4. For each line, translate it into natural English.
5. Identify the top 5-10 key vocabulary words or phrases in the text. For each word, provide the Hanzi, the Hanyu Pinyin with tone marks, the English translation, and a brief contextual explanation of how it is used.
6. Write a short, encouraging tutorial/grammar guide (1-2 paragraphs) explaining the key grammatical patterns, particle usage, or cultural context of the text.

TIMESTAMPS: Some raw lines begin with a timestamp in square brackets, e.g. "[12.3]歌词". When a line has one, you MUST keep that exact timestamp prefix at the start of the matching "text", "pinyin", and "translation" values (for example "[12.3]..."). If you merge several timestamped lines into one, use the earliest timestamp; if you split one line, repeat its timestamp on each piece. Never invent a timestamp for a line that has none, and never reorder lines.

You MUST respond with a valid JSON object matching this schema:
{{
  "lines": [
    {{
      "text": "original Chinese characters line",
      "pinyin": "hanyu pinyin line with tone marks",
      "translation": "English translation line"
    }}
  ],
  "dictionary": [
    {{
      "word": "Chinese word/phrase",
      "pinyin": "hanyu pinyin with tone marks",
      "translation": "English translation",
      "explanation": "Brief explanation of meaning and usage"
    }}
  ],
  "tutorial": "Grammar tutorial explaining key language constructs in the song/video."
}}

Raw Transcript Text:
{transcript_text}
"""

    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json", temperature=0.2
        ),
    )

    try:
        data = json.loads(response.text)
        return data
    except Exception as e:
        print(f"Error parsing Gemini JSON response: {e}")
        # Return fallback structure
        return {
            "lines": [{"text": transcript_text, "pinyin": "", "translation": ""}],
            "dictionary": [],
            "tutorial": "Could not generate analysis tutorial.",
        }


def fetch_lyrics_via_web_search(title: str) -> str:
    """Retrieve the real lyrics/script for a video from the web.

    Uses Gemini with the Google Search grounding tool so the text is actually
    sourced from the internet rather than hallucinated from the title. Grounding
    cannot be combined with forced-JSON output, so this returns plain text that is
    then structured by ``analyze_lyrics_with_llm`` in a separate call.

    Returns the raw lyrics text, or an empty string if nothing could be found.
    """
    prompt = (
        f"Find the original, verbatim lyrics (or script) for the song/video titled "
        f"'{title}'. Search the web to confirm the authentic text. If it is a Chinese "
        f"song, return the Chinese lyrics. Output ONLY the lyrics themselves, one line "
        f"per line, with no commentary, headings, romanization, or translation."
    )
    try:
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.1,
            ),
        )
        return (response.text or "").strip()
    except Exception as e:
        print(f"Error fetching lyrics via web search for '{title}': {e}")
        return ""


def analyze_youtube_video(video_id: str, title: str = "") -> dict:
    """Main orchestrator to analyze a YouTube video.
    Checks database cache first, then fetches and analyzes if missing.
    """
    conn = sqlite3.connect(DB_PATH)
    _ensure_schema(conn)
    cursor = conn.cursor()

    # 1. Check database cache (keyed by the YouTube video id)
    cursor.execute(
        """
    SELECT content_id, title, artist_or_movie, original_text, translated_text,
           pinyin_text, dictionary_json, tutorial, source
    FROM media_content WHERE video_id = ?
    """,
        (video_id,),
    )
    row = cursor.fetchone()

    if row:
        (
            content_id,
            db_title,
            artist,
            original_text,
            translated_text,
            pinyin_text,
            dictionary_json,
            tutorial,
            source,
        ) = row

        # Rebuild lines straight from the cache, preserving [timestamp] prefixes.
        lines = _rows_to_lines(original_text, pinyin_text, translated_text)
        dictionary = json.loads(dictionary_json) if dictionary_json else []

        # Backfill dictionary/tutorial for rows cached before these columns existed,
        # so subsequent hits are a pure DB read with no LLM call at all.
        if not dictionary or not tutorial:
            analysis = analyze_lyrics_with_llm(original_text, title=db_title)
            dictionary = analysis.get("dictionary", [])
            tutorial = analysis.get("tutorial", "")
            cursor.execute(
                "UPDATE media_content SET dictionary_json = ?, tutorial = ? WHERE content_id = ?",
                (json.dumps(dictionary, ensure_ascii=False), tutorial, content_id),
            )
            conn.commit()

        conn.close()
        return {
            "content_id": content_id,
            "title": db_title,
            "artist_or_movie": artist,
            "lines": lines,
            "dictionary": dictionary,
            "tutorial": tutorial or "Here is your saved tutorial for this song.",
            "source": source or "captions",
        }

    # 2. Fetch transcript. Real captions are preferred because they carry the
    #    per-line timing that drives karaoke highlighting.
    transcript_segments = fetch_youtube_transcript(video_id)

    if transcript_segments:
        # Prefix each line with its start time so the analysis keeps the timing.
        lyrics_text = "\n".join(
            f"[{seg['start']:.1f}]{seg['text']}" for seg in transcript_segments
        )
        source = "captions"
    else:
        # No captions (common for movie trailers with burned-in subtitles): fetch
        # the REAL lyrics from the web via grounded search instead of inventing them.
        if not title:
            conn.close()
            return {
                "error": "No transcript available and no video title provided for web search."
            }

        lyrics_text = fetch_lyrics_via_web_search(title)
        source = "web_search"
        if not lyrics_text:
            conn.close()
            return {
                "error": "No captions found and the lyrics could not be located on the web for this video."
            }

    # 3. Analyze with Gemini
    analysis = analyze_lyrics_with_llm(
        lyrics_text, title=title or "Unknown YouTube Video"
    )

    # Format texts for DB storage
    original_text = "\n".join(line["text"] for line in analysis["lines"])
    translated_text = "\n".join(line["translation"] for line in analysis["lines"])
    pinyin_text = "\n".join(line["pinyin"] for line in analysis["lines"])
    dictionary = analysis.get("dictionary", [])
    tutorial = analysis.get("tutorial", "")

    # Save to media_content database (including cached dictionary/tutorial/source)
    cursor.execute(
        """
    INSERT INTO media_content
        (title, artist_or_movie, media_type, language, difficulty,
         original_text, translated_text, pinyin_text, video_id,
         dictionary_json, tutorial, source)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            title or "YouTube Video",
            "YouTube",
            "song",
            "Chinese",
            "intermediate",
            original_text,
            translated_text,
            pinyin_text,
            video_id,
            json.dumps(dictionary, ensure_ascii=False),
            tutorial,
            source,
        ),
    )

    content_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "content_id": content_id,
        "title": title or "YouTube Video",
        "artist_or_movie": "YouTube",
        "lines": analysis["lines"],
        "dictionary": dictionary,
        "tutorial": tutorial,
        "source": source,
    }
