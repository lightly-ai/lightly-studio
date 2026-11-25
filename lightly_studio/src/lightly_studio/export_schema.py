"""Export OpenAPI schema from FastAPI application to JSON file."""

import argparse
import json
from typing import Any

from lightly_studio.api.app import app


def _mark_file_uploads_as_binary(schema: Any) -> None:
    """Replaces `contentMediaType` of file uploads with `format: binary` in place.

    Newer FastAPI versions mark file uploads with `contentMediaType`. The frontend client
    generator types such fields as `string`. With `format: binary`, it types them as files.
    """
    if isinstance(schema, dict):
        if schema.get("contentMediaType") == "application/octet-stream":
            del schema["contentMediaType"]
            schema["format"] = "binary"
        for value in schema.values():
            _mark_file_uploads_as_binary(schema=value)
    elif isinstance(schema, list):
        for value in schema:
            _mark_file_uploads_as_binary(schema=value)


parser = argparse.ArgumentParser(description="Export OpenAPI schema to a file.")
parser.add_argument(
    "--output",
    type=str,
    default="openapi.json",
    help="The output file path for the OpenAPI schema (default: openapi.json).",
)
args = parser.parse_args()

openapi_schema = app.openapi()
_mark_file_uploads_as_binary(schema=openapi_schema)
with open(args.output, "w") as f:
    json.dump(openapi_schema, f, indent=2)
