# STU-30 Polygon Annotations (Backend) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Spec:** `.experimental/superpowers/specs/2026-11-20-stu-30-polygon-annotations-backend-design.md`. Read it first; this plan repeats only the exact values that tasks need.

**Goal:** A `POLYGON` annotation type that can be added, edited, queried, cropped and exported, with clear errors where it isn't supported yet.

## Approach

- **Storage:** a `polygon_annotation` details table, one-to-one with `annotation_base`, like the other types. It has a JSON `polygons` column and an integer box.
- **One validation function** rounds the vertices and computes the box on every write, because the database doesn't check the shape.
- **Mirror masks:** each place that handles `SegmentationAnnotationTable` today gets a polygon branch. Most of Tasks 2–3 is this.
- **One ingestion fix:** labelformat already returns `MultiPolygon` for polygons and `BinaryMaskSegmentation` for masks. A new helper that chooses the type from that fixes the dropped vertices for COCO. YouTube-VIS is out of scope and keeps the current helper.
- **Ingestion ships last**, so every reader, export, check and the GUI handles polygons before the first real polygon is stored. The GUI shows a polygon as a read-only box; drawing and editing polygons is out of scope.

## Exact values

- `AnnotationType.POLYGON = "polygon"`; `AnnotationFileTask.OBJECT_DETECTION = "object_detection"`, `AnnotationFileTask.INSTANCE_SEGMENTATION = "instance_segmentation"`.
- Validation: at least 1 part, at least 3 vertices per part, finite numbers. Round to 3 decimals, then compute the box rounded outward.
- Evaluation error: `"Polygon annotations are not yet supported for instance segmentation evaluation."`; for semantic segmentation the same with "semantic segmentation".
- User-facing text says "polygon" and "part", never "multipolygon".

## Decisions the spec left to the builder

- Names: table `polygon_annotation`, relationship `AnnotationBaseTable.polygon_details`, model file `models/annotation/polygon.py`.
- `annotation_type` stays at its position, and `annotation_task` is the last parameter. Its default is `None`, which means `OBJECT_DETECTION`. This keeps positional calls working, and it lets the code detect when both are passed.
- `ExportFormat.SEGMENTATION_MASK_COCO` keeps its value, so the API doesn't break. The new value is `INSTANCE_SEGMENTATION_YOLO = "instance_segmentation_yolo"`.
- Errors: new resolvers and services raise `ValueError`, like the nearby `update_bounding_box` and `update_segmentation_mask`, not domain errors from `errors.py`. This is a deliberate exception from `backend-guide`; the existing `ValueError` handler maps them to HTTP responses.
- `to_coco_segmentation_masks` becomes a deprecated alias of `to_coco_instance_segmentation`, so it also exports polygons.

## How to work

- Before editing, load the skills from `AGENTS.md`: `python-guide`, `backend-guide`, `clean-code` for Python; `frontend-guide` for Tasks 14 and 14b; `changelog` for Tasks 14b and 15; `glossary` for Task 15.
- Validate each task: `cd lightly_studio && make static-checks && uv run pytest <affected tests>`.

## Review Focus

Inputs most likely to break for users. Each one has a test in the task named.

1. **COCO 2017 with mixed `iscrowd`:** one call loads polygons and masks, and export writes both back with the right `iscrowd`. Tests: Task 13 `test_add_samples_from_coco__instance_segmentation_mixed_crowd`, Task 8 `test_to_coco_instance_segmentation__polygons_and_masks`.
2. **Vertices outside the image, or a zero-area polygon:** stored as given. The crop is clipped or skipped with a warning, with no crash. Test: Task 3 `test_get_annotation_crops_for_ids__polygon_outside_image`.
3. **Class change on a track with polygons:** DuckDB deletes and reinserts the detail rows, and the polygons must come back unchanged. Test: Task 3 `test_update_label_by_object_track_id__keeps_polygons`.
4. **Evaluation on an existing COCO segmentation source:** fails with the polygon error, not a generic type error. Test: Task 7 `test_resolve_and_validate_collection__polygon_source`.
5. **YOLO segmentation with missing label files or blank lines:** loads without a crash. Tests: Task 10 (labelformat), Task 13 `test_add_samples_from_yolo__instance_segmentation_missing_label_file`.

---

## PR split

Target: at most ~200 added lines of non-test code per PR. Estimates are non-test lines. Resolver changes touch many files with imports and load options, so their estimates are generous. PRs are stacked in this order, and tasks run in PR order. Each PR adds its own changelog entry (see the list in Task 15).

| PR | Branch | Tasks | Content | Est. non-test LOC |
|---|---|---|---|---|
| labelformat | (labelformat repo) | 10 | YOLO segmentation reader fix, release 0.1.18 (other repo) | ~10 |
| 1 | `michal-stu-165-01-polygon-type-table` | 1 | Type, table, validation, migration | ~135 |
| 2 | `michal-stu-165-02-create-read-delete` | 2, 4 | Create, read and delete polygons: resolvers, API, `PolygonAnnotation`, `CreatePolygon` | ~165 |
| 3 | `michal-stu-165-03-copy-relabel-crops` | 3 | Copy, class change, crops | ~85 |
| 4 | `michal-stu-165-04-edit-polygons` | 5 | Edit polygons, reject box edits | ~105 |
| 5 | `michal-stu-165-05-query-by-box` | 6 | Query by box | ~90 + generated types |
| 6 | `michal-stu-165-06-export-coco-yolo` | 8, 9 | Export to COCO and YOLO | ~150 + generated types |
| 7 | `michal-stu-165-07-export-dialog` | 14 | Export dialog entries (frontend) | ~40 |
| 7b | `michal-stu-165-07b-frontend-polygon-guard` | 14b | GUI shows polygons as boxes; undo, copy and move keep polygons (frontend) | ~40 |
| 8 | `michal-stu-165-08-coco-ingestion` | 10 (bump), 12, 7 | COCO ingestion keeps polygons; evaluation rejects polygon sources | ~85 + `uv.lock` |
| 9 | `michal-stu-165-09-annotation-task` | 11, 13 | `AnnotationFileTask`, `annotation_task`, YOLO segmentation, deprecation | ~100 |
| 10 | `michal-stu-165-10-docs` | 15 | Docs, examples, glossary | docs only |

