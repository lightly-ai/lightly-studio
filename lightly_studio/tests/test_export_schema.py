"""Tests for the OpenAPI schema export command."""

import json
import sys
import types
from pathlib import Path

import pytest

from lightly_studio import export_schema


def test_get_signature_includes_source_and_existing_dependency_files(
    tmp_path: Path,
) -> None:
    source = tmp_path / "src/lightly_studio/example.py"
    source.parent.mkdir(parents=True)
    source.write_text("source")
    (tmp_path / "pyproject.toml").write_text("project")

    signature = export_schema._get_signature(backend_root=tmp_path)

    assert len(signature) == 64
    assert signature == export_schema._get_signature(backend_root=tmp_path)
    source.write_text("changed")
    assert signature != export_schema._get_signature(backend_root=tmp_path)


def test_main_skips_export_when_signature_is_current(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_path = tmp_path / "openapi.json"
    output_path.write_text("existing")
    signature = "current-signature"
    output_path.with_name(".openapi.json.signature").write_text(signature)
    monkeypatch.setattr(
        sys, "argv", ["export_schema.py", "--output", str(output_path), "--if-changed"]
    )
    monkeypatch.setattr(
        Path,
        "resolve",
        lambda _self: tmp_path / "src/lightly_studio/export_schema.py",
    )
    monkeypatch.setattr(export_schema, "_get_signature", lambda **_kwargs: signature)
    monkeypatch.setattr(
        export_schema, "_write_schema", lambda **_kwargs: pytest.fail("should skip")
    )

    export_schema.main()

    assert output_path.read_text() == "existing"


def test_main_exports_and_caches_signature_when_changed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_path = tmp_path / "openapi.json"
    signature = "new-signature"
    monkeypatch.setattr(
        sys, "argv", ["export_schema.py", "--output", str(output_path), "--if-changed"]
    )
    monkeypatch.setattr(
        Path,
        "resolve",
        lambda _self: tmp_path / "src/lightly_studio/export_schema.py",
    )
    monkeypatch.setattr(export_schema, "_get_signature", lambda **_kwargs: signature)
    monkeypatch.setattr(export_schema, "_write_schema", lambda **_kwargs: None)

    export_schema.main()

    assert output_path.with_name(".openapi.json.signature").read_text() == signature


def test_main_refreshes_signature_for_unconditional_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_path = tmp_path / "openapi.json"
    cache_path = output_path.with_name(".openapi.json.signature")
    cache_path.write_text("old-signature")
    signature = "new-signature"
    monkeypatch.setattr(sys, "argv", ["export_schema.py", "--output", str(output_path)])
    monkeypatch.setattr(
        Path,
        "resolve",
        lambda _self: tmp_path / "src/lightly_studio/export_schema.py",
    )
    monkeypatch.setattr(export_schema, "_get_signature", lambda **_kwargs: signature)
    monkeypatch.setattr(export_schema, "_write_schema", lambda **_kwargs: None)

    export_schema.main()

    assert cache_path.read_text() == signature


def test_main_removes_signature_when_export_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_path = tmp_path / "openapi.json"
    cache_path = output_path.with_name(".openapi.json.signature")
    cache_path.write_text("old-signature")
    monkeypatch.setattr(sys, "argv", ["export_schema.py", "--output", str(output_path)])
    monkeypatch.setattr(
        Path,
        "resolve",
        lambda _self: tmp_path / "src/lightly_studio/export_schema.py",
    )
    monkeypatch.setattr(export_schema, "_get_signature", lambda **_kwargs: "new-signature")

    def fail_write_schema(**_kwargs: object) -> None:
        raise ValueError("failed")

    monkeypatch.setattr(export_schema, "_write_schema", fail_write_schema)

    with pytest.raises(ValueError, match="failed"):
        export_schema.main()

    assert not cache_path.exists()


def test_write_schema_creates_output_and_removes_temporary_stub(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend_root = tmp_path / "backend"
    output_path = tmp_path / "nested/openapi.json"
    app_module = types.ModuleType("lightly_studio.api.app")
    app_module.__dict__["app"] = types.SimpleNamespace(openapi=lambda: {"openapi": "3.1.0"})
    monkeypatch.setitem(sys.modules, "lightly_studio.api.app", app_module)

    export_schema._write_schema(output_path=output_path, backend_root=backend_root)

    assert json.loads(output_path.read_text()) == {"openapi": "3.1.0"}
    assert not (backend_root / "src/lightly_studio/dist_lightly_studio_view_app").exists()


def test_write_schema_preserves_existing_ui_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend_root = tmp_path / "backend"
    dist_path = backend_root / "src/lightly_studio/dist_lightly_studio_view_app"
    dist_path.mkdir(parents=True)
    (dist_path / "index.html").write_text("built app")
    app_module = types.ModuleType("lightly_studio.api.app")
    app_module.__dict__["app"] = types.SimpleNamespace(openapi=dict)
    monkeypatch.setitem(sys.modules, "lightly_studio.api.app", app_module)

    export_schema._write_schema(output_path=tmp_path / "openapi.json", backend_root=backend_root)

    assert (dist_path / "index.html").read_text() == "built app"


def test_write_schema_removes_temporary_stub_after_export_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend_root = tmp_path / "backend"
    app_module = types.ModuleType("lightly_studio.api.app")
    app_module.__dict__["app"] = types.SimpleNamespace(
        openapi=lambda: (_ for _ in ()).throw(ValueError("failed"))
    )
    monkeypatch.setitem(sys.modules, "lightly_studio.api.app", app_module)

    with pytest.raises(ValueError, match="failed"):
        export_schema._write_schema(
            output_path=tmp_path / "openapi.json", backend_root=backend_root
        )

    assert not (backend_root / "src/lightly_studio/dist_lightly_studio_view_app").exists()
