# Implementation Plan: Query Language (Prototype)

## Context

Users need to filter images/samples using complex boolean conditions and subqueries from the GUI. This is a **prototype** — focus on getting a working end-to-end demo, skip tests and polish.

**Agreed design:**
- Lark text DSL (backend) → Pydantic AST → existing `MatchExpression` → SQLAlchemy
- CodeMirror 6 + Lezer grammar (frontend) with schema-driven autocomplete
- New `/query` endpoint (existing endpoints untouched)
- Subqueries (`has_tag`, `has_annotation`) from day 1

---

## Step 1: Backend — Grammar, Parser, AST, Compiler (single step) ✅ DONE

**Goal:** Full backend pipeline: text → parse → AST → MatchExpression → SQL.

**Create:**
- `lightly_studio/src/lightly_studio/core/query_language/__init__.py`
- `lightly_studio/src/lightly_studio/core/query_language/grammar.lark`
- `lightly_studio/src/lightly_studio/core/query_language/parser.py`
- `lightly_studio/src/lightly_studio/core/query_language/ast_nodes.py`
- `lightly_studio/src/lightly_studio/core/query_language/transformer.py`
- `lightly_studio/src/lightly_studio/core/query_language/field_registry.py`
- `lightly_studio/src/lightly_studio/core/query_language/compiler.py`

**Modify:**
- `lightly_studio/pyproject.toml` — add `"lark>=1.2.0,<2.0"` to dependencies

**Details:**

`grammar.lark`:
```
?query: or_expr
?or_expr: and_expr ("or"i and_expr)*   -> or_expr
?and_expr: not_expr ("and"i not_expr)* -> and_expr
?not_expr: "not"i not_expr            -> not_expr
         | atom
?atom: "(" query ")" | subquery | comparison
comparison: field_ref CMP_OP value
subquery: "has_tag"i "(" STRING ")"           -> has_tag
        | "has_annotation"i "(" query ")"     -> has_annotation
field_ref: FIELD_NAME ("." FIELD_NAME)*
FIELD_NAME: /[a-zA-Z_][a-zA-Z0-9_]*/
CMP_OP: ">=" | "<=" | "!=" | "==" | ">" | "<" | "contains"i | "in"i
?value: STRING | SIGNED_NUMBER | BOOL | list_value
BOOL: "true"i | "false"i
list_value: "[" value ("," value)* "]"
%import common.ESCAPED_STRING -> STRING
%import common.SIGNED_NUMBER
%import common.WS
%ignore WS
```

`ast_nodes.py` — Pydantic discriminated union:
- `ComparisonNode(field: FieldRef, operator: str, value: ...)`
- `AndNode(children: list[QueryNode])`, `OrNode(children: list[QueryNode])`, `NotNode(child: QueryNode)`
- `HasTagNode(tag_name: str)`, `HasAnnotationNode(inner: QueryNode)`
- `QueryNode = Annotated[Union[...], Field(discriminator="node_type")]`

`transformer.py` — Lark `Transformer` mapping tree → AST nodes. Flatten single-child AND/OR.

`field_registry.py`:
- `FieldRegistry` maps string names → `FieldInfo(name, type, operators, field_object)`
- Image fields from `ImageSampleField` (width, height, file_name, file_path_abs, created_at)
- `metadata.<key>` → `db_json.json_extract` pattern from `metadata_filter.py`
- Annotation subcontext for fields inside `has_annotation(...)`
- `resolve(field_ref, context)` → `FieldInfo` or raises error
- `get_schema()` → serializable catalogue for the schema endpoint

`compiler.py`:
- `compile(node, registry, context="sample") -> MatchExpression`
- `ComparisonNode` → field operator overload → `OrdinalFieldExpression` / `ComparableFieldExpression`
- `AndNode` → `AND(...)`, `OrNode` → `OR(...)`, `NotNode` → `NOT(...)`
- `HasTagNode` → `TagsAccessor().contains(tag_name)`
- `HasAnnotationNode` → subquery pattern from `AnnotationsFilter.apply_to_parent_sample_query`

Top-level function: `execute_query(text: str, session: Session, collection_id: UUID, sample_type: SampleType, pagination: Paginated | None) -> tuple[list, int]`

**Key files to read:**
- `lightly_studio/core/dataset_query/boolean_expression.py` — AND/OR/NOT
- `lightly_studio/core/dataset_query/field_expression.py` — leaf expressions
- `lightly_studio/core/dataset_query/image_sample_field.py` — field catalogue
- `lightly_studio/core/dataset_query/tags_expression.py` — TagsAccessor
- `lightly_studio/resolvers/annotations/annotations_filter.py` — subquery pattern
- `lightly_studio/resolvers/metadata_resolver/metadata_filter.py` — metadata handling
- `lightly_studio/resolvers/image_resolver/` — how image queries are currently built