- **Don't release between PR 2 and PR 3; merge them close together.** Until PR 3, copying a dataset drops polygon geometry and relabeling a track or polygon fails or drops geometry. Polygons can only be created through the API or Python in that window.
- **PR 8 carries the evaluation error.** From PR 8 on, existing COCO segmentation calls store polygons, so that is when evaluation starts to see them.
- **PR 6 is the riskiest size.** If the export loader grows past the estimate, split it: COCO (Task 8), then YOLO (Task 9).
- PRs 3, 4 and 5 depend only on PR 2, and PR 7 only on PR 6, so they can be reviewed in parallel.
- **PR 7b must merge before PR 8.** From PR 8 on, COCO segmentation data loads as polygons, and without 7b the GUI crashes on them. PR 7b is stacked on PR 7; PR 8 is stacked on PR 7b and keeps only the e2e test changes that its data change causes.

---

### Task 1: Polygon type, table, validation and migration

**Files:**
- Create: `lightly_studio/src/lightly_studio/models/annotation/polygon.py`
- Modify: `lightly_studio/src/lightly_studio/models/annotation/annotation_base.py` (enum, `CROPPABLE_ANNOTATION_TYPES`, relationship, `AnnotationCreate`, `AnnotationView`)
- Create: `lightly_studio/src/lightly_studio/migrations/versions/<ts>_<rev>_add_polygon_annotation.py` (down_revision `1e2ff606de9f`)
- Test: `lightly_studio/tests/models/annotation/test_polygon.py`, `lightly_studio/tests/database/test_db_migrations.py`

**Interfaces:**
- Produces:
  - `Polygons = list[list[tuple[float, float]]]` (type alias)
  - `@dataclass(frozen=True) class ValidatedPolygons: polygons: Polygons; x: int; y: int; width: int; height: int`
  - `validate_polygons(polygons: Sequence[Sequence[Sequence[float]]]) -> ValidatedPolygons` — raises `ValueError`
  - `PolygonAnnotationTable` (`__tablename__ = "polygon_annotation"`; `sample_id` PK/FK to `annotation_base.sample_id`; `x, y, width, height: int`; `polygons: Polygons` in `Column(JSON, nullable=False)`; back-populates `polygon_details`)
  - `PolygonAnnotationView(x, y, width, height, polygons)`
  - `AnnotationType.POLYGON = "polygon"`, added to `CROPPABLE_ANNOTATION_TYPES`
  - `AnnotationBaseTable.polygon_details`, `AnnotationCreate.polygons: Polygons | None = None`, `AnnotationView.polygon_details: PolygonAnnotationView | None = None` (filled in `from_annotation_table`)

- [ ] **Step 1: Write failing tests** in `test_polygon.py`

```python
def test_validate_polygons__rounds_then_boxes_outward() -> None:
    result = polygon.validate_polygons([[(1.2, 2.7), (10.5, 2.7), (10.5, 8.0001)]])
    assert result.polygons == [[(1.2, 2.7), (10.5, 2.7), (10.5, 8.0)]]
    assert (result.x, result.y, result.width, result.height) == (1, 2, 10, 6)

def test_validate_polygons__rounds_to_millipixel() -> None:
    result = polygon.validate_polygons([[(0.12345, 0.0), (1.0, 0.0), (1.0, 1.0)]])
    assert result.polygons[0][0] == (0.123, 0.0)

def test_validate_polygons__box_spans_all_parts() -> None:
    result = polygon.validate_polygons(
        [[(0, 0), (2, 0), (2, 2)], [(10, 10), (12, 10), (12, 13)]]
    )
    assert (result.x, result.y, result.width, result.height) == (0, 0, 12, 13)

@pytest.mark.parametrize(
    ("polygons", "message"),
    [
        ([], "at least 1 part"),
        ([[(0, 0), (1, 0)]], "at least 3 vertices"),
        ([[(0, 0), (1, float("nan")), (1, 1)]], "finite"),
        ([[(0, 0), (1, float("inf")), (1, 1)]], "finite"),
    ],
)
def test_validate_polygons__invalid(polygons, message) -> None:
    with pytest.raises(ValueError, match=message):
        polygon.validate_polygons(polygons)
```

- [ ] **Step 2: Run** `uv run pytest tests/models/annotation/test_polygon.py -v` — FAIL (module missing).
- [ ] **Step 3: Implement** `polygon.py` and the `annotation_base.py` changes. Name the numbers as separate constants, `COORDINATE_DECIMALS = 3` and `MIN_VERTICES_PER_PART = 3` (clean-code: no unnamed literals). Round with `round(v, COORDINATE_DECIMALS)`; box `x = floor(min_x)`, `width = ceil(max_x) - x` (same for y). Error messages name "polygon" and "part", e.g. `"A polygon needs at least 1 part."`, `"Each polygon part needs at least 3 vertices."`, `"Polygon vertices must be finite numbers."`.
- [ ] **Step 4: Write the migration**, mirroring `1789700000_e1f2a3b4c5d6_add_cuboid_3d_annotation.py`: `sync_enum_values` adding `"POLYGON"`, `create_table("polygon_annotation", sample_id Uuid PK+FK, x/y/width/height Integer not null, polygons JSON not null)`. Downgrade deletes rows (`polygon_annotation`, then `annotation_base WHERE annotation_type = 'POLYGON'`), drops the table, syncs the enum back.
- [ ] **Step 5: Add migration test** `test_postgres_polygon_annotation__upgrade_and_downgrade` in `test_db_migrations.py`, following `test_postgres_unused_embedding_cache__upgrade_and_downgrade`: after upgrade, insert a polygon row and read back `polygons` equal to the inserted nested list; after downgrade, the table is gone.
- [ ] **Step 6: Run** `uv run pytest tests/models/annotation/test_polygon.py tests/database/test_db_migrations.py -v` — PASS. Then run the migration test on Postgres: `uv run pytest tests/database/test_db_migrations.py --postgres -k polygon -v` — PASS. Without `--postgres`, `postgres_only` tests are skipped and the migration is not tested; the flag starts its own Testcontainers database.
- [ ] **Step 7: Commit** `feat: add polygon annotation type and table`

---

### Task 2: Create and read polygons

