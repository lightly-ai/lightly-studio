# Browser MCAP frame provider

`createRecordingSession` is the production frame source for the point-cloud labeling
workspace. It reads an indexed MCAP recording over HTTP byte ranges, decodes ROS 2 CDR
`sensor_msgs/msg/PointCloud2` messages in a dedicated worker, and returns canonical frames
built with `../domain`'s `createPointCloudFrame`. Decoding never runs on the main thread and
no decoded-frame backend endpoint is involved.

## What a session is, and is not

A session has one job: turn a locator into a frame. It exposes `metadata`, `listFrames`,
`readFrame` and `dispose`, and nothing else.

It is deliberately **not** a cache and **not** a scheduler. Which frames are worth holding,
which request supersedes which, and when a stale result should be dropped are decisions the
app's query client already makes for every other resource, keyed the same way a frame is:
recording, revision, locator, point budget. An earlier version of this module owned all of
that itself and became a state machine with six methods, two overlapping cancellation
mechanisms and a separate `prefetch` that duplicated loading. Callers use
`@tanstack/svelte-query` instead; `../ProviderDiagnostics/useRecordingProbe.svelte.ts` shows
the shape.

Worker traffic is serialised in call order rather than pre-empted, so a background read cannot
cancel a visible one. Aborting a request that has not started yet settles the caller
immediately and never reaches the worker. Aborting one already in flight terminates the
worker, which is the only way to stop a synchronous decode — and it discards the parsed
summary index with it, costing a re-open. That asymmetry is why prefetching is safe now and
was not before.

## Source boundary

A session is created for one already-resolved `McapSource`: recording URL, byte length, opaque
`version`, optional strong ETag, the two clock IDs, and the explicitly confirmed
`coordinateFrame`. The session never discovers or guesses any of this. Resolving a sample to a
recording — sample -> group -> sequence -> recording path, plus authorization — belongs to the
endpoint adapter that supplies `McapSource`, so provider work and recording-path storage
(LIG-10634) can land independently.

`resolveMcapSource` builds one from a URL alone: a single `Range: bytes=0-0` read returns the
recording's total length in `Content-Range` and a revision in `ETag`, so no metadata endpoint
is required.

`coordinateFrame` is a confirmed sensor convention, never inferred from a schema or topic
name; `openMcap` re-checks it against the canonical frame and rejects a mismatch rather than
transforming. `version` participates in the caller's cache key, so a re-encoded recording
cannot serve stale frames.

A `FrameLocator` is a channel, a decimal nanosecond `logTimeNs`, and a zero-based
`occurrence`. The occurrence is what distinguishes two messages published on one channel at
the same log time, and it is part of the frame ID, so those frames cache and annotate
separately.

## Reading

`HttpRangeReadable` requires an exact `206` whose `Content-Range` matches the request and
rejects a full-file `200` fallback, a truncated or overlong body, and — with `If-Match` — a
recording that changed underneath the index. Reads are bounded per request and per
decompressed chunk, so a malformed index cannot allocate unbounded memory. The injected fetch
is always called with the global as its receiver: a browser `fetch` reached through an object
field throws `Illegal invocation`, which Node's implementation does not reproduce.

`listFrames` reads message indexes, not messages. It narrows `chunkIndexes` by their time
bounds — free, since the summary is already in memory — then reads each chunk's message index
region and parses the log times out. Those regions sit outside the chunks and are never
compressed, so listing a window costs kilobytes instead of decompressing megabytes of point
clouds. Iterating messages and discarding their payloads, which is what the public
`readMessages` path does, cost 2.7 MB for five locators on an 857 MB recording.

Zstandard decoding starts only once the index shows a chunk that uses it, so a recording of
lz4 chunks never instantiates the WebAssembly decoder, and a decoder that fails to start
cannot fail an open that would otherwise have succeeded.

Decoding takes the declared sensor frame as-is, requires exactly one scalar `x`, `y` and `z`
field each, drops non-finite points, and downsamples deterministically with a fixed stride so
a frame ID stays stable across point budgets.

## Errors, progress and telemetry

Failures are `ProviderError`s with an actionable code: `auth`, `range`, `source`, `schema`,
`fields`, `corrupt`, or `limit`. An unrecognized worker failure is reported as `corrupt`, with
the underlying cause in `detail` for logs and diagnostics — a generic message that names
nothing is not actionable for anyone. `onProgress` reports `indexing`, `decoding`, `ready` and
`error`; `onTelemetry` reports `open`, `list` and `decode` durations with bytes read.

Tests use `./mcapFixture`, a real indexed recording written with `@mcap/core` that contains
duplicate log timestamps, an unsupported channel, and an optional lz4-compressed variant.
