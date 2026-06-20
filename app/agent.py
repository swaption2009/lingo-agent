# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import google.auth
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

# Import MCP tools support from ADK
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

# Import Skill tools support from ADK
import google.adk.skills as adk_skills
from google.adk.tools.skill_toolset import SkillToolset

# Google Cloud & Vertex AI credentials setup
_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

# Resolve absolute paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
mcp_server_path = os.path.join(project_root, "mcp_server.py")
skills_base_dir = os.path.join(project_root, ".agents", "skills")

# 1. Configure the MCP Toolset (stdio connection)
mcp_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="python3",
            args=[mcp_server_path],
        )
    )
)

# 2. Discover and Load local Agent Skills
skills = []
if os.path.exists(skills_base_dir):
    for entry in os.scandir(skills_base_dir):
        if entry.is_dir() and os.path.exists(os.path.join(entry.path, "SKILL.md")):
            try:
                skill_obj = adk_skills.load_skill_from_dir(entry.path)
                skills.append(skill_obj)
            except Exception as e:
                pass

skill_toolset = SkillToolset(skills=skills)

# Expose both MCP tools and Skill tools
shared_tools = [mcp_toolset, skill_toolset]

# Define Model Config
model_config = Gemini(
    model="gemini-flash-latest",
    retry_options=types.HttpRetryOptions(attempts=3),
)

def safety_policy_callback(tool, args, tool_context) -> dict | None:
    tool_name = tool.name
    
    # 1. Prevent directory traversal / unauthorized script execution
    if tool_name == "run_skill_script":
        file_path = args.get("file_path", "")
        if ".." in file_path or file_path.startswith("/") or not file_path.startswith("scripts/"):
            return {
                "error": f"Security Exception: Access to script path '{file_path}' is denied by safety policy."
            }
            
    # 2. Interactive "Vibe Diff" summary & approval hook for database modifications
    if tool_name in ["add_vocabulary_word", "delete_vocabulary_word", "reset_vocab_deck"]:
        import sys
        diff_summary = "\n" + "="*50 + "\n"
        diff_summary += f"⚠️  [Vibe Diff - Database Modification Request]\n"
        diff_summary += f"Tool: {tool_name}\n"
        diff_summary += f"Arguments:\n"
        for k, v in args.items():
            diff_summary += f"  - {k}: {v}\n"
        diff_summary += "="*50 + "\n"
        
        print(diff_summary, file=sys.stderr, flush=True)
        
        # Interactive confirmation check
        if sys.stdin.isatty():
            try:
                response = input("Do you approve this database change? (y/N): ").strip().lower()
                if response in ["y", "yes"]:
                    print("✅ Database change approved by user.", file=sys.stderr, flush=True)
                    return None  # Let the tool run
                else:
                    print("❌ Database change rejected by user.", file=sys.stderr, flush=True)
                    return {"status": "cancelled", "message": "Database action rejected by the user."}
            except Exception as e:
                return {"status": "error", "message": f"Interactive input failed: {e}"}
        else:
            print("🤖 Non-interactive environment detected. Auto-approving change.", file=sys.stderr, flush=True)
            return None

    return None

# 3. Define the cooperative sub-agents

# Sub-agent: LingoParser (Linguistic Segmentation)
lingo_parser = Agent(
    name="lingo_parser",
    model=model_config,
    description=(
        "Handles retrieving learning content (songs, movies), segmenting foreign lyrics/dialogues, "
        "translating them, and identifying vocabulary words to study."
    ),
    instruction=(
        "You are LingoParser, a specialized sub-agent for foreign language song lyrics and movie script dialogue segmentation.\n"
        "Your job is to:\n"
        "1. Retrieve the selected media content using `get_media_content`.\n"
        "2. Segment the foreign language lyrics or dialogue lines.\n"
        "3. Select a specific line to focus on, translate it, and identify key vocabulary words or grammatical items in that line.\n"
        "4. Present the selected line and translation to the user, and identify the vocabulary word you will study.\n"
        "5. Transfer control to `lingo_coach` to create a quiz for the identified words. To delegate, state that you are handing over to lingo_coach."
    ),
    tools=shared_tools,
    before_tool_callback=safety_policy_callback,
)

# Sub-agent: LingoCoach (Vocabulary & Quiz Coach)
lingo_coach = Agent(
    name="lingo_coach",
    model=model_config,
    description=(
        "Teaches the user about the selected vocabulary word in context, generates fill-in-the-blank "
        "or translation quizzes, evaluates their answer, and saves successfully learned words to their flashcard deck."
    ),
    instruction=(
        "You are LingoCoach, a specialized vocabulary and quiz tutor.\n"
        "Your job is to:\n"
        "1. Teach the user the selected vocabulary word in context (meaning, usage).\n"
        "2. Generate a fill-in-the-blank or translation quiz based on the song lyrics or movie dialogue. Use the quiz-generator skill if available.\n"
        "3. Evaluate the user's response.\n"
        "4. If the user answers correctly, add the word to their flashcard deck using the `add_vocabulary_word` tool.\n"
        "5. If they answer incorrectly, explain the correct answer and encourage them.\n"
        "6. List the next steps and hand control back to the orchestrator (lingo_host) by stating you are done and transferring back."
    ),
    tools=shared_tools,
    before_tool_callback=safety_policy_callback,
)

# Root Orchestrator: LingoHost
lingo_host = Agent(
    name="lingo_host",
    model=model_config,
    instruction=(
        "You are LingoHost, the central orchestrator for LingoKaraoke and CinemaLingo.\n"
        "You help users learn foreign languages (mainly Spanish) through song lyrics and movie dialogues.\n"
        "Your job is to:\n"
        "1. Greet the user, explain the language learning capabilities, and retrieve their profile using `get_user_profile` (call it without passing any arguments, i.e. {}).\n"
        "2. Help users search for songs or movie dialogues using `search_learning_media` (pass only the query argument, e.g. query='La Bamba', and do not specify the language parameter).\n"
        "3. Delegate the actual lyric segmentation and analysis to `lingo_parser` when a user wants to study a song or scene.\n"
        "4. Coordinate with `lingo_coach` to run the active practice and vocabulary logging.\n"
        "5. List their vocabulary deck if requested using `get_vocab_deck`.\n\n"
        "To start a lesson, search for the content, retrieve its ID, and delegate to `lingo_parser` by stating you are transferring control."
    ),
    tools=shared_tools,
    sub_agents=[lingo_parser, lingo_coach],
    before_tool_callback=safety_policy_callback,
)

root_agent = lingo_host

app = App(
    root_agent=root_agent,
    name="app",
)
