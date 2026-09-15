# LIG-8835 direct-media POC benchmark and OSS findings

This isolated Playwright harness compares the same visible image grid under three delivery
conditions and the same video under direct and proxy delivery. It does not change the ordinary
E2E performance suites or enforce an invented pass/fail latency threshold.

## Reproduce the benchmark

Start an image or video E2E environment whose indexed originals are in AWS S3, enable
`LIGHTLY_STUDIO_MEDIA_DIRECT_URLS`, and run the matching command:

```shell
LIG_8835_COMMIT=$(git rev-parse HEAD) \
LIG_8835_DATASET=<sanitized-name> \
LIG_8835_OBJECT_SET=<sanitized-id> \
LIG_8835_BUCKET_REGION=<region> \
LIG_8835_BACKEND_REGION=<region> \
LIG_8835_BROWSER_REGION=<region> \
LIG_8835_BACKEND_PID=<pid> npm run benchmark:media:images

LIG_8835_COMMIT=$(git rev-parse HEAD) \
LIG_8835_DATASET=<sanitized-name> \
LIG_8835_OBJECT_SET=<sanitized-id> \
LIG_8835_BUCKET_REGION=<region> \
LIG_8835_BACKEND_REGION=<region> \
LIG_8835_BROWSER_REGION=<region> \
LIG_8835_BACKEND_PID=<pid> npm run benchmark:media:videos
```

Each condition runs ten times by default. Condition order rotates for each repetition. A fresh
browser context is used for every measurement; set `LIG_8835_CACHE_STATE=warm` to run repeat
navigation in one context and label it accordingly. `LIG_8835_REPETITIONS` is available for a
smoke test only. The harness rewrites only the supported `mode`, `quality`, and size query
parameters to select a condition; it does not intercept response data, inject failures, or trigger
the recovery path. Direct runs fail if they observe a Studio media body or a failed storage read.

Results are written to `test-results/lig-8835/images.json` and `videos.json`. The files retain
every measurement, median/range summaries, decode-completion fractions, seek buffering state,
media dimensions/duration, sanitized request evidence, inferred Studio/storage media-body bytes,
concurrent `/api/features` latency, and optional sampled backend CPU/peak RSS. URLs retain neither query strings, bucket
names, object keys, nor sample IDs; stable hashes allow requests to be correlated. Fill in the
run metadata and supplement it with object size/dimensions or duration/codec and host resources.
Process-level network counters require an external monitor because the portable browser harness
cannot attribute host network traffic to one backend process.

The image benchmark temporarily selects high-quality thumbnails through the settings API so the
application requests the actual rendered dimensions. It restores the prior setting afterward.
Request rewriting then selects proxy originals, direct originals, or proxy resized thumbnails
without changing server configuration between measurements.

## OSS findings (2026-09-11)

| POC question                                 | Current OSS evidence                                                                                                                                                                                 | Status                                                                                         |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Raw images and videos without CORS           | Normal `<img>`/`<video>` delivery does not require readable cross-origin response data. Pixel-reading, crops, frames, posters, and resized thumbnails remain explicitly proxied.                     | Implemented; the no-CORS claim still needs the isolated header-stripping browser matrix.       |
| Expired video URL before seek/resume         | Recovery preserves time, rate, and paused/playing intent and makes one proxy source replacement.                                                                                                     | Automated component coverage exists; a real short-TTL, unbuffered browser run remains pending. |
| Browser-only storage failure                 | Each image/video item has one bounded proxy recovery attempt; proxy failure is terminal rather than alternating sources.                                                                             | Automated frontend coverage exists; real-browser abort/403/stall evidence remains pending.     |
| Direct versus proxy performance              | This harness records visible-grid decode completion, video first frame/seek/resume, media request/body evidence, lightweight API latency, and optional backend CPU/RSS under alternating conditions. | Local image/video results captured; hosted representative measurements remain pending.         |
| Credential rotation and same-key replacement | Signing resolves credentials per request and the existing credential update clears filesystem caches. Redirects and signed responses are uncached.                                                   | Dedicated credentials and disposable replacement objects are deferred to hosted validation.    |

