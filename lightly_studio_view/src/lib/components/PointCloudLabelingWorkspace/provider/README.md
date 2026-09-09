# Browser MCAP frame provider

`createMcapFrameProvider` is the production frame source for the point-cloud labeling
workspace. It reads an indexed MCAP recording over HTTP byte ranges, decodes ROS 2 CDR
`sensor_msgs/msg/PointCloud2` messages in a dedicated worker, and returns canonical
frames built with `../domain`'s `createPointCloudFrame`. Decoding never runs on the main
thread and no decoded-frame backend endpoint is involved.

## Source boundary

A provider is created for one already-resolved `McapSource`: recording URL, byte length,
opaque `version`, optional strong ETag, the two clock IDs, and the explicitly confirmed
`coordinateFrame`. The provider never discovers or guesses any of this. Resolving a sample
to a recording — sample -> group -> sequence -> recording path, plus authorization —
belongs to the endpoint adapter that supplies `McapSource`, so provider work and
recording-path storage (LIG-10634) can land independently.

`coordinateFrame` is a confirmed sensor convention, never inferred from a schema or topic
name; `openMcap` re-checks it against the canonical frame and rejects a mismatch rather
than transforming. `version` participates in cache identity, so a re-encoded recording
cannot serve stale frames.

A `FrameLocator` is a channel, a decimal nanosecond `logTimeNs`, and a zero-based
`occurrence`. The occurrence is what distinguishes two messages published on one channel
at the same log time, and it is part of the frame ID, so those frames cache and annotate
separately.

## Access, cancellation and caching

`HttpRangeReadable` requires an exact `206` whose `Content-Range` matches the request and
rejects a full-file `200` fallback, a truncated or overlong body, and — with `If-Match` —
a recording that changed underneath the index. Reads are bounded per request and per
decompressed chunk, so a malformed index cannot allocate unbounded memory.

One operation runs at a time. Starting another cancels the previous one: the worker is
terminated, which stops synchronous decoding that an `AbortSignal` alone cannot interrupt,
and the next request opens a fresh worker. External signals cancel the same way. A
cancelled request rejects with `AbortError` and is not reported as a failure. `dispose`
cancels, terminates, and clears the cache.

`FrameCache` is LRU, bounded by both packed point bytes and entry count, and keyed by
recording version, frame identity, and point budget. Oversized frames are not cached
rather than evicting everything else. `prefetch` loads at most four caller-supplied
neighbors and reuses the same cache.

## Errors, progress and telemetry

Failures are `ProviderError`s with an actionable code: `auth`, `range`, `source`,
`schema`, `fields`, `corrupt`, or `limit`. An unrecognized worker failure is reported as
`corrupt` rather than leaking internals. `onProgress` reports `indexing`, `decoding`,
`ready`, and `error`; `onTelemetry` reports `load`, `decode`, `cache` (with `cacheHit`),
and `failure` timings alongside current cache bytes and bytes read.

Decoding takes the declared sensor frame as-is, requires exactly one scalar `x`, `y` and
`z` field each, drops non-finite points, and downsamples deterministically with a fixed
stride so a frame ID stays stable across point budgets.

Tests use `./mcapFixture`, a real indexed recording written with `@mcap/core` that
contains duplicate log timestamps, an unsupported channel, and an optional lz4-compressed
variant.
