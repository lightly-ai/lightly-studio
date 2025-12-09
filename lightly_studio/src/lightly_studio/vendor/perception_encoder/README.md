# PerceptionEncoder

Trimmed down version of PerceptionEncoder-Core.

Changes:

- removed DropPath and hence the dependency to timm inside `pe.py`
- adjusted imports to match this repository
- added `model_path` as return value to the `form_config` in `pe.py`

Vendored from https://github.com/facebookresearch/perception_models, commit 430a012.