Manual provider validation confirmed that an eligible whole-video application request returns a
`307`, followed by a region-correct S3 request that serves browser byte ranges with `206 Partial
Content`. Explicit `mode=proxy` remains available for recovery. Signed query strings, bucket
names, object keys, and credentials are intentionally absent from this report.

Hosted auth-chain, credential-rotation, same-key replacement, and final topology measurements
remain a separate validation checkpoint.

## Local S3 image benchmark (2026-09-14)

The image benchmark completed ten cold-browser repetitions per condition with a 1600×1200
viewport. The browser and backend ran locally, application traffic used loopback, and the S3
bucket region was not recorded. All 32 visible images decoded in every repetition with zero media
failures.

| Condition                | First decode, median (range) | Full visible grid, median (range) |                        Media body per run |
| ------------------------ | ---------------------------: | --------------------------------: | ----------------------------------------: |
| Proxy originals          |            647 ms (594–1197) |                 936 ms (906–1581) |                   5,166,383 B from Studio |
| Direct originals         |            691 ms (658–1470) |                1109 ms (994–1518) | 5,166,383 B from storage; 0 B from Studio |
| Proxy resized thumbnails |            647 ms (609–1388) |               969.5 ms (893–1645) |                     155,281 B from Studio |

On this topology, direct originals removed all original-image body traffic from Studio but had an
18.5% slower median full-grid completion than proxy originals. Resized thumbnails transferred 97%
fewer bytes than originals and completed 3.6% slower than proxy originals at the median. Sampled
peak CPU medians were 52.7% for proxy originals, 53.7% for direct originals, and 56.7% for resized
thumbnails; these short, interleaved samples are too noisy to establish a CPU improvement. Median
concurrent `/api/features` latency stayed between 3.2 and 4.1 ms. Backend RSS rose with process
warmth across the run, so its per-condition peaks are not interpreted as a delivery-mode effect.

The sanitized raw artifact is `test-results/lig-8835/images.json` and remains outside version
control. A hosted or representative remote-browser run is still required before drawing a product
performance conclusion.

## Local S3 video benchmark (2026-09-14)

The video benchmark completed ten cold-browser repetitions per condition against the same
1280×720, 1.9-second video. The browser and backend ran locally, application traffic used
loopback, and the S3 bucket region was not recorded.

| Condition | Play to first frame, median (range) | Details to first frame, median (range) |   Seek, median (range) | Resume, median (range) |
| --------- | ----------------------------------: | -------------------------------------: | ---------------------: | ---------------------: |
| Proxy     |              383.8 ms (166.6–427.1) |                    2810 ms (2559–3216) |  110.3 ms (93.1–131.4) |    92.1 ms (83.3–99.8) |
| Direct    |                77.0 ms (40.6–150.8) |                  2429.5 ms (2344–2708) | 134.9 ms (115.8–140.9) |   91.7 ms (83.2–100.1) |

Direct delivery reduced median play-to-first-frame time by 80% and details-to-first-frame time by
13.5%. It served zero video-body bytes through Studio; successful storage responses transferred
571,307 bytes per run. Proxy delivery transferred a median 1,025,793 bytes per run through Studio.
Resume timing was effectively equal.

Seek latency is not directly comparable in this run: the target was already buffered in all ten
proxy measurements and unbuffered in all ten direct measurements. Chromium cancelled superseded
Range requests during seeking (one per direct run and one or two per proxy run); playback, seek,
and resume still completed, direct runs received successful S3 `206` bodies, and no direct run
recovered through a Studio media body. Sampled peak CPU medians were 122.0% for proxy and 119.9%
for direct; the short multi-core samples are too noisy for a CPU conclusion. Median concurrent
`/api/features` latency was 3.1 ms for proxy and 3.7 ms for direct.

The sanitized raw artifact is `test-results/lig-8835/videos.json` and remains outside version
control. The short video and unequal seek-buffer state limit generalization; repeat with a longer
representative video and a controlled unbuffered target before setting production policy.
