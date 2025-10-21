"""Export OpenAPI schema from FastAPI application to JSON file."""

import argparse
import json

from lightly_studio.api.app import app

parser = argparse.ArgumentParser(description="Export OpenAPI schema to a file.")
parser.add_argument(
    "--output",
    type=str,
    default="openapi.json",
    help="The output file path for the OpenAPI schema (default: openapi.json).",
)
args = parser.parse_args()

with open(args.output, "w") as f:
    json.dump(app.openapi(), f, indent=2)
