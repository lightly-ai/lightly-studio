"""Export the default browser auto-labeling model to ONNX.

Run from the repository root:

    uv run --no-project --python 3.12 --with lightly-train --with onnx --with onnxslim --with onnxscript --with onnxruntime python .experimental/browser-auto-labeling/export_model.py
"""

from __future__ import annotations

from pathlib import Path

import lightly_train  # type: ignore[import-not-found]

MODEL_NAME = "ltdetrv2-s-coco"
OUTPUT_PATH = Path("lightly_studio_view/static/models") / f"{MODEL_NAME}.onnx"
BYTES_PER_MB = 1_000_000


def main() -> None:
    """Export the model with a fixed batch size of 1, as the browser runs one image at a time."""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    model = lightly_train.load_model(MODEL_NAME)
    model.export_onnx(OUTPUT_PATH, precision="fp32", dynamic_batch_size=False)
    print(f"Wrote {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size / BYTES_PER_MB:.1f} MB)")


if __name__ == "__main__":
    main()
