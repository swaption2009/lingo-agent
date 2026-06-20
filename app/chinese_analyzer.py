import sqlite3
import json
import os
from google import genai
from google.genai import types
from youtube_transcript_api import YouTubeTranscriptApi

DB_PATH = "lingo_database.db"

# Initialize Google GenAI client (uses Vertex AI if GOOGLE_GENAI_USE_VERTEXAI is True)
client = genai.Client()

def fetch_youtube_transcript(video_id: str) -> list[dict]:
    """Fetches the transcript for a given YouTube video ID.
    Returns a list of dicts with 'text', 'start', and 'duration' keys.
    """
    try:
        # Try Chinese and English transcripts
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['zh-CN', 'zh-TW', 'zh', 'en'])
        return transcript
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
            response_mime_type="application/json",
            temperature=0.2
        )
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
            "tutorial": "Could not generate analysis tutorial."
        }

def analyze_youtube_video(video_id: str, title: str = "") -> dict:
    """Main orchestrator to analyze a YouTube video.
    Checks database cache first, then fetches and analyzes if missing.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Check database cache
    cursor.execute("""
    SELECT content_id, title, artist_or_movie, original_text, translated_text, pinyin_text
    FROM media_content WHERE video_id = ?
    """, (video_id,))
    row = cursor.fetchone()
    
    if row:
        content_id, db_title, artist, original_text, translated_text, pinyin_text = row
        # Also retrieve dictionary words from DB or generate if not saved
        # For cached DB hits, we retrieve lines
        lines = []
        orig_lines = original_text.split('\n')
        trans_lines = translated_text.split('\n')
        pinyin_lines = pinyin_text.split('\n') if pinyin_text else [''] * len(orig_lines)
        
        for i in range(len(orig_lines)):
            lines.append({
                "text": orig_lines[i],
                "pinyin": pinyin_lines[i] if i < len(pinyin_lines) else '',
                "translation": trans_lines[i] if i < len(trans_lines) else ''
            })
            
        # Retrieve tutorial / dictionary via a quick LLM check if needed, or query standard vocabulary
        # For simplicity, we can reconstruct or return cached content.
        # Let's generate a quick response from the database content
        conn.close()
        
        # Re-verify the cached response matches the output format
        # If we need a dictionary and tutorial, we can generate them or use cached versions.
        # Let's run a fast LLM request to get the complete structured response if the DB did not store the dict/tutorial
        # To avoid running LLM every time, we can run it once or save the dictionary/tutorial as JSON metadata.
        # Let's run the LLM request to ensure a rich response (with dictionary and tutorial) is returned.
        analysis = analyze_lyrics_with_llm(original_text, title=db_title)
        return {
            "content_id": content_id,
            "title": db_title,
            "artist_or_movie": artist,
            "lines": analysis.get("lines", lines),
            "dictionary": analysis.get("dictionary", []),
            "tutorial": analysis.get("tutorial", "Here is your saved tutorial for this song.")
        }
        
    # 2. Fetch transcript
    transcript_segments = fetch_youtube_transcript(video_id)
    
    if not transcript_segments:
        # Fallback: if no transcript, use Gemini to search or generate standard lyrics
        # based on title if provided, otherwise return error
        if not title:
            conn.close()
            return {"error": "No transcript available and no video title provided for search fallback."}
            
        prompt = f"Write the Chinese lyrics/script for the YouTube video '{title}'. Only output the Chinese lyrics themselves."
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=prompt
        )
        lyrics_text = response.text
    else:
        # Combine segments into plain text
        lyrics_text = "\n".join(seg["text"] for seg in transcript_segments)
        
    # 3. Analyze with Gemini
    analysis = analyze_lyrics_with_llm(lyrics_text, title=title or "Unknown YouTube Video")
    
    # Format texts for DB storage
    original_text = "\n".join(line["text"] for line in analysis["lines"])
    translated_text = "\n".join(line["translation"] for line in analysis["lines"])
    pinyin_text = "\n".join(line["pinyin"] for line in analysis["lines"])
    
    # Save to media_content database
    cursor.execute("""
    INSERT INTO media_content (title, artist_or_movie, media_type, language, difficulty, original_text, translated_text, pinyin_text, video_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (title or "YouTube Video", "YouTube", "song", "Chinese", "intermediate", original_text, translated_text, pinyin_text, video_id))
    
    content_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {
        "content_id": content_id,
        "title": title or "YouTube Video",
        "artist_or_movie": "YouTube",
        "lines": analysis["lines"],
        "dictionary": analysis["dictionary"],
        "tutorial": analysis["tutorial"]
    }
