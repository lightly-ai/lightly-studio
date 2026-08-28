# MCAP point-cloud processing PoC

This prototype supports the decision in LIG-10610: whether point-cloud frames should be read and
decoded directly in the browser or processed on demand by the LightlyStudio backend. It deliberately
uses the same packed XYZI output and the same Three.js renderer for both paths.

The prototype is available at the hidden `/mcap-poc` route. It is not linked from the product
navigation and is not an annotation workflow.

## Run it

Set a fixed source before starting LightlyStudio:

```bash
export LIGHTLY_STUDIO_MCAP_POC_SOURCE=/absolute/path/to/perception.mcap
```

Then build and start LightlyStudio normally and open `/mcap-poc`. Select a ROS 2
`sensor_msgs/msg/PointCloud2` topic, enter a nanosecond timestamp, choose how many runs to collect,
and press **Run both**. The first run of each path also parses the summary index and is reported
separately from the warm medians; **Drop cached indexes** puts both paths back into their cold state.
**Copy as markdown** produces a table that can be pasted straight into the issue.

The source can also be a presigned HTTPS object URL. Do not configure an `s3://` URL for the browser
comparison because browsers cannot fetch that scheme. The object store must:

- accept `GET`, `HEAD`, and `Range` requests;
- return `206 Partial Content` for range reads;
- expose `Accept-Ranges`, `Content-Range`, `Content-Length`, and `ETag` through CORS;
- allow the LightlyStudio origin; and
- keep the signed URL valid for the duration of a benchmark run.

Local sources are exposed through a PoC-only range endpoint. The API never accepts a caller-provided
path or URL; this avoids turning it into an arbitrary file or network reader.

## What is measured

Both implementations locate the first message at or after the requested timestamp, decode ROS 2 CDR
`PointCloud2`, remove non-finite XYZ points, and produce interleaved little-endian float32 XYZI data.
Both keep the parsed summary index alive between frames, so the reported per-frame cost is the cost
of an additional frame rather than the cost of opening the recording again.

| Metric          | Browser path                              | Backend path                           |
| --------------- | ----------------------------------------- | -------------------------------------- |
| Total time      | UI request through worker response        | UI request through binary response     |
| Processing time | Indexed read and decode in the worker     | Indexed read and decode on the server  |
| Cold total      | First run, which also parses the index    | First run, which also parses the index |
| Decode time     | CDR parse plus PointCloud2 to packed XYZI | Same, measured server-side             |
| Source bytes    | Range-request bytes for that frame        | Reader bytes for that frame            |
| Reads           | HTTP range request count                  | Reader call count                      |
| Peak memory     | Not portable across browsers              | Python `tracemalloc` peak              |

The UI also checks that both paths returned the same log timestamp and point count for every
iteration and reports how many of the compared frames were identical.

## Measured results

Recording: `perception.mcap`, 899 MB, 1892 lz4 chunks, 97757 messages, three Livox
`sensor_msgs/msg/PointCloud2` topics. Topic `/livox/lidar_front_left/self_filtered`, roughly 9000
points per frame, a 321 KB CDR message and a 145 KB packed XYZI frame.

| Measurement                     | Browser path              | Backend path               |
| ------------------------------- | ------------------------- | -------------------------- |
| Cold run (parses summary index) | 27 ms, 490 KB, 4 requests | 84 ms, 490 KB, 87397 reads |
| Warm frame, total               | 8–10 ms                   | 4.1 ms                     |
| Warm frame, decode only         | 0.7–1.4 ms                | 3.8 ms                     |
| Warm frame, source bytes        | ~430 KB                   | ~436 KB                    |
| Warm frame, reads               | 2 range requests          | 8 reader calls             |
| Warm frame, peak memory         | Not measured              | 2.3 MB                     |

Both paths returned identical log timestamps and point counts on every frame tested.

Two findings drove the current implementation:

- **Parsing the summary index dominates everything else.** Before the index was cached, every
  backend frame request cost about 87 ms, of which roughly 80 ms was re-reading the chunk index and
  only 4 ms was reading and decoding the frame. Caching the opened reader made the backend path
  about twenty times faster without touching the decoder. The browser worker is reused for the same
  reason. Any production design must keep an indexed reader alive per source; a stateless
  "open, seek, decode, close" endpoint measures the index, not the workload.
- **Both paths move the same bytes.** Each frame costs roughly 430 KB of source reads regardless of
  where it is decoded, because a whole lz4 chunk has to be decompressed to reach one message. The
  backend additionally sends a 145 KB packed frame to the browser, so the browser path transfers
  about three times less over the wire for this recording; the backend path can shrink that further
  by downsampling before it sends.

The Python reader issues 87397 small `read()` calls while parsing the index of this recording. On a
local file that is cheap, but it is the number to watch when the source is object storage, and it is
why a buffered remote filesystem is a prerequisite for the backend path on S3.

Caveat: these numbers were collected on a Linux VM on the developer machine with the recording on
local disk. The browser figures come from the same `@mcap/core` code path driven from Node against a
local HTTP range server, not from Chrome, so treat them as a lower bound on real browser cost. Rerun
the UI benchmark in Chrome, and against a presigned URL with realistic latency, before deciding.

## Current scope and decisions

- Indexed MCAP with LZ4 and Zstandard chunks is supported on both paths.
- The browser uses `@mcap/core`, Foxglove ROS message parsing, `lz4js`, `zstddec`, and a Web Worker.
- The backend uses the Python `mcap` and `mcap-ros2-support` libraries.
- The renderer uses Three.js and displays intensity or reflectivity as grayscale.
- The neutral frame contract can later be cached, downsampled, merged, or produced by another backend
  without changing the renderer.

This first iteration intentionally excludes 3D bounding-box labeling, merged past/future frames, RGB
projection, interpolation, H265 video, multi-user annotation persistence, and model-assisted
labeling. After measuring the boundary, the next implementation should add 3D box interaction and
persist annotations through the existing multi-user annotation pipeline. Frame merging and RGB/video
synchronization should follow once the chosen processing boundary has a caching strategy.

## Known limitations

- The cached backend reader is a process-local dictionary with no eviction policy. It is enough to
  measure the boundary, not to serve concurrent users.
- Browser peak-memory measurement is omitted because the available API is not portable.
- Backend read count measures calls into the wrapped stream; a buffered remote filesystem may make
  fewer actual object-store requests.
- Remote sources are not re-validated once cached, because re-reading the ETag would add a request to
  every frame and hide the effect being measured.
- A presigned URL expiry/refresh service is outside this PoC.