**Acceptance:** `parse_to_ast("width > 100 and has_tag(\"train\") or has_annotation(label == \"cat\")")` → AST → `MatchExpression` → valid SQLAlchemy expression.

**Learnings / diversions from plan (relevant for next steps):**

- **`compile` renamed to `compile_ast`** to avoid shadowing the Python builtin `compile`. Update any references in Step 2 accordingly.

- **Metadata fields skipped** — the plan listed `metadata.<key>` support in `FieldRegistry`. This was intentionally deferred: metadata requires a JOIN on `SampleMetadataTable` at the query level (not just a `ColumnElement`), which doesn't fit the `MatchExpression.get() → ColumnElement[bool]` contract. Step 2 can add metadata support by either extending `MatchExpression` or handling it as a query modifier outside the compiler.

- **`has_annotation` uses a simple IN-subquery, not `AnnotationsFilter`** — the plan suggested reusing `AnnotationsFilter.apply_to_parent_sample_query`. Instead, the compiler builds the subquery inline: `SELECT DISTINCT parent_sample_id FROM annotation_base JOIN annotation_label WHERE <inner_condition>`. This is simpler and sufficient for the `label == "..."` use case. The annotation context currently only exposes the `label` field (`annotation_label.annotation_label_name`).

- **`uv.lock` must be updated** — after adding `lark` to `pyproject.toml`, `uv lock` was needed before `make static-checks` would pass (`uv lock --check` fails otherwise).

- **`execute_query` does not eager-load relationships** — unlike `get_all_by_collection_id`, the `execute_query` helper in `__init__.py` does not call `_get_load_options()` (which loads tags, annotations, captions, metadata). Step 2 should integrate with the existing image resolver's `get_all_by_collection_id` (or its internal query builder) rather than using `execute_query` directly, to get the full `ImageViewsWithCount` response shape with all relationships loaded.

- **`sample_type` parameter is a no-op** — `execute_query` accepts `sample_type: SampleType` for API compatibility but always queries `ImageTable`. Video support would require additional routing logic.

---

## Step 2: Backend — API Endpoints ✅ DONE

**Goal:** Expose the query language over HTTP.

**Create:**
- `lightly_studio/src/lightly_studio/api/routes/api/query_language.py`

**Modify:**
- `lightly_studio/src/lightly_studio/api/app.py` — import + `api_router.include_router(query_language.query_language_router)`

**Endpoints:**

1. **`POST /collections/{collection_id}/images/query`**
   - Body: `{"text": "width > 100", "pagination": {"offset": 0, "limit": 50}}`
   - Returns: `ImageViewsWithCount` (same shape as existing `/images/list`)
   - Implementation: parse → compile → execute using existing image resolver query patterns

2. **`POST /collections/{collection_id}/query/validate`**
   - Body: `{"text": "width >"}`
   - Returns: `{"diagnostics": [{"start": 8, "end": 8, "message": "Unexpected end of input", "severity": "error"}]}`
   - Uses `parse_with_errors` + field registry validation

3. **`GET /collections/{collection_id}/query-schema`**
   - Returns: `{"fields": [...], "subcontexts": {"annotation": [...]}}`
   - Each field: `{"name": "width", "field_type": "number", "operators": [">","<",">=","<=","==","!="]}`
   - Reuse `get_dimension_bounds` for numeric bounds, `get_metadata_info` for metadata fields

4. **`POST /collections/{collection_id}/query-suggest`**
   - Body: `{"field": "tags", "prefix": "tr", "limit": 20}`
   - Returns: `{"values": ["train", "training"]}`
   - Query `TagTable`, `AnnotationLabelTable`, or metadata values

**Key files to read:**
- `lightly_studio/api/routes/api/image.py` — route pattern (especially `read_images`)
- `lightly_studio/api/routes/api/sample.py` — request/response model pattern
- `lightly_studio/api/app.py` — router registration (imports ~line 24-46, includes ~line 134-156)
- `lightly_studio/resolvers/image_resolver/` — query execution pattern

**Acceptance:** `curl -X POST .../images/query -d '{"text":"width > 500"}'` returns filtered images. `make export-schema` succeeds.

**Learnings / diversions from plan:**

- **`_get_load_options` and `_compute_next_cursor` imported from internal module** — rather than restructuring the resolver, the route handler directly imports these private helpers from `get_all_by_collection_id.py`. Works fine for a prototype.

- **`suggest_values` uses `Depends(get_and_validate_collection_id)` without a separate `Path`** — FastAPI resolves the `collection_id` path param automatically through the dependency; no need to declare it separately in the function signature.

- **Lark's LALR parser emits `UnexpectedToken` for most errors** — the diagnostic converter handles `UnexpectedToken` (including `$END` for EOF), `UnexpectedCharacters`, and `UnexpectedEOF`. Position is taken from `token.start_pos` (0-based char offset in the input string).

---

## Step 3: Frontend — CodeMirror Editor with Autocomplete

