#!/usr/bin/env python3
"""PreToolUse hook: remind the agent to load the guideline skill for the file it edits.

Maps the edited path to the matching guide skill(s) and injects a reminder the first time
each guide's area is touched in a session. Fails open: on any error it exits 0 with no
output, so an edit is never blocked.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

# Path prefix + file suffixes -> guide skills to load. First match wins, so the backend
# package (a subdirectory) comes before the general lightly_studio rule.
SKILLS_BY_PATH = [
    ("lightly_studio/src/lightly_studio/", (".py",), ["python-guide", "backend-guide"]),
    ("lightly_studio/", (".py",), ["python-guide"]),
    ("lightly_studio_view/", (".ts", ".svelte", ".js"), ["frontend-guide"]),
]


def skills_for(rel_path: str) -> list[str]:
    for prefix, suffixes, skills in SKILLS_BY_PATH:
        if rel_path.startswith(prefix) and rel_path.endswith(suffixes):
            return skills
    return []


def first_time(session_id: str, skill: str) -> bool:
    """True the first time this session touches this skill; records it for next time."""
    marker = Path(tempfile.gettempdir()) / "claude-skill-reminder" / f"{session_id}-{skill}"
    if marker.exists():
        return False
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.touch()
    return True


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        root = Path(payload["cwd"]).resolve()
        rel_path = str(Path(payload["tool_input"]["file_path"]).resolve().relative_to(root))
    except Exception:
        return 0  # Fail open: never block an edit.

    session_id = payload.get("session_id", "session")
    skills = [s for s in skills_for(rel_path) if first_time(session_id=session_id, skill=s)]
    if not skills:
        return 0

    context = (
        f"You are editing {rel_path}. Load the {', '.join(skills)} skill(s) with the "
        f"Skill tool before continuing. See AGENTS.md for the path-to-skill map."
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": context,
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
