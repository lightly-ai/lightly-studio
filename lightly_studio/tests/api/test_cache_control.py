from lightly_studio.api.cache_control import cache_control


def test_cache_control() -> None:
    assert cache_control(max_age_seconds=3600) == "public, max-age=3600"


def test_cache_control__private() -> None:
    assert cache_control(max_age_seconds=60, private=True) == "private, max-age=60"
