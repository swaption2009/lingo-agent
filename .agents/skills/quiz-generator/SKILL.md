---
name: quiz-generator
description: |
  Generates interactive language practice quizzes (fill-in-the-blank, multiple choice, translation) based on song lyrics or movie dialogue.
  Use when generating a quiz for a vocabulary word or grammar concept.
---
# Skill: Quiz Generator

This skill helps the agent generate structured interactive quizzes to test the user's understanding of foreign vocabulary and grammar in context.

## Guidelines
1. **Identify the Target Word**: Choose the word to test (e.g., "soy").
2. **Retrieve Context**: Use the original song verse or movie dialogue line containing the word.
3. **Formulate the Quiz**:
   - **Fill-in-the-blank**: Replace the target word with underscores. E.g. "Yo no ______ marinero."
   - **Translation**: Ask the user to translate a line from or to the target language.
   - **Multiple Choice**: Provide 3-4 options, ensuring only one is correct and others are plausible distractor words.
4. **Format the Output**: Always provide the original context line, the question, and clear instructions on how the user should answer.
5. **Evaluate Response**: Check the user's answer against the target word (case-insensitively, ignoring punctuation).
