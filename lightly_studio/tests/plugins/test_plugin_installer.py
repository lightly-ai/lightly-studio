from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from lightly_studio.dataset import env
from lightly_studio.errors import NotFoundError
from lightly_studio.plugins import plugin_installer
from lightly_studio.plugins.operator_registry import operator_registry
from lightly_studio.plugins.plugin_catalog import CatalogEntry
from lightly_studio.plugins.plugin_installer import InstallJob, InstallJobStatus
from lightly_studio.utils import executor

_ENTRY = CatalogEntry(id="lightly_plugins_demo", name="Demo", install_spec="git+https://x#y")


@pytest.fixture(autouse=True)
def _empty_jobs(mocker: MockerFixture) -> None:
    mocker.patch.object(plugin_installer, "_jobs", {})


@pytest.mark.parametrize(
    ("client_host", "expected"),
    [
        ("127.0.0.1", True),
        ("::1", True),
        ("localhost", True),
        ("192.168.1.20", False),
        ("testclient", False),
        (None, False),
    ],
)
def test_is_install_allowed(mocker: MockerFixture, client_host: str | None, expected: bool) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_ALLOW_PLUGIN_INSTALL", None)
    assert plugin_installer.is_install_allowed(client_host=client_host) == expected


@pytest.mark.parametrize("override", [True, False])
def test_is_install_allowed__env_override(mocker: MockerFixture, override: bool) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_ALLOW_PLUGIN_INSTALL", override)
    assert plugin_installer.is_install_allowed(client_host="192.168.1.20") == override
    assert plugin_installer.is_install_allowed(client_host="127.0.0.1") == override


def test_start_install(mocker: MockerFixture) -> None:
    run_install = mocker.patch.object(plugin_installer, "_run_install")
    mocker.patch.object(executor, "get_media_executor", return_value=_SyncPool())

    job = plugin_installer.start_install(entry=_ENTRY)

    assert job.plugin_id == "lightly_plugins_demo"
    assert job.status == InstallJobStatus.QUEUED
    run_install.assert_called_once()
    assert run_install.call_args.kwargs["install_spec"] == "git+https://x#y"


def test_start_install__reuses_running_job(mocker: MockerFixture) -> None:
    mocker.patch.object(plugin_installer, "_run_install")
    mocker.patch.object(executor, "get_media_executor", return_value=_SyncPool())

    first = plugin_installer.start_install(entry=_ENTRY)
    second = plugin_installer.start_install(entry=_ENTRY)

    assert first.job_id == second.job_id


def test_get_job() -> None:
    plugin_installer._jobs["job-1"] = InstallJob(job_id="job-1", plugin_id="p")

    assert plugin_installer.get_job(job_id="job-1").plugin_id == "p"
    with pytest.raises(NotFoundError, match="'job-2' not found"):
        plugin_installer.get_job(job_id="job-2")


def test_build_install_command__uv(mocker: MockerFixture) -> None:
    mocker.patch.object(shutil, "which", return_value="/bin/uv")

    command = plugin_installer.build_install_command(
        install_spec="pkg", constraints_path=Path("/tmp/c.txt")
    )

    assert command == [
        "/bin/uv",
        "pip",
        "install",
        "--python",
        sys.executable,
        "--constraint",
        "/tmp/c.txt",
        "pkg",
    ]


def test_build_install_command__pip(mocker: MockerFixture) -> None:
    mocker.patch.object(shutil, "which", return_value=None)

    command = plugin_installer.build_install_command(
        install_spec="pkg", constraints_path=Path("/tmp/c.txt")
    )

    assert command == [sys.executable, "-m", "pip", "install", "--constraint", "/tmp/c.txt", "pkg"]


def test_run_install__success(mocker: MockerFixture) -> None:
    job = InstallJob(job_id="job-1", plugin_id="lightly_plugins_demo")
    plugin_installer._jobs[job.job_id] = job
    mocker.patch.object(shutil, "which", return_value=None)
    popen = mocker.patch.object(subprocess, "Popen", return_value=_FakeProcess(return_code=0))
    discover = mocker.patch.object(operator_registry, "discover_new_plugins", return_value=["op-1"])

    plugin_installer._run_install(job=job, install_spec="pkg")

    assert job.status == InstallJobStatus.SUCCEEDED
    assert job.new_operator_ids == ["op-1"]
    assert job.log == "Collecting pkg\nInstalled pkg"
    assert job.error_message == ""
    discover.assert_called_once_with()
    assert popen.call_args.args[0][-1] == "pkg"


def test_run_install__installer_fails(mocker: MockerFixture) -> None:
    job = InstallJob(job_id="job-1", plugin_id="lightly_plugins_demo")
    mocker.patch.object(subprocess, "Popen", return_value=_FakeProcess(return_code=1))
    discover = mocker.patch.object(operator_registry, "discover_new_plugins")

    plugin_installer._run_install(job=job, install_spec="pkg")

    assert job.status == InstallJobStatus.FAILED
    assert job.error_message == "The installer exited with code 1."
    discover.assert_not_called()


def test_run_install__no_new_plugins(mocker: MockerFixture) -> None:
    job = InstallJob(job_id="job-1", plugin_id="lightly_plugins_demo")
    mocker.patch.object(subprocess, "Popen", return_value=_FakeProcess(return_code=0))
    mocker.patch.object(operator_registry, "discover_new_plugins", return_value=[])

    plugin_installer._run_install(job=job, install_spec="pkg")

    assert job.status == InstallJobStatus.SUCCEEDED
    assert job.error_message == "The package was installed, but it registered no new plugins."


def test_has_changed_imported_packages(mocker: MockerFixture) -> None:
    mocker.patch.object(
        plugin_installer, "_top_level_modules", side_effect=lambda package_name: {package_name}
    )
    mocker.patch.dict(sys.modules, {"imported": sys})

    # A new package or an unchanged package does not need a restart.
    assert not plugin_installer._has_changed_imported_packages(
        versions_before={"imported": "1.0"}, versions_after={"imported": "1.0", "new": "1.0"}
    )
    # A changed package that is not imported does not need a restart.
    assert not plugin_installer._has_changed_imported_packages(
        versions_before={"not-imported": "1.0"}, versions_after={"not-imported": "2.0"}
    )
    assert plugin_installer._has_changed_imported_packages(
        versions_before={"imported": "1.0"}, versions_after={"imported": "2.0"}
    )


def test_top_level_modules() -> None:
    assert "lightly_studio" in plugin_installer._top_level_modules(package_name="lightly-studio")
    assert plugin_installer._top_level_modules(package_name="does-not-exist") == set()


class _SyncPool:
    def submit(self, fn, **kwargs):  # type: ignore[no-untyped-def]
        fn(**kwargs)


class _FakeProcess:
    def __init__(self, return_code: int) -> None:
        self.stdout = iter(["Collecting pkg\n", "Installed pkg\n"])
        self._return_code = return_code

    def __enter__(self) -> _FakeProcess:
        return self

    def __exit__(self, *args: object) -> None:
        pass

    def wait(self) -> int:
        return self._return_code
