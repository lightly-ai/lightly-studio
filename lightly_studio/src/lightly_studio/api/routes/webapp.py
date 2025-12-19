"""This module contains the API routes for managing collections."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from .api.status import HTTP_STATUS_NOT_FOUND

app_router = APIRouter()

# Get the current project root directory
project_root = Path(__file__).resolve().parent.parent.parent

webapp_dir = project_root / "dist_lightly_studio_view_app"

# Check if the webapp directory exists and raise an error if it doesn't
if not webapp_dir.exists():
    raise RuntimeError(f"Directory '{webapp_dir}' does not exist in '{project_root}'")

# Ensure the path is absolute
webapp_dir = webapp_dir.resolve()

# ensure the webapp index.html file exists
index_file = webapp_dir / "index.html"
if not index_file.exists():
    raise RuntimeError("No index file. Did you forget to build the webapp?")


@app_router.get("/{path:path}", include_in_schema=False)
async def serve_static_webapp_files_or_default_index_file(
    path: str,
) -> FileResponse:
    """Serve static files of webapp or serve the index.html file.

    Try to serve static files with file extensions or return 404.
    If no file extension, return the main webapp index.html.
    """
    file_path = webapp_dir / path

    # if file has an extension, try to return the file
    if file_path.suffix:
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(
                status_code=HTTP_STATUS_NOT_FOUND,
                detail=f"File '{path}' not found",
            )
        return FileResponse(file_path)

    # if file has no extension, return the index.html file regardless of path
    return FileResponse(index_file)
