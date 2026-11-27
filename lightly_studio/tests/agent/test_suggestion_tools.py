from __future__ import annotations

import pytest
from pydantic import ValidationError
from sqlmodel import Session

from lightly_studio.agent import suggestion_tools
from lightly_studio.agent.suggestion_tools import SuggestedStep, SuggestNextStepsArgs
from tests import helpers_resolvers
from tests.agent import helpers_agent


def test_suggest_next_steps(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    context = helpers_agent.create_context(session=db_session, collection=collection)
    args = SuggestNextStepsArgs(
        steps=[
            SuggestedStep(label="Tag these samples", prompt="Tag the 12 samples as clock."),
            SuggestedStep(label="Find similar", prompt="Find 20 samples similar to these."),
        ]
    )

    result = suggestion_tools.suggest_next_steps(context, args)

    assert result == {"suggested_count": 2}
    assert context.ui_actions == []


def test_suggest_next_steps_args__too_many_steps() -> None:
    step = {"label": "Tag", "prompt": "Tag them."}
    with pytest.raises(ValidationError, match="at most 3 items"):
        SuggestNextStepsArgs.model_validate({"steps": [step, step, step, step]})


def test_suggest_next_steps_args__label_too_long() -> None:
    step = {"label": "x" * 41, "prompt": "Tag them."}
    with pytest.raises(ValidationError, match="at most 40 characters"):
        SuggestNextStepsArgs.model_validate({"steps": [step]})
