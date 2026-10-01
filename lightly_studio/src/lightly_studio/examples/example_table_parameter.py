"""Example of an operator with a table parameter.

A `TableParameter` accepts a variable number of rows sharing the same columns. Each column is a
built-in parameter, so it carries its own type, description, default and required flag. The GUI
renders one cell per column, typed after that column, and the operator receives the rows as a
`list[dict[str, Any]]` keyed by column name.
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
    BoolParameter,
    FloatParameter,
    StringParameter,
    TableParameter,
)

PROMPTS = "prompts"


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
                name=PROMPTS,
                description="Prompts to segment with and how to filter their masks.",
                # More columns than the dialog fits, so the table scrolls horizontally.
                columns=[
                    StringParameter(name="prompt", description="What to segment."),
                    StringParameter(
                        name="label", description="Label for the masks.", default="pedestrian"
                    ),
                    FloatParameter(
                        name="threshold", description="Minimum confidence.", default=0.5
                    ),
                    BoolParameter(name="enabled", description="Run this prompt.", default=True),
                ],
                # A row must hold every declared column, so the default fills all four in.
                default=[
                    {"prompt": "person", "label": "pedestrian", "threshold": 0.5, "enabled": True}
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
        """Report the prompts that were entered in the GUI.

        Args:
            session: Database session.
            context: Execution context containing collection_id and optional filter.
            parameters: Parameters passed to the operator.

        Returns:
            An OperatorResult listing the received rows.
        """
        # Parameters reach the operator unvalidated, so check the shape before reading cells.
        rows = parameters.get(PROMPTS)
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            return OperatorResult(success=False, message="Expected a table of prompts.")
        if not rows:
            return OperatorResult(success=False, message="No prompts provided.")

        summary = ", ".join(f"{row.get('prompt')} -> {row.get('label')}" for row in rows)
        return OperatorResult(success=True, message=f"Received {len(rows)} prompt(s): {summary}")


env = Env()
env.read_env()

db_manager.connect(cleanup_existing=True)
operator_registry.register(operator=PromptTableOperator())

dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path=env.path("EXAMPLES_DATASET_PATH"))

ls.start_gui()
