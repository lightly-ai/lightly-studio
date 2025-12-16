from dataclasses import dataclass

from lightly_studio.plugins.base_operator import BaseOperator, OperatorResult
from lightly_studio.plugins.parameter import StringParameter


@dataclass
class GreetingOperator(BaseOperator):
    name: str = "GreetingOperator"
    description: str = "This operator greet you"

    @property
    def parameters(self):
        return [
            StringParameter(
                name="name",
                required=True,
                default="beautiful and smart person",
                description="your name"
            ),
        ]

    def execute(self, *, session, dataset_id, parameters):
        your_name = parameters.get("name", "")
        return OperatorResult(success=True, message=f"Hello {your_name}!")
