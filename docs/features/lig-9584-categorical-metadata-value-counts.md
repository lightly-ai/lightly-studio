# Feature: Categorical Metadata Value Counts

**Status:** Implemented  
**Linear:** [LIG-9584](https://linear.app/lightly/issue/LIG-9584/backend-categorical-metadata-value-counts-endpoint-5-sp)  
**Downstream consumer:** [LIG-9585](https://linear.app/lightly/issue/LIG-9585/frontend-categorical-metadata-bar-chart-filter-ui-8-sp)

## Problem and Target User

ML engineers need to understand how categorical metadata such as `city`, `camera_id`, or
`production_line` is distributed across a dataset. Today the backend exposes metadata schemas and
numeric histograms, but it cannot aggregate categorical values. The frontend therefore cannot show
categorical imbalance, reveal missing ingestion data, or populate a categorical filter.

The immediate user of this feature is the frontend engineer building the distribution panel. The
end user is an ML engineer checking whether production data is balanced and complete before
training or evaluating a model.

The endpoint must keep high-cardinality fields usable: return the 20 most frequent non-null values,
aggregate the remaining non-null values, and count missing values separately.

## Proposed User Flow

1. The dataset distribution panel requests categorical value counts for a collection, optionally
   passing the same active sample filters used by the grid.
2. The backend discovers categorical fields from the collection's merged metadata schema.
3. For each categorical field, the backend applies the active filters except filters on that field
   itself, then groups non-null values and counts missing samples.
4. The backend returns up to 20 concrete values, an `other_count`, and a `missing_count` for each
   field.
5. The frontend labels the semantic aggregate fields as **Other** and **Missing**, renders the
   distribution, and can use concrete values in its filter control.

## Wireframe

This is a backend-only feature. The wireframe describes the API and data flow rather than a screen.

```text
+--------------------------------------------------------------------------------+
| POST /collections/{collection_id}/metadata/value-counts                        |
|--------------------------------------------------------------------------------|
| Request                                                                        |
| {                                                                              |
|   "filters": <ImageFilter, optional>                                           |
| }                                                                              |
+--------------------------------------+-----------------------------------------+
                                       |
                                       v
+--------------------------------------------------------------------------------+
| Resolve categorical schema fields (string, boolean)                            |
| For each field:                                                                |
|   1. remove that field's own metadata filter                                   |
|   2. apply all remaining sample filters                                        |
|   3. GROUP BY extracted JSON value + COUNT                                     |
|   4. keep top 20; sum remainder; count absent/null separately                  |
+--------------------------------------+-----------------------------------------+
                                       |
                                       v
+--------------------------------------------------------------------------------+
| 200 OK                                                                         |
| {                                                                              |
|   "city": {                                                                   |
|     "value_counts": [                                                         |
|       { "value": "Zurich", "count": 120 },                                  |
|       { "value": "Berlin", "count": 64 }                                    |
|     ],                                                                         |
|     "other_count": 17,                                                        |
|     "missing_count": 3                                                        |
|   }                                                                            |
| }                                                                              |
+--------------------------------------------------------------------------------+
```

### Meaningful response states

```text
No categorical fields            Field exists; no matching samples
{}                               {
                                   "city": {
                                     "value_counts": [],
                                     "other_count": 0,
                                     "missing_count": 0
                                   }
                                 }

All matching samples missing     More than 20 concrete values
{                                {
  "city": {                       "camera_id": {
    "value_counts": [],              "value_counts": [<20 entries>],
    "other_count": 0,                "other_count": 481,
    "missing_count": 42               "missing_count": 7
  }                                  }
}                                  }
                                 }
```

## Content and Interaction

### Proposed contract

- Use `POST /collections/{collection_id}/metadata/value-counts` so callers can provide the same
  structured `ImageFilter` used by the existing numeric histogram endpoint.
- The request body is optional. No body means counts for the full collection.
- Return a mapping keyed by metadata field name, matching the existing
  `/metadata/histograms` response convention.
- Each field maps to:
  - `value_counts`: up to 20 `{value, count}` entries for concrete non-null values;
  - `other_count`: the sum of concrete values outside the top 20;
  - `missing_count`: samples where the key is absent or resolves to JSON null.
- `value` preserves the categorical scalar type (`string` or `boolean`). `count`, `other_count`,
  and `missing_count` are non-negative integers.
- `value_counts` is ordered by descending count. Equal counts use a deterministic ascending value
  order so responses and charts do not move arbitrarily between requests.
- Top 20 applies only to concrete non-null values. **Other** and **Missing** are additional semantic
  buckets, so a field can produce at most 22 displayed bars.
- `other_count` and `missing_count` are always present, including when zero. The frontend may omit
  zero-height bars from presentation.

### Contract-facing content semantics

- **Missing** means the field is absent from the sample, the sample has no metadata row, or the
  extracted JSON value is null. It does not mean an empty string, `false`, or the literal string
  `"Missing"`.
- **Other** means the sum of all concrete non-null values ranked below the top 20. It is not the
  literal string `"Other"` and it does not include missing samples.
- **Missing** and **Other** are presentation labels derived from `missing_count` and `other_count`.
  They must not be serialized as ordinary `value` entries; a user may legitimately store the
  strings `"Missing"` or `"Other"`.
- Every matching sample contributes exactly once per field. For each response field:
  `sum(value_counts[].count) + other_count + missing_count` equals the number of samples after
  applicable filters.
- The field's own metadata filter is excluded while other active filters remain applied. This
  faceted-search behavior preserves alternative values while the user edits that field and mirrors
  numeric metadata histograms.

### Validation

- `collection_id` follows the existing metadata endpoint convention; a syntactically valid unknown
  collection returns an empty mapping.
- Only scalar categorical schema types are returned. Numeric, list, dict, and complex metadata
  fields are omitted rather than partially coerced.
- The top-value limit is fixed at 20 for this scope; the endpoint does not expose a caller-supplied
  limit.

## States

- **Loading:** The endpoint is a single synchronous HTTP request with no partial/streaming response.
  The downstream frontend owns loading feedback and may keep prior data visible while refetching.
- **Empty:** Return `200 {}` when the collection has no categorical fields. Keep known categorical
  field keys in the response with zero counts when filters match no samples.
- **Error:** Use existing collection/API error handling for an invalid or inaccessible collection.
  Database/query failures fail the request as a whole; do not return silently partial field data.
- **Success:** Return `200` with the field mapping. A field with only missing values has empty
  `value_counts`, `other_count: 0`, and its full sample total in `missing_count`.

## Responsive and Accessibility Requirements

- Responsive layout does not apply to this backend-only endpoint.
- The response exposes bucket meaning structurally so clients do not have to infer semantics from
  English labels, color, position, or capitalization.
- Counts remain machine-readable integers. The downstream UI is responsible for localized labels,
  accessible bar names, and non-color-only distinction of Missing and Other.

## Decision Rationale

- **Mirror the numeric histogram endpoint:** A POST request with optional `ImageFilter`, a response
  keyed by field, and own-field filter exclusion gives the frontend one consistent distribution
  model.
- **Return all categorical fields in one request:** The distribution panel can switch fields without
  issuing a new request, while the server still limits every high-cardinality result.
- **Separate aggregate counts from concrete values:** Structural `other_count` and `missing_count`
  avoid collisions with real user values named `"Other"` or `"Missing"` and make filtering intent
  unambiguous.
- **Count missing against all collection samples:** An inner join would hide samples with no metadata
  row and under-report precisely the ingestion failures this feature is intended to reveal.
- **Use a fixed top 20:** It satisfies the agreed usability/performance bound and avoids adding a
  tuning control without a demonstrated consumer need.
- **Order by frequency with deterministic ties:** Most important categories appear first and API
  snapshots remain stable.
- **Keep aggregation in SQL:** GROUP BY and COUNT avoid loading per-sample metadata into Python and
  follow the existing resolver/database boundary for both DuckDB and PostgreSQL.

## Acceptance Criteria

- [x] A collection-level endpoint returns value counts for every scalar categorical metadata field.
- [x] Unfiltered requests count the full collection; requests with `ImageFilter` count matching
      samples.
- [x] For each field, its own metadata filter is excluded while all other active filters apply.
- [x] A field with 20 or fewer distinct non-null values returns every value with `other_count: 0`.
- [x] A field with more than 20 distinct non-null values returns exactly the 20 most frequent values
      and the sum of all remaining values in `other_count`.
- [x] Top-value ties have a deterministic order and no sample is counted twice or dropped.
- [x] `missing_count` includes samples with an absent key, explicit JSON null, and no metadata row.
- [x] Empty strings, `false`, and literal `"Missing"`/`"Other"` values remain concrete values rather
      than being merged into semantic buckets.
- [x] Empty collections or collections without categorical metadata return `200 {}`.
- [x] Known categorical fields remain present with zero counts when active filters match no samples.
- [x] Numeric and complex metadata fields are not returned by this endpoint.
- [x] The response models are represented in generated OpenAPI output.
- [x] Resolver and route tests cover low cardinality, high cardinality, missing values, filtering,
      own-field filter exclusion, empty results, deterministic ties, and collection isolation.
- [x] The aggregation works on the supported DuckDB and PostgreSQL JSON extraction paths.

## Non-goals

- Building the bar chart, categorical selector, or checkbox/multi-select UI (LIG-9585).
- Adding or changing categorical metadata filter operators.
- Making the Other bucket selectable; it aggregates multiple values and cannot identify a single
  filter predicate.
- Adding pagination, search, arbitrary top-N configuration, or returning the full high-cardinality
  tail.
- Aggregating list, dict, GPS, datetime, or other complex metadata types.
- Changing numeric histogram behavior or the existing metadata info endpoint.
- Persisting precomputed counts or adding a database migration.

## Assumptions and Open Questions

### Assumptions

- Categorical metadata means scalar `string` and `boolean` schema types. Integers and floats remain
  numeric even when they happen to have few unique values.
- Top 20 is recomputed from the samples remaining after applicable filters rather than fixed to the
  collection's unfiltered top 20; this makes the response represent the active dataset view.
- Missing is based on the total sample population after applicable filters, not only samples that
  already have a metadata row.
- Returning every categorical field in one request is acceptable at expected metadata-field counts,
  consistent with the all-fields numeric histogram endpoint.

### Open questions

- The downstream story requires **Missing** to be filterable, but the current equality filter does
  not define an explicit absent/null operator. Confirm whether LIG-9585 will add that filter contract
  or whether a separate backend follow-up is required; it is not part of this counts endpoint.
- Should boolean metadata be presented through this categorical flow in LIG-9585? This spec includes
  it because it is a scalar finite category, but the Linear examples mention strings only.
- If querying all categorical fields proves expensive for collections with many metadata keys,
  should a later optimization add an optional field selector? It is deliberately omitted from the
  initial contract.