**Goal:** Full frontend: Lezer grammar, CodeMirror component with autocomplete and lint, integrated into samples page.

**Install:**
```bash
cd lightly_studio_view
npm install @codemirror/state @codemirror/view @codemirror/autocomplete @codemirror/lint @codemirror/language @lezer/lr @lezer/highlight
npm install -D @lezer/generator
```

**Create:**
- `lightly_studio_view/src/lib/components/QueryEditor/query-language.grammar` — Lezer grammar (mirrors Lark)
- `lightly_studio_view/src/lib/components/QueryEditor/query-language.ts` — language definition
- `lightly_studio_view/src/lib/components/QueryEditor/QueryEditor.svelte` — CodeMirror mount
- `lightly_studio_view/src/lib/components/QueryEditor/completionSource.ts` — autocomplete
- `lightly_studio_view/src/lib/components/QueryEditor/lintSource.ts` — backend validation
- `lightly_studio_view/src/lib/hooks/useQuerySchema/useQuerySchema.ts` — schema hook

**Modify:**
- `lightly_studio_view/package.json` — add `build:grammar` script, wire into `predev`/`prebuild`
- `lightly_studio_view/src/lib/components/GridHeader/GridHeader.svelte` — add QueryEditor
- Relevant parent components to pass `collectionId` and wire query execution

**Details:**

Lezer grammar mirrors Lark (same productions):
```
@top Query { expression }
expression { OrExpr }
OrExpr { AndExpr ("or" AndExpr)* }
AndExpr { NotExpr ("and" NotExpr)* }
NotExpr { kw<"not"> NotExpr | Atom }
Atom { "(" expression ")" | HasTag | HasAnnotation | Comparison }
Comparison { FieldRef CompOp Value }
HasTag { kw<"has_tag"> "(" String ")" }
HasAnnotation { kw<"has_annotation"> "(" expression ")" }
FieldRef { identifier ("." identifier)* }
// ... tokens
```

`QueryEditor.svelte`:
- Lazy-load CodeMirror via dynamic `import()` in `onMount`
- Props: `collectionId: string`, `onExecute: (text: string) => void`
- Style: compact, single-line expanding, matches app design (Tailwind)
- Bind to `?q=` URL param for persistence

`completionSource.ts`:
- Read Lezer syntax tree at cursor
- Field position → suggest field names from schema
- Operator position → suggest operators for field type
- Value position → inline enums or debounced `/query-suggest`
- Inside `has_annotation(...)` → switch to annotation field catalogue

`lintSource.ts`:
- Debounced (300ms) POST to `/query/validate`
- Map response diagnostics to CodeMirror `Diagnostic[]`

`useQuerySchema.ts`:
- `createQuery` from `@tanstack/svelte-query`
- Fetches `/query-schema`, caches per collection

Integration into samples page:
- Add `QueryEditor` to `GridHeader`
- On submit, call `/images/query` with the text
- Results drive the image grid (same `ImageViewsWithCount` shape)
- Clear query → revert to default view

**Key files to read:**
- `lightly_studio_view/package.json` — scripts, deps
- `lightly_studio_view/src/lib/components/GridHeader/GridHeader.svelte`
- `lightly_studio_view/src/lib/hooks/useImageFilters/useImageFilters.ts` — hook pattern
- `lightly_studio_view/src/lib/hooks/useImagesInfinite/useImagesInfinite.ts` — grid data loading
- `lightly_studio_view/src/routes/datasets/[dataset_id]/[collection_type]/[collection_id]/samples/+page.svelte`
- `ai_guidelines/frontend.md` — conventions

**Acceptance:** Type `width > 1024 and has_tag("train")` in the editor on the samples page → grid updates. Autocomplete suggests fields and operators. Errors show inline.

---

## Dependency Graph

```
Step 1 (Backend core)  ──→  Step 2 (API endpoints)  ──→  Step 3 (Frontend)
                        ╲                                ╱
                         ╲──── can start Lezer grammar ─╱
                               after Lark grammar done
```

Steps 1 and 2 are sequential. Step 3's Lezer grammar can start as soon as the Lark grammar in Step 1 is defined (they mirror each other). The rest of Step 3 needs Step 2's endpoints.

---

## Verification (manual smoke test)

1. `cd lightly_studio && make static-checks` (passes)
2. `cd lightly_studio && make export-schema` (new endpoints in openapi.json)
3. `cd lightly_studio_view && npm run generate-api-client` (new TS types)
4. `cd lightly_studio_view && make static-checks` (passes)
5. Start dev server, open a collection's samples page
6. Type `width > 1024 and has_tag("train")` → grid filters correctly
7. Type `has_annotation(label == "cat")` → shows images with cat annotations
8. Autocomplete suggests fields after typing `w`, operators after `width `
9. Malformed input shows red underline
10. URL with `?q=...` is shareable
