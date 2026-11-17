from __future__ import annotations

import pytest
from pydantic import ValidationError

from lightly_studio.models.sample_query import SampleQueryRequest


class TestSampleQueryRequest:
    def test_validate_offset(self) -> None:
        assert SampleQueryRequest(offset=5).offset == 5
        assert SampleQueryRequest(cursor="abc").cursor == "abc"

    def test_validate_offset__with_cursor__raises(self) -> None:
        with pytest.raises(ValidationError, match="only on the first page"):
            SampleQueryRequest(cursor="abc", offset=5)

    @pytest.mark.parametrize("limit", [0, 1001])
    def test_limit__out_of_range__raises(self, limit: int) -> None:
        with pytest.raises(ValidationError):
            SampleQueryRequest(limit=limit)
