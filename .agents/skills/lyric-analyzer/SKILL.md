---
name: lyric-analyzer
description: |
  Analyzes lyrics or movie dialogues, segments them line-by-line, and generates phonetic guides and translations.
  Use when the user wants to break down a song or dialogue line.
---
# Skill: Lyric Analyzer

This skill helps the agent segment and analyze foreign language text from lyrics or dialogues, providing translations and phonetic pronunciation guides.

## Guidelines
1. Segment the text into single lines or short verses.
2. Generate phonetic/pronunciation guides for the line to help the user pronounce it.
3. For Spanish, you can run the helper script `phonetic_generator.py` to generate phonetic annotations:
   - Call `run_skill_script` with `file_path="scripts/phonetic_generator.py"` and argument `args=["<text_line>"]`.
4. Explain key vocabulary verbs or nouns in the line.
