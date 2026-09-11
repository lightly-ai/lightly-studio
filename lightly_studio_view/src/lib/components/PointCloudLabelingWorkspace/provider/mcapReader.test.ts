import { afterEach, describe, expect, it, vi } from 'vitest';
import { decompress } from 'lz4js';
import { canonicalCoordinateFrame, createPointCloudFrame } from '../domain';
import { mcapFixture, RIGHT_LIDAR_MOUNT } from './mcapFixture';
import { openMcap } from './mcapReader';

// Spied rather than replaced: listing frames must not decompress a single chunk, while
// decoding one obviously has to.
vi.mock('lz4js', async (importOriginal) => {
    const actual = await importOriginal<typeof import('lz4js')>();
    return { ...actual, decompress: vi.fn(actual.decompress) };
});

afterEach(() => vi.unstubAllGlobals());

function serve(bytes: Uint8Array) {
    // The zstd decoder loads its WASM through a `data:` URL, so only the
    // recording request is served from the fixture.
    const passthrough = globalThis.fetch;
    vi.stubGlobal(
        'fetch',
        vi.fn<typeof fetch>(async (url, options) => {
            if (url !== '/recording') return passthrough(url, options);
            // Read the record directly: jsdom's `Headers` drops `Range`.
            const range = (options?.headers as Record<string, string>).Range;
            const [, start, end] = /^bytes=(\d+)-(\d+)$/.exec(range)!;
            return new Response(bytes.slice(Number(start), Number(end) + 1), {
                status: 206,
                headers: { 'Content-Range': `bytes ${start}-${end}/${bytes.length}` }
            });
        })
    );
}

function sourceFor(bytes: Uint8Array, coordinateFrameId = 'lidar') {
    return {
        recordingId: 'r',
        version: 'v1',
        url: '/recording',
        sizeBytes: String(bytes.length),
        coordinateFrame: canonicalCoordinateFrame(coordinateFrameId),
        logClockId: 'log',
        publishClockId: 'publish'
    };
}

describe('openMcap', () => {
    it('reads real MCAP ranges, exposes topics, and disambiguates duplicate timestamps', async () => {
        const { bytes, channelId, unsupportedChannelId, timestamp } = await mcapFixture();
        serve(bytes);
        const session = await openMcap(sourceFor(bytes), new AbortController().signal);
        expect(session.metadata.topics).toEqual([
            {
                channelId,
                topic: '/lidar',
                schema: 'sensor_msgs/msg/PointCloud2',
                supported: true,
                messageCount: '2'
            },
            {
                channelId: unsupportedChannelId,
                topic: '/imu',
                schema: 'sensor_msgs/msg/Imu',
                supported: false,
                messageCount: '1'
            }
        ]);
        const range = await session.listFrames(
            channelId,
            timestamp.toString(),
            timestamp.toString()
        );
        expect(range.frames.map((frame) => frame.occurrence)).toEqual([0, 1]);
        const first = createPointCloudFrame(await session.loadFrame(range.frames[0], 10));
        const second = createPointCloudFrame(await session.loadFrame(range.frames[1], 10));
        expect(first.id).not.toBe(second.id);
        expect(first.positions.copy()).toEqual(new Float32Array([1, 2, 3]));
        expect(second.positions.copy()).toEqual(new Float32Array([4, 2, 3]));
        expect(first.timestamp.nanoseconds).toBe('1789000000000000001');
        expect(first.source.publishedAt?.nanoseconds).toBe('1789000000000000000');
        expect(
            (await session.listFrames(channelId, timestamp.toString(), timestamp.toString(), 1))
                .truncated
        ).toBe(true);
        await expect(
            session.loadFrame({ channelId, logTimeNs: timestamp.toString(), occurrence: 2 }, 10)
        ).rejects.toMatchObject({ code: 'source' });
    });

    it('reads lz4-compressed chunks', async () => {
        const { bytes, channelId, timestamp } = await mcapFixture({ compressed: true });
        serve(bytes);
        const session = await openMcap(sourceFor(bytes), new AbortController().signal);
        const range = await session.listFrames(
            channelId,
            timestamp.toString(),
            timestamp.toString()
        );
        const frame = createPointCloudFrame(await session.loadFrame(range.frames[0], 10));
        expect(frame.positions.copy()).toEqual(new Float32Array([1, 2, 3]));
    });

    it('lists a window from the message index, without decompressing chunks', async () => {
        const { bytes, channelId, timestamp } = await mcapFixture({ compressed: true });
        serve(bytes);
        const session = await openMcap(sourceFor(bytes), new AbortController().signal);
        vi.mocked(decompress).mockClear();
        const readBefore = session.readable.bytesRead;

        const range = await session.listFrames(
            channelId,
            timestamp.toString(),
            timestamp.toString()
        );

        expect(range.frames.map((frame) => frame.occurrence)).toEqual([0, 1]);
        expect(decompress).not.toHaveBeenCalled();
        // The index region is a fraction of the chunk it belongs to.
        expect(session.readable.bytesRead - readBefore).toBeLessThan(bytes.length / 4);

        await session.loadFrame(range.frames[0], 10);
        expect(decompress).toHaveBeenCalled();
    });

    it('rejects recordings without identity, version, or clock metadata', async () => {
        const { bytes } = await mcapFixture();
        serve(bytes);
        const signal = new AbortController().signal;
        await expect(openMcap({ ...sourceFor(bytes), version: '' }, signal)).rejects.toMatchObject({
            code: 'source'
        });
        await expect(
            openMcap({ ...sourceFor(bytes), logClockId: '' }, signal)
        ).rejects.toMatchObject({ code: 'source' });
    });

    it('rejects unsupported channels, malformed locators, and invalid ranges', async () => {
        const { bytes, channelId, unsupportedChannelId, timestamp } = await mcapFixture();
        serve(bytes);
        const session = await openMcap(sourceFor(bytes), new AbortController().signal);
        const logTimeNs = timestamp.toString();
        await expect(
            session.loadFrame({ channelId: unsupportedChannelId, logTimeNs, occurrence: 0 }, 10)
        ).rejects.toMatchObject({ code: 'schema' });
        await expect(
            session.loadFrame({ channelId: 4096, logTimeNs, occurrence: 0 }, 10)
        ).rejects.toMatchObject({ code: 'schema' });
        await expect(
            session.loadFrame({ channelId, logTimeNs: '-1', occurrence: 0 }, 10)
        ).rejects.toMatchObject({ code: 'source' });
        await expect(
            session.loadFrame({ channelId, logTimeNs, occurrence: -1 }, 10)
        ).rejects.toMatchObject({ code: 'source' });
        await expect(session.listFrames(channelId, logTimeNs, '1')).rejects.toMatchObject({
            code: 'source'
        });
        await expect(session.listFrames(channelId, logTimeNs, logTimeNs, 0)).rejects.toMatchObject({
            code: 'source'
        });
        await expect(
            session.listFrames(channelId, logTimeNs, logTimeNs, 1001)
        ).rejects.toMatchObject({ code: 'source' });
    });
});

