# Optional built-in embedding models (drop torch from the base install)

## Intent

`torch` and related packages are core dependencies of `lightly-studio`, but only the two built-in
embedding models (MobileCLIP and Perception Encoder) use them. They are heavy, especially on
Linux, where PyPI serves the CUDA build of `torch`. Developers have a workaround to get the CPU
build; users and deployments get the full stack.

We move these packages to an optional extra, `lightly-studio[builtin-models]`. Who benefits:

1. **Our CI.** Most jobs install and run faster.
2. **Our enterprise deployment.** A smaller image, later. It uses the built-in models today, so it
   keeps the extra until it moves to an embedding service (separate project).
3. **Users with custom or remote embedders.** They no longer install a model stack they do not use.

**Why an extra and not an opt-out:** pip cannot skip a package's dependency, and installers do
not support default extras (PEP 771). A split into `lightly-studio-core` plus `lightly-studio`
would give a real opt-out, but costs a second package to publish and version.

## Goals

- `pip install lightly-studio` does not install `torch`, `torchvision`, `open-clip-torch` (with
  its transitive `timm`, `huggingface-hub`, `ftfy`, `regex`, `safetensors`), or `einops`.
- `pip install "lightly-studio[builtin-models]"` behaves as today.
- Without the extra, everything else works: import, dataset loading, the GUI, custom and remote
  embedders. Only the built-in models are missing.
- When the backend would have used a built-in model but the extra is missing, it logs a warning
  that names the extra and the install command.

## Non-goals

- **Frontend changes.** Without embeddings the frontend hides embedding features silently, as
  today. A follow-up will show them as disabled, with a link to a docs page that lists every
  reason for missing embeddings. It must not guess the reason, because there are many.
- **Splitting the `has_embeddings` gate.** One gate controls features with different needs: the
  plot and sampling need only stored embeddings, text search needs a loaded embedder. The split is
  a follow-up, done before the frontend one, which depends on it.
- A two-package split or any other opt-out.
- Changes to custom or remote embedder APIs.

## Anti-goals

- An `ImportError` or crash from `import lightly_studio` or any lightly-studio code path without
  the extra. Modules whose purpose is torch may need torch to import (see "Public torch helpers").
- A moved package staying in the core by accident as a transitive dependency.
- Reporting a broken install (torch present but failing to import) as "extra missing".

## Current state

- The registry imports the built-in models lazily, but nothing catches an import failure. Without
  torch today, ingestion crashes and text search answers 500. A failed load is not cached, so
  every call retries the import.
- When the registry returns a `NoEmbedderReason`, embedding is skipped with a log, and
  `has_embeddings` hides the features. The existing messages do not name the extra.
- `embed/image_embedding.py` and `embed/image_crop_embedding.py` import `torch` at module level.
  The LightlyTrain tutorial and two examples import them directly.
- The `cpu`/`gpu` dependency groups and the `pytorch-cpu` uv source pick the torch build for
  development (CONTRIBUTING.md, "GPU Torch on Linux").

## Decisions

- **Extra name `builtin-models`.** It says what you get and matches the code
  (`preload_builtin_embedders`). Rejected:
  - `default-models`: "default model" already means a collection's default embedding model, which
    can be a custom embedder.
  - `embeddings`: custom and remote embedders give embeddings without it.
- **Extra contents:** `torch`, `torchvision`, `open-clip-torch`, `einops`, with current pins and
  markers. `scikit-learn`, `scipy`, and `lightly-mundig` stay in the core: they are used outside
  the models and do not need torch.
- **Without the extra:** skip embedding and log a warning, do not raise. Exception:
  `preload_builtin_embedders()` raises. Enterprise calls it to warm the model cache, so an image
  built without the extra by mistake fails instead of shipping without embeddings.
- **Datasets embedded earlier, opened without the extra:** a known gap until the gate split. The
  features stay visible; the plot and sampling work on stored embeddings; text search answers 409
  with the install hint. New samples are not embedded.
- **Upgrade path:** a plain `pip install -U lightly-studio` drops the built-in models. A changelog
  entry and a major version bump are enough.
- **Docs:** install instructions (quickstart, README, ...) use
  `pip install "lightly-studio[builtin-models]"` and explain when to leave the extra out. Examples
  and tutorials say what they need: the extra if they use the built-in models (for example
  `example_custom_embedding_model.py`, the epic-kitchens tutorial), only torch if they don't (the
  LightlyTrain ones, where `lightly-train` brings torch).

## How

- **Subpackage `lightly_studio/builtin_models/`.** The two built-in embedders and `vendor/` move
  into it. A later split into its own distribution is then a folder move.
- **Detection in `builtin_models/__init__.py`**, which imports no torch:
  - `is_installed()` runs `importlib.util.find_spec` on the extra's packages and is cached with
    `functools.cache`. It logs the warning on the first miss, so the warning shows once per
    process. `find_spec` does not import, so a broken install still fails loudly.
  - The install hint is written once, for the warning, the 409 message, and the preload error.
- **Registry.** Before the lazy import, it calls `is_installed()`. Without the extra it returns a
  new `NoEmbedderReason` (for example `BUILTIN_MODELS_NOT_INSTALLED`), and the callers skip or
  answer 409 as for the other reasons.
- **Lint rule.** Ruff `TID253` bans module-level imports of `torch`, `torchvision`, `open_clip`,
  `timm`, and `einops`, except in `builtin_models/` and the public torch helpers. Tests that need
  the models import them inside the test.
- **Public torch helpers stay.** `embed/image_embedding.py` and `embed/image_crop_embedding.py`
  keep their module-level `torch` import and their import paths, which the docs use. They exist to
  write torch embedders, so `No module named 'torch'` is the right error.

## Left to the builder

- Exact warning wording. Use the glossary skill.
- How the extra fits with the dev environment and the `cpu`/`gpu` groups. Developers get the
  extra by default, so the full test suite runs locally as today.
- CI layout. At least one job installs without the extra and checks that import and dataset
  loading work and log the warning. The tests that need the models run in a job with the extra.
  How to mark or skip them is your call.
- Whether the enterprise image needs changes in this repo or only in its own build.
