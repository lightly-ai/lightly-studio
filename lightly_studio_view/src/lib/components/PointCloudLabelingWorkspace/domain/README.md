# Point-cloud labeling contracts

Import the public contracts and constructors from `./domain`. Fixtures are a separate
`./domain/fixtures` entry point so production consumers do not load test data. This
module has no UI framework, renderer, or generated transport dependencies. Named types
are exported intentionally: this issue defines the shared boundary for future adapters.

## Coordinates and time

Point positions, bounds and cuboid centres use meters in a right-handed frame with
x forward, y left and z up. A frame ID identifies both the axes and origin; two
different IDs cannot be mixed even if their conventions match. Providers must convert
source units and axes before constructing a frame. `assertCompatibleCoordinates`
rejects implicit conversion; it does not perform a transform.

Cuboid sizes are full local-axis extents, not half extents. Rotations are unit xyzw
quaternions, actively rotating local vectors into the annotation's coordinate frame.
Positive angles follow the right-hand rule. Renderers with y-up conventions must apply
an explicit adapter transform, leaving canonical annotations unchanged. Persistence
stores the same `CuboidAnnotation` shape, including its coordinate frame, without
Euler-angle conversion. IDs are opaque strings; annotation IDs identify individual
frame annotations, track IDs link objects across frames, and keyframe IDs identify
explicit track anchors. Untracked annotations use null for both track and keyframe.
Tracked annotations with a null keyframe are interpolated; tracked annotations with a
keyframe ID are authored anchors.

Timestamps are decimal integer nanoseconds and carry a clock ID. Use `BigInt` for
arithmetic and compare only matching clocks. Camera timestamps are independent of
point-cloud timestamps; temporal alignment is the provider's responsibility. The frame
timestamp is recording timeline time (`logTime` for MCAP). `source.publishedAt` preserves
publication time and its clock separately. `source` also identifies the recording, stream,
and individual message. Providers must derive stable frame IDs from that identity, including
a message locator to disambiguate equal timestamps. A downsampled version of the same message
retains its frame ID so annotations survive point-budget changes.

Calibrated camera images are rectified pinhole images. Calibration maps optical camera coordinates
(x right, y down, z forward) into the named point-cloud frame with
`p_cloud = R(q) * p_camera + translation`. Intrinsics use pixels, with the top-left
pixel centre at (0, 0). Unrectified imagery must be rectified by an adapter before attaching
calibration, though it may be displayed without calibration. Missing imagery and missing
calibration are independent null values; an empty camera array means no camera context is
available. Camera adapters may expose a URI or register a decoded resource such as an
`ImageBitmap`; they own and dispose decoded resources outside the immutable domain model.

## Ownership and availability

Use `createPointCloudFrame` and `createCuboidAnnotation` at domain entry points.
They copy owned input data and freeze metadata/geometry. Packed point attributes expose
only `length` and `copy()`, which returns a fresh Float32Array for renderer upload or
worker transfer. `PointCloudFrameTransfer` is structured-cloneable and
`exportPointCloudFrame` creates disposable buffers that can safely be transferred without
detaching the cached canonical frame. Cache a copied buffer per renderer frame rather than
copying every render.
These constructors validate geometry and packing, not arbitrary transport payloads;
transport adapters still validate IDs and camera metadata before constructing them.

Positions are consecutive xyz triples. Optional intensity has one normalized value per
point; optional color has three linear RGB values per point. Adapters normalize sensor
intensity and convert sRGB/byte colors before entry. Bounds are derived from positions,
with null for an empty frame. `sourcePointCount` records the number before filtering or
deterministic downsampling. Missing optional attributes are undefined, distinct from an
empty loaded frame. Loading/error state belongs to the future provider contract.

Interaction state is separate from frame and annotation data. Selection/hover reference
annotation IDs in the active frame. Dirty upserts and deletions must be disjoint. Save
adapters capture a revision and clear only the changes acknowledged by that save, retaining
edits made while the request was in flight.

Fixtures allocate fresh deterministic data on demand: empty, normal, 350,000-point,
partially available and malformed provider inputs. Malformed inputs deliberately bypass
construction so rejection can be tested. Camera, annotation class, annotation, track and
interaction fixtures share IDs for integration tests.
