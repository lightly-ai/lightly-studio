# Glossary and Naming

Canonical terminology for LightlyStudio. Use the **Term** in every user-facing surface — the GUI, the
docs, and the public Python API (names, arguments, docstrings, and error messages). The **Avoid** column
lists wording that must not appear in those surfaces.

Internal implementation names (database tables and columns, resolvers, REST JSON fields, and the
generated frontend client) are exempt and keep their existing spelling — do not rename them mechanically.

Add new topics as their own `##` section below.

## Annotations

> **Migration in progress (LIG-9649):** the rename lands across several PRs. Until they all merge, a few public surfaces still use the old terms and are temporarily exempt — the query-DSL field `label` (→ `class_name`) and the `add_annotations_from_*` `name` argument with its "annotation collection" docstrings (→ `annotation_source`).

| Concept | Term | Python identifier | Avoid |
|---|---|---|---|
| A classification, object-detection box, or segmentation mask attached to a sample | **annotation** | — | label, annotation label |
| The category of an annotation, e.g. `"dog"`, `"cat"` | **annotation class** | `class_name` | label, label class, annotation label |
| The named origin grouping annotations, e.g. ground truth, a model's predictions, or an annotator | **annotation source** | `annotation_source` | annotation collection, collection, bare "name", collection name, label source |

**Labeling** — the process of a human creating annotations — stays as-is (e.g. "labeling workflow",
"auto-labeling"). Only the *noun* "label" is replaced by "annotation" / "annotation class".

Exempt internal names for this topic: `annotation_label`, `annotation_label_name`, `annotation_label_id`,
`annotation_collection_id`, `annotation_collection_coverage`, `collection.name`, the `*_resolver` modules,
and the `collection_name` parameter of internal `add_annotations` helpers.
