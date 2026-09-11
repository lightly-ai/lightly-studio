import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createCameraReader, type CameraChannel, type CameraMessage } from './cameraFrames';

const identity = {
    recordingId: 'recording-0',
    logClockId: 'log',
    publishClockId: 'publish',
    maxWidth: 480,
    stillWindowNs: 100_000_000n,
    videoLookbackNs: 4_000_000_000n
};

const stills: CameraChannel = {
    channelId: 3,
    topic: '/camera_front/image',
    encoding: 'compressed-image'
};
const video: CameraChannel = {
    channelId: 4,
    topic: '/camera_rear/video',
    encoding: 'compressed-video'
};

function message(logTimeNs: bigint, value: unknown): CameraMessage {
    return { logTimeNs, publishTimeNs: logTimeNs - 1n, value };
}

/** A NAL unit an H.264 stream can be joined at. */
const keyframe = new Uint8Array([0, 0, 0, 1, 0x65, 9]);
const delta = new Uint8Array([0, 0, 0, 1, 0x41, 9]);

let decoded: unknown[] = [];

beforeEach(() => {
    decoded = [];
    vi.stubGlobal(
        'createImageBitmap',
        vi.fn(async (source: unknown) => {
            decoded.push(source);
            return { width: 480, height: 270, close: vi.fn() } as unknown as ImageBitmap;
        })
    );
    vi.stubGlobal('VideoDecoder', undefined);
});

afterEach(() => vi.unstubAllGlobals());

describe('createCameraReader', () => {
    it('shows the still nearest the moment, and describes where it came from', async () => {
        const reader = createCameraReader({
            ...identity,
            readWindow: async () => [
                message(900n, { format: 'jpeg', data: new Uint8Array([1]) }),
                message(1_050n, { format: 'jpeg', data: new Uint8Array([2]) })
            ]
        });

        const { cameras, images } = await reader.read([stills], 1_000n);

        expect(cameras).toHaveLength(1);
        expect(cameras[0]).toMatchObject({
            id: '/camera_front/image',
            width: 480,
            height: 270,
            calibration: null,
            timestamp: { nanoseconds: '1050', clockId: 'log' },
            source: { recordingId: 'recording-0', streamId: '3' }
        });
        expect(cameras[0].image).toEqual({ kind: 'decoded', resourceId: '3:1050' });
        expect(images[0].resourceId).toBe('3:1050');
    });

    it('reads each camera around the frame it was asked for', async () => {
        const windows: [bigint, bigint][] = [];
        const reader = createCameraReader({
            ...identity,
            readWindow: async (_channel, startNs, endNs) => {
                windows.push([startNs, endNs]);
                return [message(1_000n, { format: 'jpeg', data: new Uint8Array([1]) })];
            }
        });

        await reader.read([stills], 1_000_000_000n);

        expect(windows).toEqual([[900_000_000n, 1_100_000_000n]]);
    });

    it('leaves out a camera with nothing to show rather than failing the frame', async () => {
        const reader = createCameraReader({ ...identity, readWindow: async () => [] });

        const { cameras, images } = await reader.read([stills], 1_000n);

        expect(cameras).toEqual([]);
        expect(images).toEqual([]);
    });

    it('leaves out a camera whose picture will not decode', async () => {
        vi.stubGlobal(
            'createImageBitmap',
            vi.fn(async () => {
                throw new Error('unsupported image');
            })
        );
        const reader = createCameraReader({
            ...identity,
            readWindow: async () => [message(1_000n, { format: 'jpeg', data: new Uint8Array() })]
        });

        expect((await reader.read([stills], 1_000n)).cameras).toEqual([]);
    });

    it('decodes video from the keyframe the moment depends on', async () => {
        const fed: string[] = [];
        vi.stubGlobal(
            'EncodedVideoChunk',
            class {
                constructor(init: { type: string }) {
                    fed.push(init.type);
                    return init as never;
                }
            }
        );
        vi.stubGlobal(
            'VideoDecoder',
            class {
                static isConfigSupported = async () => ({ supported: true });
                state = 'unconfigured';
                #output: (frame: unknown) => void;
                constructor({ output }: { output: (frame: unknown) => void }) {
                    this.#output = output;
                }
                configure() {
                    this.state = 'configured';
                }
                decode() {
                    this.#output({ displayWidth: 1920, close: vi.fn() });
                }
                async flush() {}
                close() {
                    this.state = 'closed';
                }
            }
        );
        const reader = createCameraReader({
            ...identity,
            readWindow: async () => [
                message(800n, { format: 'h264', data: keyframe }),
                message(900n, { format: 'h264', data: delta }),
                // Past the moment asked for: the picture shown is the one before it.
                message(1_100n, { format: 'h264', data: delta })
            ]
        });

        const { cameras } = await reader.read([video], 1_000n);

        expect(fed).toEqual(['key', 'delta']);
        expect(cameras[0].timestamp.nanoseconds).toBe('900');
        reader.close();
    });

    it('leaves out video whose keyframe is outside the window it looked in', async () => {
        const reader = createCameraReader({
            ...identity,
            readWindow: async () => [message(900n, { format: 'h264', data: delta })]
        });

        expect((await reader.read([video], 1_000n)).cameras).toEqual([]);
    });
});
