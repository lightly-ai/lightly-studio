from dataclasses import replace

import pytest

from prepare_release import packages, wheel
from prepare_release.errors import PrepareReleaseError

EMBED = packages.get("lightly-studio-embed")


def test_find_wheel(tmp_path):
    (tmp_path / "lightly_studio_embed-0.1.0-py3-none-any.whl").touch()
    (tmp_path / "lightly_studio_embed-0.1.0.tar.gz").touch()
    assert wheel.find_wheel(tmp_path).name == "lightly_studio_embed-0.1.0-py3-none-any.whl"


def test_find_wheel__none(tmp_path):
    with pytest.raises(PrepareReleaseError, match="found 0"):
        wheel.find_wheel(tmp_path)


def test_find_wheel__several(tmp_path):
    (tmp_path / "a-0.1.0-py3-none-any.whl").touch()
    (tmp_path / "a-0.2.0-py3-none-any.whl").touch()
    with pytest.raises(PrepareReleaseError, match="found 2"):
        wheel.find_wheel(tmp_path)


def test_parse_installed_names():
    listing = '[{"name": "numpy", "version": "2.1.0"}, {"name": "pillow", "version": "11.0.0"}]'
    assert wheel.parse_installed_names(listing) == ["numpy", "pillow"]


def test_parse_installed_names__not_json():
    with pytest.raises(PrepareReleaseError, match="could not read"):
        wheel.parse_installed_names("error: no environment found")


def test_parse_installed_names__missing_name():
    with pytest.raises(PrepareReleaseError, match="could not read"):
        wheel.parse_installed_names('[{"version": "2.1.0"}]')


def test_assert_no_forbidden_dependencies():
    wheel.assert_no_forbidden_dependencies(
        installed=["fastapi", "numpy", "pillow", "pydantic", "uvicorn", "lightly-studio-embed"],
        package=EMBED,
    )


def test_assert_no_forbidden_dependencies__transitive_torch():
    with pytest.raises(PrepareReleaseError, match="torchvision"):
        wheel.assert_no_forbidden_dependencies(installed=["numpy", "torchvision"], package=EMBED)


def test_assert_no_forbidden_dependencies__normalizes_before_matching():
    with pytest.raises(PrepareReleaseError, match="nvidia_cublas_cu12"):
        wheel.assert_no_forbidden_dependencies(installed=["nvidia_cublas_cu12"], package=EMBED)


def test_assert_no_forbidden_dependencies__lists_every_offender():
    with pytest.raises(PrepareReleaseError, match="duckdb, lightly-studio, opencv-python"):
        wheel.assert_no_forbidden_dependencies(
            installed=["opencv-python", "duckdb", "lightly-studio"], package=EMBED
        )


def test_normalize_name():
    assert wheel.normalize_name("NVIDIA_cuBLAS.cu12") == "nvidia-cublas-cu12"


def test_assert_no_forbidden_dependencies__normalizes_the_patterns_too():
    package = replace(EMBED, forbidden_dependencies=("OpenCV_Python",))
    with pytest.raises(PrepareReleaseError, match="opencv-python-headless"):
        wheel.assert_no_forbidden_dependencies(
            installed=["opencv-python-headless"], package=package
        )
