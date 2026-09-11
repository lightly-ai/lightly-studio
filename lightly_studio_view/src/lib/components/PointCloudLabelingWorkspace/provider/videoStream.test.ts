import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createVideoStream } from './videoStream';
import type { VideoChunk } from './videoChunks';

/** Chunks fed to the most recent decoder, and how many decoders were built. */
let fed: { type: string; timestamp: number }[] = [];
let decodersOpened = 0;
let closed = 0;

class FakeVideoFrame {
    displayWidth = 1920;
    close = vi.fn();
}

class FakeVideoDecoder {
    static isConfigSupported = vi.fn(async () => ({ supported: true }));
    state = 'unconfigured';
    #output: (frame: unknown) => void;

    constructor({ output }: { output: (frame: unknown) => void }) {
        this.#output = output;
        decodersOpened += 1;
    }

    configure() {
        this.state = 'configured';
    }

    decode(chunk: { type: string; timestamp: number }) {
        fed.push(chunk);
        this.#output(new FakeVideoFrame());
    }

    async flush() {}

    close() {
        this.state = 'closed';
        closed += 1;
    }
}

const chunk = (logTimeNs: bigint): VideoChunk => ({ logTimeNs, data: new Uint8Array([1]) });

beforeEach(() => {
    fed = [];
    decodersOpened = 0;
    closed = 0;
    vi.stubGlobal('VideoDecoder', FakeVideoDecoder);
    vi.stubGlobal(
        'EncodedVideoChunk',
        class {
            constructor(public init: { type: string; timestamp: number }) {
                return init as never;
            }
        }
    );
    vi.stubGlobal(
        'createImageBitmap',
        vi.fn(async () => ({ width: 320 }) as ImageBitmap)
    );
});

afterEach(() => vi.unstubAllGlobals());

describe('createVideoStream', () => {
    it('feeds the group from its keyframe and returns its last picture', async () => {
        const stream = createVideoStream('h264', 320);

        const picture = await stream.decode([chunk(10n), chunk(20n)]);

        expect(picture).not.toBeNull();
        expect(fed.map((item) => item.type)).toEqual(['key', 'delta']);
    });

    it('feeds only what is new when the next picture continues the same group', async () => {
        const stream = createVideoStream('h264', 320);

        await stream.decode([chunk(10n), chunk(20n)]);
        fed = [];
        await stream.decode([chunk(10n), chunk(20n), chunk(30n)]);

        // The group is not replayed: stepping forward costs one chunk, not three.
        expect(fed).toHaveLength(1);
        expect(fed[0].type).toBe('delta');
        expect(decodersOpened).toBe(1);
    });

    it('starts over when the picture belongs to a later group', async () => {
        const stream = createVideoStream('h264', 320);

        await stream.decode([chunk(10n), chunk(20n)]);
        fed = [];
        await stream.decode([chunk(40n), chunk(50n)]);

        expect(fed.map((item) => item.type)).toEqual(['key', 'delta']);
        expect(decodersOpened).toBe(2);
        expect(closed).toBe(1);
    });

    it('starts over when stepping backwards inside a group', async () => {
        const stream = createVideoStream('h264', 320);

        await stream.decode([chunk(10n), chunk(20n), chunk(30n)]);
        fed = [];
        await stream.decode([chunk(10n)]);

        expect(fed.map((item) => item.type)).toEqual(['key']);
        expect(decodersOpened).toBe(2);
    });

    it('has nothing to decode without a keyframe to start from', async () => {
        const stream = createVideoStream('h264', 320);

        expect(await stream.decode([])).toBeNull();
        expect(decodersOpened).toBe(0);
    });

    it('reports a codec the browser will not decode', async () => {
        FakeVideoDecoder.isConfigSupported.mockResolvedValueOnce({ supported: false });
        const stream = createVideoStream('h265', 320);

        await expect(stream.decode([chunk(10n)])).rejects.toMatchObject({ code: 'schema' });
    });

    it('closes the decoder it opened', async () => {
        const stream = createVideoStream('h264', 320);

        await stream.decode([chunk(10n)]);
        stream.close();

        expect(closed).toBe(1);
    });
});
