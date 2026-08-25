#!/usr/bin/env python3
"""PreToolUse hook: remind the agent to load the guideline skill for the file it edits.

Maps the edited path to the matching guide skill(s). Reminds once per session per area.
Fails open: on any error it exits 0 with no output, so an edit is never blocked.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

# Path prefix + file suffixes -> guide skills to load. First match wins, so the backend
# package (a subdirectory) comes before the general lightly_studio rule.
SKILLS_BY_PATH = [
    ("lightly_studio/src/lightly_studio/", (".py",), ["python-guide", "backend-guide"]),
    ("lightly_studio/", (".py",), ["python-guide"]),
    ("lightly_studio_view/", (".ts", ".svelte"), ["frontend-guide"]),
]


def skills_for(rel_path: str) -> list[str]:
    for prefix, suffixes, skills in SKILLS_BY_PATH:
        if rel_path.startswith(prefix) and rel_path.endswith(suffixes):
            return skills
    return []


def first_time(session_id: str, skill: str) -> bool:
    """True the first time this session touches this skill; records it for next time.

    Fails open: on any filesystem error (including an existing marker) it returns
    False, so a marker problem never produces a reminder. `touch(exist_ok=False)`
    makes the create atomic against a concurrent hook.
    """
    marker_dir = Path(tempfile.gettempdir()) / "claude-skill-reminder"
    marker = marker_dir / f"{session_id}-{skill}"
    try:
        marker_dir.mkdir(parents=True, exist_ok=True)
        marker.touch(exist_ok=False)
    except OSError:
        return False
    return True


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or payload["cwd"]).resolve()
        file_path = Path(payload["tool_input"]["file_path"]).resolve()
        rel_path = str(file_path.relative_to(root))
    except Exception:
        return 0  # Fail open: never block an edit.

    session_id = payload.get("session_id", "session")
    skills = []
    for skill in skills_for(rel_path):
        if first_time(session_id=session_id, skill=skill):
            skills.append(skill)
    if not skills:
        return 0

    context = (
        f"You are editing {rel_path}. Load the {', '.join(skills)} skill(s) with the "
        f"Skill tool before continuing. See AGENTS.md for the path-to-skill map."
    )
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": context,
        }
    }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
