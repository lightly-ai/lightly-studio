import pytest

from lightly_studio.models.collection import SampleType
from lightly_studio.plugins import operator_context
from lightly_studio.plugins.operator_context import OperatorScope


@pytest.mark.parametrize("sample_type", list(SampleType))
def test_get_allowed_scopes_for_collection(sample_type: SampleType) -> None:
    # Make sure each known sampletype can be mapped to a operator type
    scope = OperatorScope(sample_type.value)
    assert operator_context.get_allowed_scopes_for_collection(
        sample_type=sample_type, is_root_collection=False
    ) == [scope]
    assert operator_context.get_allowed_scopes_for_collection(
        sample_type=sample_type, is_root_collection=True
    ) == [
        OperatorScope.ROOT,
        scope,
    ]
