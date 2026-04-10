# FINDINGS: SVAR Filter Query Builder Prototype (LIG-9166)

## Integration Status

The prototype is fully integrated into the real codebase and builds successfully. The "Advanced Query Builder ✨" toggle button appears above the samples grid.

---

## SVAR FilterBuilder Actual API

### Component Props
```typescript
<FilterBuilder
  fields={IField[]}      // { id: string; label: string; type: 'text'|'number'|'date'|'tuple' }[]
  options={TOptions}     // Record<fieldId, AnyData[]> or (field: string) => AnyData[]
  value={IFilterSet}     // optional: controlled value
  onchange={handler}     // (ev: { value: IFilterSet }) => void
/>
```

### Output Shape (`IFilterSet`)
```typescript
interface IFilterSet {
  rules?: (IFilter | IFilterSet)[];   // leaf rules or nested groups
  glue?: 'and' | 'or';               // how rules are combined, defaults to 'and'
}

interface IFilter {
  field: string;           // field id from the fields config
  filter?: TFilterType;    // operator: 'equal' | 'greater' | 'less' | 'greaterOrEqual' | ...
  includes?: AnyData[];    // for multi-select / "is one of" conditions
  value?: AnyData;         // single value
}
```

### Operator names (TFilterType)
`'greater'` | `'less'` | `'greaterOrEqual'` | `'lessOrEqual'` | `'equal'` | `'notEqual'` | `'contains'` | `'notContains'` | `'beginsWith'` | `'notBeginsWith'` | `'endsWith'` | `'notEndsWith'` | `'between'` | `'notBetween'`

Note: operators are camelCase strings, **not** symbols like `>`, `<`, `=`.

### TypeScript Package Issue
The `@svar-ui/svelte-filter` and `@svar-ui/filter-store` packages have broken `types` paths in their `package.json` (pointing to files that don't exist at the specified paths). Workaround: local type definitions in `src/lib/types/svar-filter.ts`. Also required changing `tsconfig.json` from `"moduleResolution": "node"` to `"bundler"`.

---

## NOT Operator
SVAR supports negation via `notEqual`, `notContains`, `notBeginsWith`, `notEndsWith`, `notBetween` operators on individual fields. There is **no top-level NOT group** (you can't negate an entire group like `NOT (annotation_class = "car" AND tag = "X")`). For our use case, `notEqual` on `annotation_class` maps cleanly to excluding a label.

---

## Multi-Value Fields & OR Across Annotation Classes
SVAR supports multi-value selection via the `includes` array on `IFilter`. When a user picks multiple values for a single field (e.g. "annotation_class is one of [car, truck]"), the output is:
```json
{ "field": "annotation_class", "filter": "equal", "includes": ["car", "truck"] }
```
This maps naturally to `annotation_label_ids: [carId, truckId]` — **a single API call with multiple IDs**, which the existing `AnnotationsFilter` supports. No OR group needed.

OR across fields (e.g. `annotation_class = "car" OR width > 1000`) is supported by SVAR via `glue: "or"` at the group level, but **our current translation skips OR groups** with a console warning. Backend `ImageFilter` currently has no OR semantics across fields anyway.

---

## FilterQuery Component (Natural Language / DSL Mode)
`FilterQuery` is a YouTrack-style search bar. It works without an AI backend in "structured syntax" mode (`parse: "strict"`). In that mode, users type `annotation_class = "car" AND width > 1000` and it parses to the same `IFilterSet` JSON that `FilterBuilder` emits. AI support (for conversational queries) requires an external AI endpoint — **not needed for initial integration**.

---

## Field Grouping
SVAR does not natively group fields by category in `FilterBuilder`. Fields are listed in a flat dropdown in the order they are defined in the `fields` array. You can influence grouping order but there are no visual separators or headers. For our use case, consider ordering: metadata fields, then annotation fields, then dimension fields.

---

## Missing Backend Fields
The following query fields would require backend additions to `ImageFilter`:
- **Filename / file path** — currently no string filter in `ImageFilter`
- **Import date / created_at** — not in `ImageFilter`
- **Annotation bbox area** — not in `ImageFilter`; would need aggregated annotation properties
- **Confidence score** — not exposed through `ImageFilter`
- **Annotation count per image** — no "image has >= N annotations" filter
- **Caption text search** — `has_captions` bool exists but no text search

Fields that work today with the existing API:
- Annotation label (via `annotation_label_ids`) ✅
- Tag (via `tag_ids`) ✅
- Image width / height (via `FilterDimensions`) ✅
- Custom metadata (via `MetadataFilter[]`) ✅

---

## UX Impressions vs Rheinmetall Example Queries

**Strengths:**
- Visual group-based builder is intuitive for non-technical users
- AND/OR glue toggle on groups is visible and clear
- Dynamic options (pass arrays for text fields, used for tags and annotation labels)
- Works out of the box, no backend changes required for supported fields

**Weaknesses vs Rheinmetall / Labelbox / Voxel51:**
- No field categories/groups — long flat list of fields is hard to scan
- No "image has annotation matching [bbox area > X]" style nested conditions
- `FilterQuery` DSL mode is more powerful for power users but requires learning syntax
- No "is empty" / "has no annotations" operator (would need a backend `has_annotations: false` flag)
- The `includes` multi-select UI for text fields isn't obvious — users must know to use it

**Overall:** Good fit for the straightforward AND-combination of existing filter types (labels + tags + dimensions + metadata). Gets unwieldy for annotation-level predicates that require backend additions.

---

## Implementation Notes

### Files Created
- `src/lib/utils/translateQueryBuilderFilter.ts` — maps `IFilterSet` → `ImageFilter`
- `src/lib/hooks/useQueryBuilderFilter/useQueryBuilderFilter.ts` — store-based hook
- `src/lib/hooks/useQueryBuilderFilter/index.ts` — barrel
- `src/lib/components/QueryBuilderPanel/QueryBuilderPanel.svelte` — UI panel
- `src/lib/components/QueryBuilderPanel/index.ts` — barrel
- `src/lib/types/svar-filter.ts` — local type definitions (workaround for broken package types)

### Files Modified
- `src/lib/components/Samples/Samples.svelte` — toggle button + panel + filter merge
- `tsconfig.json` — `moduleResolution: "node"` → `"bundler"` (needed for SVAR + SvelteKit 2)

### Filter Merge Strategy (Prototype)
When the Query Builder is active (`showQueryBuilder = true`) and has rules, it overrides `annotation_label_ids` and `tag_ids` in `samplesParams`. The existing dimension sliders and metadata range filters remain active alongside the QB. This is intentionally simple for the prototype.