**Files:**
- Modify: `resolvers/annotation_resolver/create_many.py`
- Modify (add `selectinload`/`joinedload(AnnotationBaseTable.polygon_details)` next to every `segmentation_details` load): `resolvers/image_resolver/load_options.py`, `resolvers/image_resolver/get_all_by_collection_id.py`, `resolvers/image_resolver/get_for_export.py`, `resolvers/annotation_resolver/get_all_with_payload.py` (2 places), `resolvers/annotation_resolver/get_all_by_parent_sample_ids_and_annotation_collection_id.py`, `resolvers/annotation_resolver/get_all_by_collection_id_and_parent_sample_ids.py` (new `POLYGON` branch), `resolvers/video_frame_resolver/get_all_by_collection_id.py`, `resolvers/video_resolver/get_all_by_collection_id.py`
- Modify: `services/annotations_service/create_annotation.py` (`AnnotationCreateParams.polygons`), `api/routes/api/annotations/create_annotation.py` (`AnnotationCreateInput.polygons`, passed through)
- Modify: `lightly_studio/tests/helpers_resolvers.py` (`create_annotation(..., polygons: Polygons | None = None)`, same in `create_annotations`)
- Modify (deletion ships with creation, so a polygon can always be deleted; without it the foreign key blocks the `annotation_base` delete after the first phase has committed): `resolvers/annotation_resolver/delete_annotations_by_ids.py` (add table to the tuple), `resolvers/dataset_resolver/delete_dataset.py` (`_delete_polygon_annotations`, same shape as `_delete_segmentation_annotations`)
- Test: `tests/resolvers/annotations/test_create_many_polygon.py`, `tests/api/routes/api/annotations/test_create_annotation.py`, the matching delete test files in `tests/resolvers/annotations/` and `tests/resolvers/dataset_resolver/`

**Interfaces:**
- Consumes: Task 1 `validate_polygons`, `PolygonAnnotationTable`, `AnnotationCreate.polygons`.
- Produces: `create_many` stores polygon details for `AnnotationType.POLYGON`; the box comes from `validate_polygons`, and `AnnotationCreate.x/y/width/height` are ignored for polygons. `AnnotationView.polygon_details` is populated on every read path above.

- [ ] **Step 1: Write failing tests**

```python
def test_create_many__polygon(db_session: Session) -> None:
    # image collection + label via helpers_resolvers
    ids = annotation_resolver.create_many(session=db_session, parent_collection_id=..., annotations=[
        AnnotationCreate(annotation_label_id=..., annotation_type=AnnotationType.POLYGON,
                         parent_sample_id=..., polygons=[[(1.5, 1.5), (4.0, 1.5), (4.0, 3.2)]])])
    annotation = annotation_resolver.get_by_id(session=db_session, annotation_id=ids[0])
    assert annotation.polygon_details.polygons == [[[1.5, 1.5], [4.0, 1.5], [4.0, 3.2]]]
    assert (annotation.polygon_details.x, annotation.polygon_details.width) == (1, 3)

def test_create_many__polygon_missing_polygons(db_session: Session) -> None:
    with pytest.raises(ValueError, match="polygons"):
        annotation_resolver.create_many(... annotation_type=AnnotationType.POLYGON, polygons=None ...)

def test_create_many__polygon_on_video_frame_with_track(db_session: Session) -> None:
    # parent is a video frame, object_track_id set; read back via video_frame get_all_by_collection_id
    assert frame.sample.annotations[0].polygon_details is not None
    assert frame.sample.annotations[0].object_track_id == track_id
```

API test `test_create_annotation__polygon`: POST with `annotation_type="polygon"`, `polygons=[[[0,0],[2,0],[2,2]]]` → 200, response `polygon_details.width == 2`; with 2 vertices → 400/422 with "at least 3 vertices".

- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement.** In `create_many`, add `elif annotation_type == AnnotationType.POLYGON:` that raises `ValueError("Missing polygons for polygon.")` when `polygons is None`, else builds `PolygonAnnotationTable` from `validate_polygons`; bulk-save the list; set `db_base_annotation.polygon_details = None` next to the others. Check how the API maps `ValueError` for the segmentation case and match it.
- [ ] **Step 3b: Delete tests**: `test_delete_annotations_by_ids__polygon` (after delete, `select(PolygonAnnotationTable)` is empty) and `test_delete_dataset__polygon` (same after deleting the dataset). Implement both deletions.
- [ ] **Step 4: Add a read test** to `tests/resolvers/annotations/test_get_all_with_payload.py`: `test_get_all_with_payload__polygon_details` asserts `polygon_details.polygons` in the payload view.
- [ ] **Step 5: Run** the new tests plus `tests/resolvers/annotations tests/resolvers/image_resolver tests/resolvers/video_frame_resolver tests/api/routes/api/annotations` — PASS.
- [ ] **Step 6: Commit** `feat: create and read polygon annotations`

---

### Task 3: Copy, label change and crops

**Files:**
- Modify: `resolvers/dataset_resolver/deep_copy.py` (`_copy_annotation_details(detail_table=PolygonAnnotationTable)`), `resolvers/annotation_resolver/annotation_helper.py` (reinsert a `PolygonAnnotationTable` copy), `resolvers/annotation_resolver/update_label_by_object_track_id.py` (`_capture_polygons`, delete, reinsert), `resolvers/annotation_resolver/get_annotation_crops.py` (outer join; `box_source = object_detection or segmentation or polygon`)
- Test: the matching files in `tests/resolvers/annotations/` and `tests/resolvers/dataset_resolver/`

**Interfaces:**
- Consumes: Task 2 `helpers_resolvers.create_annotation(..., polygons=...)`.
- Produces: no new names.

- [ ] **Step 1: Write failing tests**
  - `test_deep_copy__polygon`: copy has equal `polygons` and box, new `sample_id`.
  - `test_update_annotation_label__polygon` (path through `annotation_helper`): label changes; `polygons` unchanged.
  - `test_update_label_by_object_track_id__keeps_polygons`: two polygon frames in one track; after relabel, both keep their `polygons`.
  - `test_get_annotation_crops_for_ids__polygon`: crop box equals the polygon box.
  - `test_get_annotation_crops_for_ids__polygon_outside_image`: polygon partly outside the image is clipped; fully outside is skipped (no exception).
- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement** each file by copying its segmentation branch for polygons.
- [ ] **Step 4: Run** `uv run pytest tests/resolvers/annotations tests/resolvers/dataset_resolver -v` — PASS.
- [ ] **Step 5: Commit** `feat: copy, relabel and crop polygon annotations`

---

### Task 4: Python API `PolygonAnnotation` and `CreatePolygon`

