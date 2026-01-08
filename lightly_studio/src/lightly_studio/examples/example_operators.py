"""Example of how to register operators."""

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
from lightly_studio.plugins.parameter import (
    BaseParameter,
    BoolParameter,
    FloatParameter,
    IntParameter,
    StringParameter,
)


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
            StringParameter(name="test str", required=True, default="Good Morning"),
            StringParameter(
                name="test str 2", required=True, default="Another", description="Test Description"
            ),
            BoolParameter(
                name="test flag 2", required=True, description="Test Description", default=True
            ),
            FloatParameter(name="test float", required=False, default=2.0, description="abc"),
            IntParameter(name="test int", required=False, default=2),
            IntParameter(name="test int 2", required=True, description="Yet another int"),
            IntParameter(
                name="test int 3",
                required=True,
                description=(
                    "Yet another int with a very long description. this will show how we will "
                    "overflow or what soever is happening to this text in the GUI. maybe it "
                    "exceeds maybe not. only time will tell"
                ),
            ),
        ]

    def execute(
        self,
        *,
        session: Session,
        collection_id: UUID,
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Execute the operator with the given parameters.

        Args:
            session: Database session.
            collection_id: ID of the collection to operate on.
            parameters: Parameters passed to the operator.

        Returns:
            Dictionary with 'success' (bool) and 'message' (str) keys.
        """
        return OperatorResult(
            success=bool(parameters.get("test flag")),
            message=str(parameters.get("test str"))
            + " "
            + str(parameters.get("test str 2"))
            + " "
            + str(parameters.get("test flag 2"))
            + " "
            + str(parameters.get("test float"))
            + " "
            + str(parameters.get("test int"))
            + " "
            + str(collection_id)
            + str(session),
        )


# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Setup dummy operators
test = TestOperator()
for i in range(20):
    operator_registry.register(operator=TestOperator(name=f"test_{i}"))

# Define data path
dataset_path = env.path("EXAMPLES_DATASET_PATH", "/path/to/your/dataset")

# Create a DatasetLoader from a path
dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path=dataset_path)

ls.start_gui()
