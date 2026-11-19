from __future__ import annotations

import dataclasses

import pytest

from lightly_studio.api.dependencies import identity
from lightly_studio.api.replaceable import Replaceable


class TestReplaceable:
    def test_init(self) -> None:
        replace = Replaceable()

        assert replace.get_identity is identity.get_identity

    def test_init__replacement(self) -> None:
        replace = Replaceable(get_identity=identity.get_proxy_identity)

        assert replace.get_identity is identity.get_proxy_identity

    def test_init__is_frozen(self) -> None:
        replace = Replaceable()

        with pytest.raises(dataclasses.FrozenInstanceError):
            replace.get_identity = identity.get_proxy_identity  # type: ignore[misc]

    def test_fields(self) -> None:
        defaults = {field.name: field.default for field in dataclasses.fields(Replaceable)}

        assert defaults == {"get_identity": identity.get_identity}