**Files:**
- Create: `lightly_studio/src/lightly_studio/core/annotation/polygon.py` (`PolygonAnnotation`)
- Modify: `core/annotation/annotation_create.py` (`CreatePolygon`), `core/annotation/__init__.py` (export both), `core/sample.py` (`annotations` branch for `POLYGON`)
- Test: `tests/core/annotation/test_annotation_create.py`, `tests/core/image/test_image_sample.py`

**Interfaces:**
- Produces:
  - `class PolygonAnnotation(Annotation)`: `__init__(self, inner: PolygonAnnotationTable)` raises `ValueError("Expected annotation type: polygon")` for other types. No writable `DBField`s: `DBField.__set__` commits the raw value, which would skip validation and leave the box stale. Instead:
    - `x, y, width, height`: read-only properties (no setter), because the box is derived from the vertices.
    - `polygons`: property whose setter calls the Task 5 service `update_annotation_polygons`, so it validates and recomputes the box. Task 4 lands before Task 5 (PR 2 vs PR 4), so add the setter in Task 5 and make `polygons` read-only until then.
  - `class CreatePolygon(CreateAnnotationBase)`: `polygons: Polygons` (docstring: "Parts of the polygon, each a list of (x, y) vertices in pixels."); `to_annotation_create(...)` returns `AnnotationCreate(annotation_type=POLYGON, polygons=self.polygons, ...)`.

- [ ] **Step 1: Write failing tests**

```python
def test_create_polygon__to_annotation_create(db_session: Session) -> None:
    create = CreatePolygon(class_name="cat", polygons=[[(0, 0), (4, 0), (4, 4)]], confidence=0.5)
    result = create.to_annotation_create(session=db_session, dataset_id=..., parent_sample_id=...)
    assert result.annotation_type == AnnotationType.POLYGON
    assert result.polygons == [[(0, 0), (4, 0), (4, 4)]]

def test_image_sample__add_polygon_annotation(...) -> None:
    sample.add_annotation(CreatePolygon(class_name="cat", polygons=[[(0, 0), (4, 0), (4, 4)]]))
    (annotation,) = sample.annotations
    assert isinstance(annotation, PolygonAnnotation)
    assert annotation.width == 4

def test_polygon_annotation__box_is_read_only(...) -> None:
    with pytest.raises(AttributeError):
        annotation.width = 10
```

- [ ] **Step 2: Run** — FAIL. **Step 3: Implement.** **Step 4: Run** — PASS.
- [ ] **Step 5: Commit** `feat: add PolygonAnnotation and CreatePolygon to the Python API`

---

### Task 5: Update a polygon; reject box edits

**Files:**
- Create: `resolvers/annotation_resolver/update_polygons.py`, `services/annotations_service/update_annotation_polygons.py`
- Modify: `resolvers/annotation_resolver/__init__.py`, `services/annotations_service/__init__.py`, `services/annotations_service/update_annotation.py` (`AnnotationUpdate.polygons: Polygons | None = None`), `api/routes/api/annotation.py` (`AnnotationUpdateInput.polygons`, passed through), `resolvers/annotation_resolver/update_bounding_box.py`, `core/annotation/polygon.py` (`PolygonAnnotation.polygons` setter, see Task 4)
- Test: `tests/resolvers/annotations/test_update_polygons.py`, `tests/services/annotations_service/test_update_annotation.py`, `tests/resolvers/annotations/test_annotations_update_bounding_box.py`, `tests/core/image/test_image_sample.py`

**Interfaces:**
- Consumes: Task 1 `validate_polygons`.
- Produces: `update_polygons(session: Session, annotation_id: UUID, polygons: Polygons) -> AnnotationBaseTable` (replaces `polygons` and the box; `ValueError` if not found or not a polygon); `update_annotation_polygons(session, annotation_id, polygons) -> AnnotationBaseTable` (service; marks evaluation runs stale like `update_segmentation_mask` does, if it does).

- [ ] **Step 1: Write failing tests**
  - `test_update_polygons__replaces_and_recomputes_box`: start `[[(0,0),(2,0),(2,2)]]`, update to two parts `[[(0,0),(2,0),(2,2)], [(5,5),(9,5),(9,7)]]` → `width == 9`, `height == 7`.
  - `test_update_polygons__invalid_keeps_old`: 2-vertex part → `ValueError`; stored polygon unchanged.
  - `test_update_polygons__not_a_polygon`: on an object detection → `ValueError("Annotation type does not support polygons.")`.
  - `test_update_bounding_box__polygon_rejected`: `ValueError` whose message says to edit the vertices; box unchanged.
  - API `test_update_annotation__polygons`: PUT with `polygons` → 200, new box in response.
  - SDK `test_polygon_annotation__set_polygons`: `annotation.polygons = [[(0,0),(9,0),(9,7)]]` → `annotation.width == 9`; a 2-vertex part → `ValueError`, stored polygon unchanged.
- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement.** In `update_bounding_box`, add a branch before the `else`: `elif annotation.polygon_details: raise ValueError("The box of a polygon annotation can't be edited. Edit its vertices instead.")`.
- [ ] **Step 4: Run** — PASS. **Step 5: Commit** `feat: update polygon annotations`

---

### Task 6: Query polygons by box

**Files:**
- Create: `core/dataset_query/polygon_query.py` (`PolygonField`, `PolygonQuery`, mirroring `segmentation_mask_query.py`)
- Modify: `core/dataset_query/__init__.py` (export both), `models/query_expr.py` (`PolygonMatchExpr`, add to `MatchExpr`, `model_rebuild`, `_validate_evaluation_scope`), `core/dataset_query/query_translation.py` (`("polygon", "class_name"|"source")` string fields, `("polygon", "x"|"y"|"width"|"height")` integer fields, `("polygon", "confidence")` nullable float, `PolygonMatchExpr → PolygonQuery`), `services/sample_services/sample_query_service.py` (`_ANNOTATION_SCOPES[PolygonMatchExpr] = "polygon"`), `core/dataset_query/video_query_validation.py` (add to the annotation tuple)
- Test: `tests/core/dataset_query/test_polygon_query.py`, `tests/core/dataset_query/test_query_translation__database.py`, `tests/core/dataset_query/test_video_frame_query.py`

**Interfaces:**
- Produces: `PolygonMatchExpr(type: Literal["polygon_match_expr"], subexpr: MatchExpr)`; `PolygonField.{x,y,width,height,class_name,source,confidence}`; `PolygonQuery(*criteria: MatchExpression)` (like `SegmentationMaskQuery`; `MatchExpr` is the request-model union, not the query type) matching samples with an annotation of type `POLYGON` meeting the criteria.