describe('openMcap with several lidar channels', () => {
    async function fusedSession(coordinateFrameId = 'CABIN') {
        const fixture = await mcapFixture({ fused: true });
        serve(fixture.bytes);
        const session = await openMcap(
            sourceFor(fixture.bytes, coordinateFrameId),
            new AbortController().signal
        );
        return { ...fixture, session };
    }

    it('fuses every lidar into the frame, placed by /tf_static', async () => {
        const { session, channelId, timestamp } = await fusedSession();

        const range = await session.listFrames(
            channelId,
            timestamp.toString(),
            timestamp.toString()
        );
        const frame = createPointCloudFrame(await session.loadFrame(range.frames[0], 10));

        // The read channel's own point, then the other sensor's origin at its mount: the
        // second sensor is what a single-channel read leaves as empty space.
        expect([...frame.positions.copy()]).toEqual([
            1,
            2,
            3,
            RIGHT_LIDAR_MOUNT.x,
            RIGHT_LIDAR_MOUNT.y,
            RIGHT_LIDAR_MOUNT.z
        ]);
        expect(frame.sourcePointCount).toBe(2);
    });

    it('reports the frame everything was aligned into, not the sensor frame', async () => {
        const { session, channelId, timestamp } = await fusedSession();
        const range = await session.listFrames(
            channelId,
            timestamp.toString(),
            timestamp.toString()
        );

        const frame = await session.loadFrame(range.frames[0], 10);

        expect(frame.coordinateFrame.id).toBe('CABIN');
    });

    it('keeps frame identity on the channel the frame was listed on', async () => {
        const { session, channelId, rightChannelId, timestamp } = await fusedSession();
        const range = await session.listFrames(
            channelId,
            timestamp.toString(),
            timestamp.toString()
        );

        const frame = await session.loadFrame(range.frames[0], 10);

        expect(frame.source.streamId).toBe(String(channelId));
        expect(frame.source.streamId).not.toBe(String(rightChannelId));
    });

    it('falls back to the read channel frame when the target is not in /tf_static', async () => {
        const { session, channelId, timestamp } = await fusedSession('VEHICLE');
        const range = await session.listFrames(
            channelId,
            timestamp.toString(),
            timestamp.toString()
        );

        const frame = createPointCloudFrame(await session.loadFrame(range.frames[0], 10));

        // 'lidar' sits at the CABIN origin here, so the other sensor still resolves into it.
        expect(frame.coordinateFrame.id).toBe('lidar');
        expect(frame.positions.length).toBe(6);
    });

    it('splits the point budget across the channels it fuses', async () => {
        const { session, channelId, timestamp } = await fusedSession();
        const range = await session.listFrames(
            channelId,
            timestamp.toString(),
            timestamp.toString()
        );

        // One point per sweep survives a budget of one point per channel.
        const frame = await session.loadFrame(range.frames[0], 2);

        expect(frame.positions.length).toBe(6);
    });

    it('refuses to align lidars a recording gives no transforms for', async () => {
        const { bytes, channelId, timestamp } = await mcapFixture({
            fused: true,
            omitTransforms: true
        });
        serve(bytes);
        const session = await openMcap(sourceFor(bytes, 'CABIN'), new AbortController().signal);
        const range = await session.listFrames(
            channelId,
            timestamp.toString(),
            timestamp.toString()
        );

        await expect(session.loadFrame(range.frames[0], 10)).rejects.toMatchObject({
            code: 'source'
        });
    });
});
