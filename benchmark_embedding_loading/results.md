# Embeddings2D benchmark summary

## Case
- Endpoint: `POST /api/embeddings2d/default`
- Filter: `ImageFilter` with only `sample_filter.collection_id`
- Dataset: `lexica_benchmark.db`

## Changes
1) Filter path: replace eager-loaded sample fetch with an IDs-only query (or skip entirely for collection-only filters).
2) twod cache key: avoid giant IN-list by hashing per-collection, and stream the hash aggregation to reduce Python overhead.

## Results
Baseline (before any changes):
- `model=0.001s twod=0.733s filter=3.861s arrow=0.025s total=4.620s`

After change #1 (IDs-only filter):
- `model=0.001s twod=0.737s filter=0.000s arrow=0.014s total=0.752s` (~6.1x faster vs baseline)

After change #2 (twod hash micro-optimization):
- `model=0.001s twod=0.266s filter=0.000s arrow=0.015s total=0.282s` (~16.4x faster vs baseline; ~2.7x faster vs change #1)

## Notes / Next targets
- Remaining time is dominated by the per-request embeddings hash scan.
- Potential improvement (not implemented): store `embedding_hash` per row at write time and hash those values for the cache key. Expected to shave a noticeable fraction of the current `twod` time (likely ~25–40%), but still O(N) over rows.
- Future optimizations should focus on `POST /api/embeddings2d/default`.