- [ ] **Step 1: Write failing tests**
  - `test_polygon_query__width`: two images, polygons with box widths 10 and 50; `PolygonQuery(PolygonField.width > 20)` returns only the second.
  - `test_polygon_query__ignores_masks`: a mask with width 50 doesn't match `PolygonQuery(PolygonField.width > 20)`.
  - `test_query_translation__polygon_match_expr` (database): `QueryExpr` JSON `{"type": "polygon_match_expr", "subexpr": {"type": "integer_expr", "field": {"table": "polygon", "name": "x"}, ...}}` translates and returns the expected sample.
  - `test_video_frame_query__polygon`: `frame(polygon(width > 20))` scope validates on a video collection.
- [ ] **Step 2: Run** — FAIL. **Step 3: Implement.** **Step 4: Run** — PASS.
- [ ] **Step 5: Regenerate the frontend API types**: first export the schema (`cd lightly_studio && uv run src/lightly_studio/export_schema.py`, which writes `lightly_studio/openapi.json`), then `cd lightly_studio_view && npm run generate-api-client`. The client reads `openapi.json` and does not export it itself. This makes `types.gen.ts` / `schemas.gen.ts` include the new models; commit them.
- [ ] **Step 6: Commit** `feat: query polygon annotations by box`

---

### Task 7: Evaluation rejects polygon sources

**Files:**
- Modify: `lightly_studio/src/lightly_studio/evaluation/validators.py`
- Test: `lightly_studio/tests/evaluation/test_validators.py`

**Interfaces:**
- Produces: `resolve_and_validate_collection` raises `ValueError(f"Polygon annotations are not yet supported for {task_label} evaluation.")` for `INSTANCE_SEGMENTATION` (`"instance segmentation"`) and `SEMANTIC_SEGMENTATION` (`"semantic segmentation"`) when the collection holds any `POLYGON`; the check runs before `_validate_collection_annotation_type`.

- [ ] **Step 1: Write failing tests**
  - `test_resolve_and_validate_collection__polygon_source`: collection with one polygon and one mask, task `INSTANCE_SEGMENTATION` → `ValueError` matching `"Polygon annotations are not yet supported for instance segmentation evaluation."`.
  - Same for `SEMANTIC_SEGMENTATION` with `"semantic segmentation"`.
  - `test_resolve_and_validate_collection__masks_only_still_ok`: unchanged behavior.
- [ ] **Step 2: Run** — FAIL. **Step 3: Implement** with a `func.count()` query like `_validate_collection_annotation_type`, filtered on `annotation_type == POLYGON`. **Step 4: Run** — PASS.
- [ ] **Step 5: Commit** `feat: reject polygon sources in segmentation evaluation`

---

### Task 8: Export loader handles several types; COCO instance segmentation

**Files:**
- Modify: `export/annotation_batches.py`, `export/lightly_studio_label_input.py`, `export/dataset_export.py`, `api/routes/api/export.py`
- Test: `tests/export/test_dataset_export__coco_instance_segmentation.py` (rename from `test_dataset_export__coco_segmentation_masks.py` with `git mv`), `tests/export/test_lightly_studio_label_input.py`, `tests/export/test_dataset_export__pascal_voc.py`

**Interfaces:**
- Produces:
  - `iter_sample_annotations(session, samples, annotation_types: Sequence[AnnotationType], annotation_collection_id)` (was a single `annotation_type`; update all callers). `_export_options` loads `polygon_details` for `POLYGON`.
  - `LightlyStudioInstanceSegmentationInput` class attribute `ANNOTATION_TYPES: tuple[AnnotationType, ...] = (POLYGON, SEGMENTATION_MASK)`; `LightlyStudioPascalVOCInstanceSegmentationInput.ANNOTATION_TYPES = (SEGMENTATION_MASK,)`.
  - `_annotation_to_single_inst_seg` returns `SingleInstanceSegmentation(segmentation=MultiPolygon(polygons=...))` for polygons.
  - `DatasetExport.to_coco_instance_segmentation(output_json: PathLike | None = None, annotation_collection_id: UUID | None = None) -> None`; `to_coco_segmentation_masks` warns `DeprecationWarning("to_coco_segmentation_masks is deprecated, use to_coco_instance_segmentation instead.")` and delegates.
  - The API's `SEGMENTATION_MASK_COCO` branch calls `to_coco_instance_segmentation` and writes `coco_instance_segmentation_export.json`.

- [ ] **Step 1: Write failing tests**

```python
def test_to_coco_instance_segmentation__polygons_and_masks(...) -> None:
    # one image: a 2-part polygon [[(1,1),(5,1),(5,5)], [(10,10),(12,10),(12,12)]] and an RLE mask
    export.to_coco_instance_segmentation(output_json=tmp_path / "out.json")
    anns = sorted(json.loads(...)["annotations"], key=lambda a: a["iscrowd"])
    assert anns[0]["iscrowd"] == 0
    assert anns[0]["segmentation"] == [[1, 1, 5, 1, 5, 5], [10, 10, 12, 10, 12, 12]]
    assert anns[1]["iscrowd"] == 1 and "counts" in anns[1]["segmentation"]

def test_to_coco_segmentation_masks__deprecated(...) -> None:
    with pytest.warns(DeprecationWarning):
        export.to_coco_segmentation_masks(output_json=...)

def test_to_pascalvoc_segmentation_mask__ignores_polygons(...) -> None:
    # image with only a polygon → written mask is all background
```

- [ ] **Step 2: Run** — FAIL. **Step 3: Implement.** **Step 4: Run** `uv run pytest tests/export tests/api/routes/api/test_export.py -v` — PASS.
- [ ] **Step 5: Commit** `feat: export polygons in COCO instance segmentation`

---

### Task 9: YOLO instance segmentation export

**Files:**
- Modify: `export/lightly_studio_label_input.py` (`LightlyStudioYOLOInstanceSegmentationInput`), `export/dataset_export.py` (`to_yolo_instance_segmentation`), `models/export_format.py` (`INSTANCE_SEGMENTATION_YOLO`), `api/routes/api/export.py` (branch, output dir `temp_dir / "yolo_instance_segmentation"`)
- Test: `tests/export/test_dataset_export__yolo_instance_segmentation.py`, `tests/api/routes/api/test_export.py`
- Not changed: `export/youtube_vis_label_input.py` stays masks-only (YouTube-VIS is out of scope).

