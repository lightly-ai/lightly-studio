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

