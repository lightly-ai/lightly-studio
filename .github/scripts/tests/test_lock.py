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


def test_parse_lock_blocks():
    blocks = lock.parse_lock_blocks(SAMPLE_LOCK)
    assert set(blocks) == {"", "alpha", "lightly-studio"}
    assert 'version = "1.0.5"' in blocks["lightly-studio"]


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
