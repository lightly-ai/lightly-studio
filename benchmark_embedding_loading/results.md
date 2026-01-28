# Embeddings2D benchmark summary

## Case
- Endpoint: `POST /api/embeddings2d/default`
- Filter: `ImageFilter` with only `sample_filter.collection_id`
- Dataset: `lexica_benchmark.db`

## Change
The filter step used `image_resolver.get_all_by_collection_id`, which eagerly loads captions, annotations, tags, metadata, etc. For `embeddings2d` we only need matching `sample_id`s.

Update:
- `_get_matching_sample_ids` now runs an **IDs-only** query (`select(ImageTable.sample_id)` / `select(VideoTable.sample_id)`).
- If the filter is **only** `collection_id`, the query is skipped entirely.

## Results
Before:
- `model=0.001s twod=0.733s filter=3.861s arrow=0.025s total=4.620s`

After:
- `model=0.001s twod=0.737s filter=0.000s arrow=0.014s total=0.752s`

## Notes / Next targets
- Remaining time is mostly in `twodim_embedding_resolver` (embeddings hash + load).
- Future optimizations should focus on `POST /api/embeddings2d/default`.
