"""Example of an operator plugin with a table parameter.

A `TableParameter` lets an operator accept a variable number of rows, where every row provides the
same set of columns. Use it when a single scalar parameter is not enough, for example to pair a
segmentation prompt with the label, colour and thresholds to apply to it.

This example declares five columns, more than the operator dialog can show at once, so the table
scrolls horizontally: the header scrolls along with the rows and the remove button stays pinned
to the right edge.

Each column is a built-in parameter, so it carries its own type, description, default and required
flag. The GUI renders one cell per column, typed after that column: a text input for `str`, a number
input for `int` and `float`, and a checkbox for `bool`. It pre-fills new cells with the column
default and lets the user add and remove rows. The operator receives the rows as a
`list[dict[str, Any]]`, keyed by column name. This example simply reports the rows it received back
to the GUI.
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
    StringParameter,
    TableParameter,
)

PARAM_PROMPTS = "prompts"
COLUMN_PROMPT = "prompt"
COLUMN_LABEL = "label"
COLUMN_COLOR = "color"
COLUMN_THRESHOLD = "threshold"
COLUMN_MIN_AREA = "min_area"


@dataclass
class PromptTableOperator(BaseOperator):
    """Operator that collects prompts and their settings through a table parameter."""

    name: str = "Prompt Table"
    description: str = "Collects a table of segmentation prompts and their settings."

    @property
    def parameters(self) -> list[BaseParameter]:
        """Return the list of parameters this operator expects."""
        return [
            TableParameter(
                name=PARAM_PROMPTS,
                required=True,
                description=(
                    "Prompt to segment with, the label and colour to give its masks, and the "
                    "thresholds to filter them by."
                ),
                columns=[
                    StringParameter(
                        name=COLUMN_PROMPT, description="What to segment in the image."
                    ),
                    StringParameter(
                        name=COLUMN_LABEL,
                        description="Label to assign to the resulting masks.",
                        default="pedestrian",
                        required=False,
                    ),
                    StringParameter(
                        name=COLUMN_COLOR,
                        description="Hex colour to draw the masks in.",
                        default="#ff0000",
                        required=False,
                    ),
                    FloatParameter(
                        name=COLUMN_THRESHOLD,
                        description="Minimum confidence to keep a mask.",
                        default=0.5,
                        required=False,
                    ),
                    FloatParameter(
                        name=COLUMN_MIN_AREA,
                        description="Smallest mask area to keep, as a fraction of the image.",
                        default=0.01,
                        required=False,
                    ),
                ],
                default=[
                    {
                        COLUMN_PROMPT: "person",
                        COLUMN_LABEL: "pedestrian",
                        COLUMN_COLOR: "#ff0000",
                        COLUMN_THRESHOLD: 0.5,
                        COLUMN_MIN_AREA: 0.01,
                    }
                ],
            ),
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
        """Report the prompts and their settings that were entered in the GUI.

        Args:
            session: Database session.
            context: Execution context containing collection_id and optional filter.
            parameters: Parameters passed to the operator.

        Returns:
            An OperatorResult listing the received rows.
        """
        # The rows are not validated against the declared parameters before they reach the
        # operator, so read them defensively.
        rows = parameters.get(PARAM_PROMPTS) or []
        if not rows:
            return OperatorResult(success=False, message="No prompts provided.")

        summary = ", ".join(
            f"{row.get(COLUMN_PROMPT, '')} -> {row.get(COLUMN_LABEL, '')} "
            f"@ {row.get(COLUMN_THRESHOLD, '')}"
            for row in rows
        )
        return OperatorResult(success=True, message=f"Received {len(rows)} prompt(s): {summary}")


# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Register the operator so the GUI lists it
operator_registry.register(operator=PromptTableOperator())

# Define data path
dataset_path = env.path("EXAMPLES_DATASET_PATH")

# Create a dataset from a path
dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path=dataset_path)

ls.start_gui()