**Interfaces:**
- Consumes: Task 8 `ANNOTATION_TYPES`, `iter_sample_annotations`.
- Produces:
  - `LightlyStudioYOLOInstanceSegmentationInput(LightlyStudioInstanceSegmentationInput)`: `USE_RELATIVE_FILENAME = True`, `ANNOTATION_TYPES = (POLYGON,)`.
  - `DatasetExport.to_yolo_instance_segmentation(output_folder: PathLike, annotation_collection_id: UUID | None = None) -> None` — writes with `YOLOv8InstanceSegmentationOutput`; when the selection has masks, logs one warning: `"Skipped {n} segmentation mask annotations: YOLO instance segmentation supports only polygons."`.

- [ ] **Step 1: Write failing tests**
  - `test_to_yolo_instance_segmentation__polygon`: 100×50 image, polygon `[[(10,5),(50,5),(50,25)]]` → label line `"<cls> 0.1 0.1 0.5 0.1 0.5 0.5 0.1 0.1"` (labelformat repeats the first vertex to close the loop); `data.yaml` exists.
  - `test_to_yolo_instance_segmentation__skips_masks_with_warning`: image with a mask and a polygon → one line; `caplog` has `"Skipped 1 segmentation mask annotations"`.
  - `test_to_yolo_instance_segmentation__multi_part_becomes_one_line`: 2-part polygon → one line.
  - API: `test_export__instance_segmentation_yolo` returns a zip/dir with `labels/`.
- [ ] **Step 2: Run** — FAIL. **Step 3: Implement.** **Step 4: Run** — PASS.
- [ ] **Step 5: Regenerate API client types** (new `ExportFormat` value) as in Task 6 step 5: `export_schema.py` first, then `npm run generate-api-client`. Commit them.
- [ ] **Step 6: Commit** `feat: export polygons to YOLO`

---

### Task 10: labelformat — YOLO segmentation reader robustness (separate repo)

**Files (in `~/repos/labelformat`):**
- Modify: `src/labelformat/formats/yolov8.py` (`YOLOv8InstanceSegmentationInput.get_labels`)
- Test: `tests/unit/formats/test_yolov8.py`
- Then in Studio: `lightly_studio/pyproject.toml` `labelformat>=0.1.18`, `uv lock`

**Interfaces:**
- Produces: the segmentation reader skips images without a label file (with the existing warning, then `continue`) and ignores blank lines, matching `YOLOv8ObjectDetectionInput`.

- [ ] **Step 1: Write failing tests** `test_yolov8_instance_segmentation_input__missing_label_file` (image yielded nowhere, no exception) and `test_yolov8_instance_segmentation_input__blank_lines` (file `"0 0.1 0.1 0.5 0.1 0.5 0.5\n\n"` → one object).
- [ ] **Step 2: Run** `pytest tests/unit/formats/test_yolov8.py -v` — FAIL (`FileNotFoundError` / `IndexError`).
- [ ] **Step 3: Implement**: `continue` after the warning; read with `[line.split() for line in file if line.strip()]`.
- [ ] **Step 4: Run** — PASS. **Step 5:** open the labelformat PR, release 0.1.18, then bump in Studio and `uv lock`.
- [ ] **Step 6: Commit (Studio)** `chore: require labelformat 0.1.18`

---

### Task 11: `AnnotationFileTask` and the deprecation resolver

**Files:**
- Create: `lightly_studio/src/lightly_studio/core/annotation_file_task.py`
- Modify: `lightly_studio/src/lightly_studio/__init__.py` (export `AnnotationFileTask`)
- Test: `lightly_studio/tests/core/test_annotation_file_task.py`

**Interfaces:**
- Produces:
  - `class AnnotationFileTask(str, Enum)` with the two values from Global Constraints.
  - `resolve_annotation_task(annotation_task: AnnotationFileTask | None, annotation_type: AnnotationType | None) -> AnnotationFileTask`: both set → `ValueError("Pass either annotation_task or annotation_type, not both.")`; only `annotation_type` → `DeprecationWarning("annotation_type is deprecated, use annotation_task instead.", stacklevel=3)` and map `OBJECT_DETECTION→OBJECT_DETECTION`, `SEGMENTATION_MASK→INSTANCE_SEGMENTATION`, anything else → `ValueError(f"Invalid annotation type: {annotation_type}")`; neither → `OBJECT_DETECTION`.

- [ ] **Step 1: Write failing tests** for the four cases above (`pytest.warns`, `pytest.raises`, default).
- [ ] **Step 2: Run** — FAIL. **Step 3: Implement.** **Step 4: Run** — PASS.
- [ ] **Step 5: Commit** `feat: add AnnotationFileTask`

---

### Task 12: Image ingestion creates polygons; invalid parts dropped

**Files:**
- Modify: `core/labelformat_helpers.py`, `core/image/add_annotations.py`
- Test: `tests/core/test_labelformat_helpers.py`, `tests/core/image/test_add_annotations.py`
- Not changed: `core/video/add_videos.py` keeps calling `get_segmentation_annotation_create` (YouTube-VIS is out of scope), so its existing tests stay as they are.

**Interfaces:**
- Produces:
  - `get_instance_segmentation_annotation_create(...) -> AnnotationCreate | None` (new; called by `add_annotations.add_annotations_from_labelformat` instead of `get_segmentation_annotation_create`): `MultiPolygon` → `AnnotationType.POLYGON` with `polygons` = the valid parts, or `None` if no part is valid; `BinaryMaskSegmentation` → `SEGMENTATION_MASK` via `get_segmentation_annotation_create`. `get_segmentation_annotation_create` is unchanged.
  - `valid_polygon_parts(multipolygon: MultiPolygon) -> Polygons` — keeps parts with ≥3 vertices and only finite coordinates.
  - `warn_skipped_polygons(count: int) -> None` — no-op for 0, else one `logger.warning(f"Skipped {count} polygon annotations without a valid part. A valid part has at least 3 vertices.")`.
  - `add_annotations.add_annotations_from_labelformat` sums the `None`s over all batches and calls `warn_skipped_polygons` once at the end.

- [ ] **Step 1: Write failing tests**

