---
name: glossary
description: Read when naming anything user-facing - GUI text, docs, public Python API names, arguments, docstrings, or error messages. Gives the approved LightlyStudio term for each concept and the wording to avoid, currently covering annotations, annotation classes, annotation sources, labeling, and ingestion.
---

# Glossary and Naming

Terminology for LightlyStudio.

Use the **Term** for all user-facing parts: the GUI, the docs, and the public Python API (names, arguments, docstrings, and error messages).
Internal implementation names (database tables and columns, resolvers, REST JSON fields, and the
generated frontend client) are exempt.

Add new topics as their own `##` section below.

## Annotations

| Concept | Term | Python identifier | Avoid |
|---|---|---|---|
| A classification, object-detection box, or segmentation mask attached to a sample | **annotation** | - | label, annotation label |
| The category of an annotation, e.g. `"dog"`, `"cat"` | **annotation class** | `class_name` | label, label class, annotation label |
| A group of annotations, e.g. ground truth, a model's predictions | **annotation source** | `annotation_source` | annotation collection, collection, collection name, label source |
| Creating annotations | **labeling** | - | the noun 'label' |

## Data ingestion

| Concept | Term | Avoid |
|---|---|---|
| Images added without any annotations | **raw images** | image folder, unlabeled images |
| Videos added without any annotations | **raw videos** | video folder |
| Adding samples to a dataset, for example with `add_images_from_path` | **ingestion** (verb: ingest) | import |

"Import" clashes with Python `import` in nearby code blocks, so avoid it for adding samples.
Exception: loading an external annotation format such as COCO, YOLO, or Label Studio is an
**import**, also when it creates samples, for example `add_samples_from_coco` or
`add_annotations_from_*`.

