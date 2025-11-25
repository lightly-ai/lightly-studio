"""Example of how to add samples in coco caption format to a dataset."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from environs import Env
from sqlmodel import Session

import lightly_studio as ls
from lightly_studio import db_manager
from lightly_studio.plugins.base_operator import BaseOperator, OperatorResult
from lightly_studio.plugins.operator_registry import operator_registry
from lightly_studio.plugins.parameter import BaseParameter, BoolParameter, StringParameter


@dataclass
class TestOperator(BaseOperator):
    """Dummy Operator for demo purpose."""
    name: str = "test operator"
    description: str = "used to test the operator and registry system"

    @property
    def parameters(self) -> list[BaseParameter]:
        """Return the list of parameters this operator expects."""
        return [
            BoolParameter(name="test flag", required=True),
            StringParameter(name="test str", required=True),
        ]

    def execute(
        self,
        *,
        session: Session,
        dataset_id: UUID,
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Execute the operator with the given parameters.

        Args:
            session: Database session.
            dataset_id: ID of the dataset to operate on.
            parameters: Parameters passed to the operator.

        Returns:
            Dictionary with 'success' (bool) and 'message' (str) keys.
        """
        return OperatorResult(
            success=bool(parameters.get("test flag")),
            message=str(parameters.get("test str")) + " " + str(session) + " " + str(dataset_id),
        )


# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Define data paths
annotations_json = env.path(
    "EXAMPLES_COCO_CAPTION_JSON_PATH", "/path/to/your/dataset/annotations.json"
)
images_path = env.path("EXAMPLES_COCO_CAPTION_IMAGES_PATH", "/path/to/your/dataset")

test =  TestOperator()
for i in range(20):
    operator_registry.register(operator=TestOperator(name=f"test_{i}"))

# Create a DatasetLoader from a path
dataset = ls.Dataset.create()
dataset.add_samples_from_coco_caption(
    annotations_json=annotations_json,
    images_path=images_path,
)

ls.start_gui()
