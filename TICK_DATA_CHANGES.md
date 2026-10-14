# One request per tick: tick data endpoint

## Why

The point-cloud workspace used to request each sensor channel of a tick on its own: one `/point-cloud` request per lidar and one `/camera-frame` request per camera. Each request read the S3-backed MCAP file separately, so a tick with 3 lidars and 5 cameras cost 8 requests and 8 reads.

The GUI now asks for a tick's data with **one request**. The backend reads every channel of that tick in **one pass** over the MCAP file, decodes each channel by its media type, and returns everything in one response.

## How it works

1. The GUI requests `GET /datasets/{dataset_id}/mcap-sequences/{sequence_id}/ticks/{seq_number}/data`.
2. The backend resolves the tick to its recording and the locator of each channel (channel id, log time, and keyframe for video).
3. It computes one read window, from the smallest to the largest log time of the tick's channels.
   - A camera whose cached decoder cannot continue needs to start at its keyframe, so the window starts there.
   - A camera whose cached decoder can continue only needs the messages after its last decoded frame.
4. It reads all channels with **one** `get_decoded_messages_in_range` call, which returns the messages grouped by channel.
5. It decodes each channel's message at its locator log time:
   - **Point cloud**: transformed to the display frame and serialized as an Arrow IPC stream. If no transform reaches the display frame, the points stay in the sensor frame. The Arrow `frame_id` tells the frame they are in.
   - **Camera**: decoded with the cached `VideoDecoder` and encoded as a JPEG, scaled to `camera_height` (the frontend sends 360 px).
6. It returns one response with one payload per channel.

### Query parameters

| Name | Type | Meaning |
|---|---|---|
| `target_frame_id` | string, optional | Frame to express the points in. Omit to keep the sensor frames. |
| `camera_height` | int > 0, optional | Height of the camera JPEGs in pixels, keeping the aspect ratio. Omit for full size. |

### Response body

`application/octet-stream`, a concatenation of payloads. Each payload has a 21-byte little-endian header, then its bytes:

| Field | Type | Meaning |
|---|---|---|
| `channel_id` | u32 | MCAP channel the payload was read from |
| `kind` | u8 | `0` = Arrow IPC point cloud, `1` = JPEG camera frame |
| `log_time_ns` | u64 | Log time of the message |
| `length` | u64 | Number of payload bytes that follow |

Point clouds come first, then camera frames. A channel without a message at its locator log time is left out and logged as a warning.

Errors: 404 for an unknown tick (or one outside the dataset), 400 if a channel is missing from the file or a message cannot be decoded.

### Expected size

A tick with 3 lidars and 5 cameras is about 6–7 MB, mostly lidar data (about 1.5–2 MB per lidar). Scaling the camera images to 360 px cuts the camera share by roughly 5–10x compared with full resolution.

## Backend changes (`lightly_studio/`)

| File | Change |
|---|---|
| `core/mcap/reader/file_reader.py` | `get_decoded_messages_in_range` takes `channel_ids: Sequence[int]` and returns `dict[int, list[DecodedMessage]]`. It reads the overlapping chunks once for all channels. `get_decoded_message_at` wraps it. |
| `services/recording_service/resolve_tick.py` (new) | `resolve_tick(...)`: sequence → tick link → channel locators. Shared by `get_tick_details` and `get_tick_data`. |
| `services/recording_service/get_tick_data.py` (new) | `get_tick_data(...)`: the read and decode flow above. Defines `TickPayload` and `TickPayloadKind`. |
| `services/recording_service/encode_point_cloud_message.py` (new) | Encodes one point-cloud message, with the per-message transform and the sensor-frame fallback. Moved out of the removed `get_point_cloud.py`. |
| `services/recording_service/get_camera_frame.py` | The decoder feed loop is now public as `decode_camera_frame`, together with `feed_start_ns` and `store_decoder`, so `/camera-frame` and the tick service share it. |
| `services/recording_service/get_tick_details.py` | Uses `resolve_tick`. Behavior unchanged. |
| `api/routes/mcap_sequences/get_tick_data.py` (new) | The route. |
| `api/routes/mcap_sequences/tick_payload_encoding.py` (new) | The binary framing of the response body. |

### Removed

- The `/point-cloud` route and its service (`api/routes/recordings/get_point_cloud.py`, `services/recording_service/get_point_cloud.py`) and their tests.

### Kept

- `/camera-frame`, unchanged for callers. The sequence grid thumbnails use it, and the enlarge dialog uses it for the full-resolution frame.

## Frontend changes (`lightly_studio_view/`)

| File | Change |
|---|---|
| `src/lib/hooks/useTickData/` (new) | `decodeTickPayloads` parses the body, keeping 64-bit log times exact as strings. `fetchTickData` returns `{ pointClouds, cameraFrames }`. `getTickDataOptions` is the single cached query per tick, keyed by `['tick-data', datasetId, sequenceId, seqNumber, displayFrameId]`. `useTickCameraFrames` selects the camera images. |
| `useCloudPointFrame` | Reads the tick-data query and merges the point clouds of the selected lidars in `select`. Toggling lidars no longer refetches. The return type is unchanged. Its params are now `{ datasetId, sequenceId, seqNumber, displayFrameId?, selectedChannelIds? }`. |
| `pointCloudWorkspace.svelte.ts` | Passes the tick instead of per-channel locators. |
| `CameraProjectionStrip` / `CameraProjectionFrame` | Each tile shows the JPEG from the tick data through an object URL, revoked on change or unmount. The enlarge dialog loads the full-resolution frame from `/camera-frame` when it opens. |
| `prefetchMcapTick` | Prefetches the tick details and the tick data: two requests per tick, regardless of the channel count. The scheduler, queue and chunking are unchanged. |

### Removed

- `fetchCloudPointFrame`, `fetchMergedCloudPointFrame`, `getCloudPointFrameOptions`, `prefetchCameraFrame`, and their tests.

## Tests

- **Backend**:
  - `tests/core/mcap/test_reader.py`: adapted to the new signature, plus one test that reads two channels in one call.
  - New `tests/services/recording_service/test_get_tick_data.py`: a tick returns one point cloud and one JPEG, with a real H.264 delta frame decoded from its keyframe and scaled to `camera_height`; an unknown tick returns `None`.
  - New `tests/api/routes/mcap_sequences/test_get_tick_data.py`: decodes the body; an unknown tick returns 404.
  - `tests/core/mcap/helpers.py`: `write_mcap` takes optional `video_access_units`, so the test MCAP can carry decodable H.264.
- **Frontend**:
  - New `decodeTickPayloads.test.ts`.
  - Updated tests for `useCloudPointFrame`, `prefetchMcapTick`, `CameraProjectionFrame`, and `CameraProjectionStrip`, and hook mocks in the workspace and page tests.

### Results

- Frontend: all 466 test files pass; `svelte-check` and eslint are clean.
- Backend: ruff and mypy are clean. The MCAP, recording-service and route tests pass, except `test_read_cache_options__random`, which already failed on the branch (the test expects `readahead`, while `session.py` sets `blockcache`). The full suite also has failures in image import, video, export, server and database tests, outside this change and not checked against the branch head.

## Not yet verified

- An end-to-end run in the app. Run `example_mcap.py`, open a point-cloud sequence, and check:
  - the network tab shows one `/ticks/{n}/data` request per tick, with no `/point-cloud` calls and a `/camera-frame` call only when a tile is enlarged;
  - the point clouds and camera tiles render and follow playback;
  - the backend log shows one `Tick N: … read … decode …` line per tick.
