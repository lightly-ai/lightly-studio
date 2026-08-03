"""Manual check for the optional-numeric-column fix in `ParameterTable`.

TEMPORARY: added so reviewers can try the fix by hand. Delete before merging. The permanent table
parameter example arrives with the Storybook part of this stack as `example_table_parameter.py`.

Run it, open the GUI, and run "segment with prompts" from the root scope.

The `threshold` column is `required=False` and has no default, so a new row starts it at ''.
Before the fix that cell looked fine and the backend rejected the row with:

    TypeError: Invalid cell 'threshold' in row 0:
    Expected value of type 'float' but got <class 'str'>'

After the fix the cell is outlined as invalid the moment the row appears, so the state is visible
before submitting. Filling in a number clears it.

What to look at:
  - "Add row" -> `threshold` and `limit` are flagged, `prompt` and `label` are not.
  - Type a number into `threshold` -> the flag clears while the row is still incomplete otherwise.
  - Clear it again -> the flag comes back (defaults alone would not cover this).
  - `label` is optional text and stays unflagged even when empty; '' is a valid str.
  - Execute with every numeric cell filled -> the message echoes the parsed rows and their types.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from environs import Env
from sqlmodel import Session

import lightly_studio as ls
from lightly_studio.database import db_manager
from lightly_studio.plugins.base_operator import BaseOperator, OperatorResult
from lightly_studio.plugins.operator_context import ExecutionContext, OperatorScope
from lightly_studio.plugins.operator_registry import operator_registry
from lightly_studio.plugins.parameter import (
    BaseParameter,
    FloatParameter,
    IntParameter,
    StringParameter,
    TableParameter,
)


@dataclass
class SegmentWithPromptsOperator(BaseOperator):
    """Operator whose table parameter mixes required and optional columns of both types."""

    name: str = "segment with prompts"
    description: str = "Demonstrates a table parameter with optional numeric columns."

    @property
    def parameters(self) -> list[BaseParameter]:
        """Return the table parameter this operator expects."""
        return [
            TableParameter(
                name="prompts",
                description="One row per prompt to segment with.",
                columns=[
                    # Required text: flagged only once the table blocks submission.
                    StringParameter(name="prompt", description="What to segment."),
                    # Optional text: '' is a valid str, so it is never flagged.
                    StringParameter(
                        name="label",
                        description="Label to assign. Optional, blank is fine.",
                        required=False,
                    ),
                    # Optional number with no default: the case the fix is about.
                    FloatParameter(
                        name="threshold",
                        description="Confidence threshold. Optional, but must be a number.",
                        required=False,
                    ),
                    # Required number, for comparison: same flag, different reason.
                    IntParameter(name="limit", description="Maximum masks to keep."),
                ],
            )
        ]

    @property
    def supported_scopes(self) -> list[OperatorScope]:
        """Return the list of scopes this operator can be triggered from."""
        return [OperatorScope.ROOT]

    def execute(
        self,
        *,
        session: Session,  # noqa: ARG002
        context: ExecutionContext,  # noqa: ARG002
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Report the rows that arrived, with the Python type of every cell.

        Args:
            session: Database session.
            context: Execution context containing collection_id and optional filter.
            parameters: Parameters passed to the operator.

        Returns:
            The rows received, so the types that survived the round trip are visible in the GUI.
        """
        # Parameters are not validated against the declared schema before they reach `execute`,
        # so the rows are read defensively.
        rows = parameters.get("prompts")
        if not isinstance(rows, list):
            return OperatorResult(success=False, message=f"Expected a list but got {type(rows)}")

        described = [
            ", ".join(f"{name}={value!r} ({type(value).__name__})" for name, value in row.items())
            if isinstance(row, dict)
            else f"not a dict: {row!r}"
            for row in rows
        ]
        return OperatorResult(
            success=True,
            message=f"Received {len(rows)} row(s): " + " | ".join(described),
        )


env = Env()
env.read_env()

db_manager.connect(cleanup_existing=True)

operator_registry.register(operator=SegmentWithPromptsOperator())

dataset_path = env.path("EXAMPLES_DATASET_PATH")

dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path=dataset_path)

ls.start_gui()