```python
def test_get_instance_segmentation_annotation_create__multipolygon_is_polygon() -> None:
    result = labelformat_helpers.get_instance_segmentation_annotation_create(
        parent_sample_id=uuid4(), annotation_label_id=uuid4(),
        segmentation=MultiPolygon(polygons=[[(1.0, 1.0), (5.0, 1.0), (5.0, 5.0)], [(0.0, 0.0), (1.0, 1.0)]]),
    )
    assert result.annotation_type == AnnotationType.POLYGON
    assert result.polygons == [[(1.0, 1.0), (5.0, 1.0), (5.0, 5.0)]]

def test_get_instance_segmentation_annotation_create__no_valid_part() -> None:
    assert labelformat_helpers.get_instance_segmentation_annotation_create(
        ..., segmentation=MultiPolygon(polygons=[[(0.0, 0.0), (1.0, 1.0)]])) is None

def test_add_annotations_from_labelformat__one_warning_for_skipped(caplog, ...) -> None:
    # 3 images across 2 batches (patch batch size), each with one invalid polygon
    assert caplog.text.count("Skipped 3 polygon annotations") == 1
```

- [ ] **Step 2: Run** — FAIL. **Step 3: Implement.** **Step 4: Run** `uv run pytest tests/core -v -k "labelformat or add_annotations or add_videos"` — PASS (`add_videos` confirms YouTube-VIS is unchanged).
- [ ] **Step 5: Commit** `fix: keep COCO polygon vertices as polygon annotations`

---

### Task 13: COCO and YOLO dataset methods take `annotation_task`

**Files:**
- Modify: `core/image/image_dataset.py` (`add_annotations_from_coco`, `add_samples_from_coco`, `add_annotations_from_yolo`, `add_samples_from_yolo`)
- Test: `tests/core/image/test_image_dataset__coco.py`, `tests/core/image/test_image_dataset__yolo.py`, `tests/core/image/test_image_dataset__add_annotations.py`

**Interfaces:**
- Consumes: Task 11 `resolve_annotation_task`; Task 12 polygon creation.
- Produces: COCO methods: `annotation_type: AnnotationType | None = None` (deprecated, same position) and `annotation_task: AnnotationFileTask | None = None` (last); `INSTANCE_SEGMENTATION` → `COCOInstanceSegmentationInput`. YOLO methods: `annotation_task: AnnotationFileTask | None = None` (last); `INSTANCE_SEGMENTATION` → `YOLOv8InstanceSegmentationInput`. Docstrings say what each task reads; the COCO one says `iscrowd=0` → polygons, `iscrowd=1` → masks.

- [ ] **Step 1: Write failing tests** (write small fixture files under `tmp_path`)
  - `test_add_samples_from_coco__instance_segmentation_mixed_crowd`: one `iscrowd=0` 2-part polygon + one `iscrowd=1` RLE → one `POLYGON` with both parts and one `SEGMENTATION_MASK`.
  - `test_add_samples_from_coco__deprecated_annotation_type`: `annotation_type=SEGMENTATION_MASK` → `DeprecationWarning`, polygons created.
  - `test_add_samples_from_coco__both_parameters`: `ValueError`.
  - `test_add_annotations_from_coco__instance_segmentation`: same result via the attach path.
  - `test_add_samples_from_yolo__instance_segmentation`: one line `0 0.1 0.1 0.5 0.1 0.5 0.5` on a 100×50 image → polygon `[[(10.0, 5.0), (50.0, 5.0), (50.0, 25.0)]]`.
  - `test_add_samples_from_yolo__instance_segmentation_missing_label_file`: an image without a label file is skipped with labelformat's warning and no crash; the other images load (needs Task 10). Studio creates samples from `get_labels()`, so a skipped image gets no sample, same as with `OBJECT_DETECTION` today.
  - `test_add_annotations_from_yolo__instance_segmentation`.
- [ ] **Step 2: Run** — FAIL. **Step 3: Implement.** **Step 4: Run** the three test files — PASS.
- [ ] **Step 5: Commit** `feat: load COCO and YOLO polygons with annotation_task`

---

### Task 14: Export dialog entries (frontend)

**Files:**
- Modify: `lightly_studio_view/src/lib/components/ExportSamples/exportOptions.ts` (`ExportType` union, the format list and its labels), `lightly_studio_view/src/lib/components/ExportSamples/ExportSamples.svelte` (tab content for the new type)
- Test: `lightly_studio_view/src/lib/components/ExportSamples/exportOptions.test.ts` (there is no `ExportSamples.svelte` test)

**Interfaces:**
- Consumes: Task 9 `ExportFormat.INSTANCE_SEGMENTATION_YOLO` in the generated client.
- Produces: in `exportOptions.ts`, the `segmentation` option label "Image Segmentation Mask (COCO)" becomes "Instance segmentation (COCO)", and a new `ExportType` value with label "Instance segmentation (YOLO)" is listed for image collections. In `ExportSamples.svelte`, the COCO tab description is "Polygons and segmentation masks will be exported in COCO format."; the YOLO tab has description "Polygons will be exported in YOLO format. Segmentation masks are skipped.", `testId="submit-button-instance-segmentations-yolo"`, and submits `instance_segmentation_yolo`.

- [ ] **Step 1: Write the failing tests** in `exportOptions.test.ts`: the options for an image collection include both labels; the COCO option no longer says "Segmentation Mask".
- [ ] **Step 2: Run** `npx vitest run src/lib/components/ExportSamples/exportOptions.test.ts` — FAIL. **Step 3: Implement.** **Step 4: Run** — PASS; `make static-checks` in `lightly_studio_view`.
- [ ] **Step 5: Commit** `feat: add instance segmentation export entries`

---

### Task 14b: GUI shows polygons as boxes; undo, copy and move keep polygons (frontend)

Without this task the GUI throws on any polygon in 2 places (`getBoundingBox`, `AnnotationItem.svelte`), and 2 more show nothing (the canvas in `SampleAnnotations/index.svelte`, the size in the side panel). Undo of a delete, copy and move to another source fail: they send no `polygons`, so the backend rejects them with "Polygon annotations require polygons.". The create API already accepts `polygons` and computes the box, so the fix is one field. Move is fixed ahead of time: the annotation card that offers it doesn't open for polygons yet (`CARD_TYPES` in `AnnotationCardLayer.svelte`).

