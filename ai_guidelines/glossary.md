# Glossary and Naming

These terms are canonical across all **user-facing** surfaces: the GUI, the docs, and the public Python API
(names, arguments, docstrings, and error messages). Use them consistently and avoid the forbidden alternatives.

| Concept | Term to use | Python identifier | Do **not** call it |
|---|---|---|---|
| A single piece of data attached to a sample: a classification, an object-detection bounding box, or a segmentation mask. | **annotation** | — | "label", "annotation label" |
| The category of an annotation, e.g. `"dog"`, `"cat"`. | **annotation class** | `class_name` | "label", "label class", "annotation label" |
| The named origin that groups annotations from one provider, e.g. ground truth, a model's predictions, or an annotator. | **annotation source** | `annotation_source` | "annotation collection", "collection", a bare "name", "collection name" |

## Forbidden user-facing terms

Do not use any of these in the GUI, docs, public Python API, or error messages: **"label"**, **"annotation label"**,
**"label class"**, **"label source"**, **"annotation collection"**, or **"collection name"** (when referring to an
annotation source).

## Exempt (internal) names

Internal implementation names are intentionally exempt and keep their existing spelling. Do **not** mechanically
rename them:

- Database tables/columns, e.g. `annotation_label`, `annotation_label_name`, `annotation_label_id`,
  `annotation_collection_id`, `annotation_collection_coverage`, and `collection.name`.
- Resolvers and internal helpers, e.g. `annotation_label_resolver`, `annotation_collection_coverage_resolver`,
  and the `collection_name` parameter of internal `add_annotations` helpers.
- REST endpoint paths and JSON field names, and the generated frontend API client (`*.gen.ts`).
