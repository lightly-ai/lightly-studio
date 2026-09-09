import { beforeEach, describe, expect, it, vi } from 'vitest';
import { canonicalCoordinateFrame, createPointCloudFrame } from '../domain';
import { probeFirstFrame } from './providerProbe';

const { resolveMcapSource, createMcapFrameProvider } = vi.hoisted(() => ({
    resolveMcapSource: vi.fn(),
    createMcapFrameProvider: vi.fn()
}));

vi.mock('../provider', async (importOriginal) => ({
    ...(await importOriginal<typeof import('../provider')>()),
    resolveMcapSource,
    createMcapFrameProvider
}));

const source = {
    recordingId: 'sample-1',
    version: 'rev-1',
    url: '/mcap/media/sample-1',
    sizeBytes: '1048576',
    coordinateFrame: canonicalCoordinateFrame('lidar'),
    logClockId: 'log',
    publishClockId: 'publish'
};

const supported = {
    channelId: 7,
    topic: '/lidar/points',
    schema: 'sensor_msgs/msg/PointCloud2',
    supported: true,
    messageCount: '900'
};

const locator = { channelId: 7, logTimeNs: '1789000000000000001', occurrence: 0 };

function frame() {
    return createPointCloudFrame({
        id: 'frame-1',
        source: { recordingId: 'sample-1', streamId: '7', messageId: 'm', publishedAt: null },
        timestamp: { nanoseconds: locator.logTimeNs, clockId: 'log' },
        coordinateFrame: canonicalCoordinateFrame('lidar'),
        sourcePointCount: 9000,
        positions: new Float32Array([1, 2, 3, 4, 5, 6]),
        cameras: []
    });
}

function provider(overrides: Record<string, unknown> = {}) {
    const dispose = vi.fn();
    createMcapFrameProvider.mockReturnValue({
        open: vi.fn(async () => ({
            topics: [supported],
            firstLogTimeNs: '1789000000000000000',
            lastLogTimeNs: '1789000000000000900'
        })),
        listFrames: vi.fn(async () => ({ frames: [locator], truncated: true })),
        loadFrame: vi.fn(async () => frame()),
        dispose,
        ...overrides
    });
    return dispose;
}

const callbacks = { onPhase: vi.fn(), onTelemetry: vi.fn() };

beforeEach(() => {
    vi.clearAllMocks();
    resolveMcapSource.mockResolvedValue(source);
});

describe('probeFirstFrame', () => {
    it('reports the recording, its channels, and the first decoded frame', async () => {
        const dispose = provider();

        const result = await probeFirstFrame('sample-1', source.url, callbacks);

        expect(result).toEqual({
            sizeBytes: '1048576',
            version: 'rev-1',
            topics: [supported],
            firstLogTimeNs: '1789000000000000000',
            lastLogTimeNs: '1789000000000000900',
            frameCount: 1,
            truncated: true,
            pointCount: 2,
            sourcePointCount: 9000,
            frameId: 'frame-1',
            logTimeNs: locator.logTimeNs
        });
        expect(resolveMcapSource).toHaveBeenCalledWith(
            expect.objectContaining({ sampleId: 'sample-1', coordinateFrameId: 'lidar' })
        );
        expect(dispose).toHaveBeenCalled();
    });

    it('rejects a recording with no supported channel', async () => {
        const dispose = provider({
            open: vi.fn(async () => ({
                topics: [{ ...supported, supported: false }],
                firstLogTimeNs: '1',
                lastLogTimeNs: '2'
            }))
        });

        await expect(probeFirstFrame('sample-1', source.url, callbacks)).rejects.toMatchObject({
            code: 'schema'
        });
        expect(dispose).toHaveBeenCalled();
    });

    it('rejects a channel with no frames in its time range', async () => {
        provider({ listFrames: vi.fn(async () => ({ frames: [], truncated: false })) });

        await expect(probeFirstFrame('sample-1', source.url, callbacks)).rejects.toMatchObject({
            code: 'source'
        });
    });

    it('disposes the provider when reading the frame fails', async () => {
        const dispose = provider({
            loadFrame: vi.fn().mockRejectedValue(new Error('range failed'))
        });

        await expect(probeFirstFrame('sample-1', source.url, callbacks)).rejects.toThrow(
            /range failed/
        );
        expect(dispose).toHaveBeenCalled();
    });
});