**Files:**
- Modify: `lightly_studio_view/src/lib/services/types.ts` (`isPolygonAnnotation` guard), `src/lib/components/SampleAnnotation/utils.ts` (`getBoundingBox`), `src/lib/components/SampleAnnotation/SampleAnnotation.svelte` (no `ResizableRectangle` for polygons), `src/lib/components/SampleAnnotations/index.svelte` (draw the box as `object_detection`), `src/lib/components/AnnotationsGrid/AnnotationItem/AnnotationItem.svelte`, `src/lib/components/SampleDetails/SampleDetailsSidePanel/SampleDetailsSidePanelAnnotation/SampleDetailsSidePanelAnnotation.svelte`
- Modify: `src/lib/services/addAnnotationDeleteToUndoStack.ts` (`buildRestoreInput`), `src/lib/components/CopyAnnotationToSource/useCopyAnnotationToSource.svelte.ts`, `src/lib/components/SampleDetails/AnnotationCard/useMoveAnnotationByCopy.svelte.ts`
- Test: the `.test.ts` next to each modified file, except `types.ts` and `SampleDetailsSidePanelAnnotation.svelte`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: Task 2 `AnnotationView.polygon_details: PolygonAnnotationView | null` (`x`, `y`, `width`, `height`, `polygons`) and `AnnotationCreateInput.polygons` in the generated client.
- Produces: `isPolygonAnnotation(annotation: Annotation): annotation is Annotation & { polygon_details: PolygonAnnotationView }` in `$lib/services/types`.

- [ ] **Step 1: Show polygons as boxes.** The code and its tests exist in commit `91c58e011` (on PR 8). Bring over its `lightly_studio_view/src/` files only (`git checkout 91c58e011 -- <files>`); its 3 e2e files stay in PR 8. Tests: `utils.test.ts` "returns the rounded box of a polygon annotation", `SampleAnnotation.test.ts` "shows the box of a polygon without resize handles in edit mode", `index.test.ts` "draws the box of a polygon annotation", `AnnotationItem.test.ts` "shows the box of a polygon annotation".
- [ ] **Step 2: Write the failing tests** for the three create inputs. Each test uses a polygon annotation with `polygon_details.polygons = [[[0, 0], [10, 0], [10, 10]]]` and asserts that `createAnnotation` gets `annotation_type: 'polygon'` and `polygons: [[[0, 0], [10, 0], [10, 10]]]`:
  - `addAnnotationDeleteToUndoStack.test.ts`: "restores a deleted polygon with its vertices"
  - `useCopyAnnotationToSource.svelte.test.ts`: "copies a polygon with its vertices"
  - `useMoveAnnotationByCopy.svelte.test.ts`: "moves a polygon with its vertices", and the undo re-creates the original with the same `polygons`
- [ ] **Step 3: Run** `npx vitest run <the 3 test files>` — FAIL.
- [ ] **Step 4: Implement:** add `polygons: annotation.polygon_details?.polygons` to the create input in all three. Don't pass the polygon box: the backend computes it.
- [ ] **Step 5: Run** the 7 affected test files — PASS; `make static-checks` in `lightly_studio_view`. Never the full suite.
- [ ] **Step 6: Changelog** (Added): `The GUI shows polygon annotations as boxes. Polygons can't be edited in the GUI yet.`
- [ ] **Step 7: Commit** `feat: show polygon annotations as boxes in the GUI`. Then merge up without rewriting history: 7b → PR 8 → PR 9 → PR 10 (`git merge --no-edit`), and set PR 8's base on GitHub: `gh pr edit <PR 8> --base michal-stu-165-07b-frontend-polygon-guard`.

---

### Task 15: Docs, examples, glossary

**Files:**
- Modify: `lightly_studio/docs/docs/workflows/export.md` (new COCO/YOLO entries; note that COCOeval treats `iscrowd=1` as ignore regions), `lightly_studio/docs/docs/workflows/image_dataset.md` and any page using `annotation_type=` (switch to `annotation_task=`), examples `examples/example_coco.py`, `examples/example_coco_s3.py`, `examples/coco_plugins_demo/example_coco_plugins.py`
- Modify: `.agents/skills/glossary/SKILL.md` (rows for **polygon** and **part**; avoid "multipolygon"; add polygon to the annotation row)

- [ ] **Step 1:** `grep -rn "annotation_type=\|to_coco_segmentation_masks" lightly_studio/docs lightly_studio/src/lightly_studio/examples README.md`. Replace only calls to the deprecated APIs: `add_annotations_from_coco`, `add_samples_from_coco`, `add_annotations_from_yolo`, `add_samples_from_yolo`, and `to_coco_segmentation_masks`. Leave `add_videos_from_youtube_vis(annotation_type=...)` alone (YouTube-VIS is out of scope, not deprecated). Leave other `annotation_type=` uses alone, e.g. `AnnotationCreate(annotation_type=...)` in `examples/coco_plugins_demo/lightly_train_inference_operator.py` and its docs snippet; `AnnotationCreate` still requires it.
- [ ] **Step 2: Changelog entries** (load the `changelog` skill), one per change. Each entry goes into the PR that makes the change, not into this PR. This step lists them and checks that they are all there:
  - Added: `Python SDK: Load polygon annotations from COCO and YOLO with annotation_task=AnnotationFileTask.INSTANCE_SEGMENTATION, and export them to the same formats.`
  - Added: `Export polygons to YOLO with the new "Instance segmentation (YOLO)" export.`
  - Changed: `The "Segmentation masks (COCO)" export is now "Instance segmentation (COCO)" and includes polygons.`
  - Deprecated: `Python SDK: annotation_type in the COCO methods. Use annotation_task instead.` and `Python SDK: to_coco_segmentation_masks. Use to_coco_instance_segmentation instead.`
  - Fixed: `Python SDK: COCO polygons are loaded with their vertices, not only their box.`
  - Added (PR 7b): `The GUI shows polygon annotations as boxes. Polygons can't be edited in the GUI yet.`
  - Changed: `Instance and semantic segmentation evaluation reports an error for annotation sources with polygons. Before, such sources ran and skipped the polygons.`
- [ ] **Step 3: Run** `cd lightly_studio && make static-checks` and `uv run python -W error::DeprecationWarning -c "import lightly_studio"` — no warnings at import.
- [ ] **Step 4: Commit** `docs: polygon annotations and annotation_task`

---

## Follow-ups (not in this plan)

- Query editor keyword `polygon(...)` in `lightly_studio_view/src/lib/components/QueryEditor/language/` (frontend polygon ticket).
- Spec follow-ups: rasterizing polygons, removing deprecated APIs, labelformat COCO RLE/`iscrowd` check.
