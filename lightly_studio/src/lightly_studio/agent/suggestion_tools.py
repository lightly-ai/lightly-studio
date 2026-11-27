"""The agent tool that suggests the next steps to the user.

The GUI shows each step as a button. It reads the steps from the arguments of the tool call in
the transcript, so the tool itself changes nothing.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from lightly_studio.agent.agent_tool import AgentContext, AgentTool

# The name of the tool. The agent loop uses it to detect when tool work is complete.
SUGGEST_NEXT_STEPS = "suggest_next_steps"

# The largest number of characters in the text of one button.
_MAX_LABEL_LENGTH = 40

# The largest number of steps in one suggestion.
_MAX_STEPS = 3


class SuggestedStep(BaseModel):
    """One next step that the user can do with one click."""

    label: str = Field(
        min_length=1,
        max_length=_MAX_LABEL_LENGTH,
        description="The short text of the button, for example 'Tag these samples'.",
    )
    prompt: str = Field(
        min_length=1,
        description=(
            "The full request that the click sends as the user message, with real names and "
            "counts, for example 'Tag the 12 clock samples as clock.'"
        ),
    )


class SuggestNextStepsArgs(BaseModel):
    """Arguments of ``suggest_next_steps``."""

    steps: list[SuggestedStep] = Field(min_length=1, max_length=_MAX_STEPS)


def suggest_next_steps(context: AgentContext, args: SuggestNextStepsArgs) -> dict[str, Any]:
    """Accept the suggested steps. The GUI reads them from the tool call."""
    del context
    return {"suggested_count": len(args.steps)}


SUGGESTION_TOOLS: list[AgentTool[Any]] = [
    AgentTool(
        name=SUGGEST_NEXT_STEPS,
        description=(
            f"Suggest 1 to {_MAX_STEPS} next steps to the user as buttons. Call it in the same "
            "message as your written answer."
        ),
        args_model=SuggestNextStepsArgs,
        run=suggest_next_steps,
    ),
]
