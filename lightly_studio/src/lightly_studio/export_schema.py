"""Export OpenAPI schema from FastAPI application to JSON file."""

import argparse
import hashlib
import importlib
import json
import shutil
from pathlib import Path


def main() -> None:
    """Export the OpenAPI schema when the command line is invoked."""
    parser = argparse.ArgumentParser(description="Export OpenAPI schema to a file.")
    parser.add_argument(
        "--output",
        type=str,
        default="openapi.json",
        help="The output file path for the OpenAPI schema (default: openapi.json).",
    )
    parser.add_argument(
        "--if-changed",
        action="store_true",
        help="Skip exporting when backend sources and dependencies are unchanged.",
    )
    args = parser.parse_args()
    output_path = Path(args.output)
    backend_root = Path(__file__).resolve().parents[2]
    cache_path = output_path.with_name(f".{output_path.name}.signature")

    signature = _get_signature(backend_root=backend_root)
    if args.if_changed:
        if output_path.exists() and cache_path.exists() and cache_path.read_text() == signature:
            print("OpenAPI schema is up to date.")
            return
        print("Exporting OpenAPI schema...")

    cache_path.unlink(missing_ok=True)
    _write_schema(output_path=output_path, backend_root=backend_root)
    cache_path.write_text(signature)


def _get_signature(backend_root: Path) -> str:
    """Return a digest of backend source and dependency files."""
    digest = hashlib.sha256()
    for path in sorted((backend_root / "src/lightly_studio").rglob("*.py")):
        digest.update(str(path.relative_to(backend_root)).encode())
        digest.update(path.read_bytes())
    for name in ("pyproject.toml", "uv.lock"):
        path = backend_root / name
        if path.exists():
            digest.update(name.encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _write_schema(output_path: Path, backend_root: Path) -> None:
    """Write the app's OpenAPI schema and remove a temporary UI stub."""
    dist_path = backend_root / "src/lightly_studio/dist_lightly_studio_view_app"
    created_stub = not dist_path.exists()
    if created_stub:
        dist_path.mkdir(parents=True)
        (dist_path / "index.html").touch()

    try:
        app = importlib.import_module("lightly_studio.api.app").app

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w") as file:
            json.dump(app.openapi(), file, indent=2)
    finally:
        if created_stub:
            shutil.rmtree(dist_path)


if __name__ == "__main__":
    main()
