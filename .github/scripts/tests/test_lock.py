import pytest

from prepare_release import lock
from prepare_release.errors import PrepareReleaseError

SAMPLE_LOCK = """\
version = 1
revision = 2

[[package]]
name = "alpha"
version = "1.0.0"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "lightly-studio"
version = "1.0.5"
source = { editable = "." }
dependencies = [
    { name = "alpha" },
]
"""


SAMPLE_LOCK_WITH_DUPLICATE = """\
version = 1
revision = 2

[[package]]
name = "alpha"
version = "1.0.0"
source = { registry = "https://pypi.org/simple" }
resolution-markers = [
    "python_full_version < '3.11'",
]

[[package]]
name = "alpha"
version = "1.0.0"
source = { registry = "https://pypi.org/simple" }
resolution-markers = [
    "python_full_version >= '3.11'",
]

[[package]]
name = "lightly-studio"
version = "1.0.5"
source = { editable = "." }
dependencies = [
    { name = "alpha" },
]
"""


def test_assert_lock_diff_narrow__version_only_change_is_ok():
    after = SAMPLE_LOCK.replace(
        'name = "lightly-studio"\nversion = "1.0.5"', 'name = "lightly-studio"\nversion = "1.0.6"'
    )
    lock.assert_lock_diff_narrow(SAMPLE_LOCK, after, package="lightly-studio")


def test_assert_lock_diff_narrow__unrelated_package_changed_raises():
    after = SAMPLE_LOCK.replace(
        'name = "alpha"\nversion = "1.0.0"', 'name = "alpha"\nversion = "1.1.0"'
    )
    with pytest.raises(PrepareReleaseError, match="alpha"):
        lock.assert_lock_diff_narrow(SAMPLE_LOCK, after, package="lightly-studio")


def test_assert_lock_diff_narrow__broader_change_to_target_package_raises():
    after = SAMPLE_LOCK.replace(
        'version = "1.0.5"\nsource = { editable = "." }',
        'version = "1.0.6"\nsource = { editable = "./elsewhere" }',
    )
    with pytest.raises(PrepareReleaseError, match="more than its version line"):
        lock.assert_lock_diff_narrow(SAMPLE_LOCK, after, package="lightly-studio")


def test_assert_lock_diff_narrow__unchanged_duplicate_blocks_are_ok():
    lock.assert_lock_diff_narrow(
        SAMPLE_LOCK_WITH_DUPLICATE,
        SAMPLE_LOCK_WITH_DUPLICATE.replace('version = "1.0.5"', 'version = "1.0.6"'),
        package="lightly-studio",
    )


def test_assert_lock_diff_narrow__change_to_first_of_duplicate_blocks_raises():
    # A change to the first duplicate block must not be masked by the second.
    after = SAMPLE_LOCK_WITH_DUPLICATE.replace(
        'name = "alpha"\nversion = "1.0.0"\nsource = { registry = "https://pypi.org/simple" }\n'
        "resolution-markers = [\n    \"python_full_version < '3.11'\",\n]",
        'name = "alpha"\nversion = "1.1.0"\nsource = { registry = "https://pypi.org/simple" }\n'
        "resolution-markers = [\n    \"python_full_version < '3.11'\",\n]",
        1,
    )
    with pytest.raises(PrepareReleaseError, match="alpha"):
        lock.assert_lock_diff_narrow(SAMPLE_LOCK_WITH_DUPLICATE, after, package="lightly-studio")


def test_parse_lock_blocks():
    blocks = lock._parse_lock_blocks(SAMPLE_LOCK)
    assert set(blocks) == {"", "alpha", "lightly-studio"}
    assert 'version = "1.0.5"' in blocks["lightly-studio"][0]


def test_parse_lock_blocks__preserves_duplicate_package_blocks():
    blocks = lock._parse_lock_blocks(SAMPLE_LOCK_WITH_DUPLICATE)
    assert len(blocks["alpha"]) == 2
    assert "< '3.11'" in blocks["alpha"][0]
    assert ">= '3.11'" in blocks["alpha"][1]
