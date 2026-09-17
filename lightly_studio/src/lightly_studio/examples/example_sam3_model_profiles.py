"""Show how an inference server can expose more than one SAM3 checkpoint.

The server process should select one profile at startup, then echo its ``model_key`` from
``/v1/describe`` and use the profile's checkpoint when constructing the SAM3 adapter.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SAM3ModelProfile:
    """Configuration for one model offered by the inference server."""

    model_key: str
    checkpoint: str
    device: str


MODEL_PROFILES: dict[str, SAM3ModelProfile] = {
    "sam3/local": SAM3ModelProfile(
        model_key="sam3/local",
        checkpoint="checkpoints/sam3.pt",
        device="cuda",
    ),
    # Add another available model by adding a profile with a unique model_key.
    "sam3/quality": SAM3ModelProfile(
        model_key="sam3/quality",
        checkpoint="checkpoints/sam3-quality.pt",
        device="cuda",
    ),
}


def get_selected_profile(model_key: str | None = None) -> SAM3ModelProfile:
    """Resolve the profile selected by ``SAM3_MODEL_KEY`` or the CLI argument."""
    selected_key = model_key or os.environ.get("SAM3_MODEL_KEY", "sam3/local")
    try:
        return MODEL_PROFILES[selected_key]
    except KeyError as exc:
        available = ", ".join(sorted(MODEL_PROFILES))
        raise ValueError(
            f"Unknown SAM3_MODEL_KEY {selected_key!r}; choose one of: {available}"
        ) from exc


def describe(profile: SAM3ModelProfile) -> dict[str, object]:
    """Build the descriptor body returned by ``GET /v1/describe``."""
    return {
        "protocol_version": "1.0",
        "model_key": profile.model_key,
        "ready": True,
        "capabilities": ["segmentation_image_bytes", "object_detection_image_bytes"],
        "supported_conditioning": ["targets", "points", "boxes"],
        "limits": {"max_batch_size": 8, "max_request_bytes": 33_554_432},
    }


def main() -> None:
    """Print the selected SAM3 profile and its protocol descriptor."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-key", default=None)
    args = parser.parse_args()
    profile = get_selected_profile(model_key=args.model_key)
    print(json.dumps({"profile": asdict(profile), "describe": describe(profile)}, indent=2))


if __name__ == "__main__":
    main()
