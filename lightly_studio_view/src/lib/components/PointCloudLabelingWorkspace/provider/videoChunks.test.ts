import { describe, expect, it } from 'vitest';
import { chunksForTarget, isKeyframe, type VideoChunk } from './videoChunks';

/** A NAL unit with a start code, as an encoder emits it. */
function nal(headerByte: number): Uint8Array {
    return new Uint8Array([0, 0, 0, 1, headerByte, 9, 9, 9]);
}

const h264Key = nal(0x65); // type 5
const h264Delta = nal(0x41); // type 1
const h265Key = nal(16 << 1); // type 16, an IRAP picture
const h265Delta = nal(1 << 1); // type 1

describe('isKeyframe', () => {
    it('finds the picture a stream can be joined at', () => {
        expect(isKeyframe('h264', h264Key)).toBe(true);
        expect(isKeyframe('h264', h264Delta)).toBe(false);
        expect(isKeyframe('h265', h265Key)).toBe(true);
        expect(isKeyframe('hevc', h265Delta)).toBe(false);
    });

    it('treats every chunk of an independently decodable codec as an entry point', () => {
        expect(isKeyframe('vp9', h264Delta)).toBe(true);
        expect(isKeyframe('av1', new Uint8Array([1, 2, 3]))).toBe(true);
    });

    it('does not read past the end of a truncated chunk', () => {
        expect(isKeyframe('h264', new Uint8Array([0, 0, 0, 1]))).toBe(false);
        expect(isKeyframe('h264', new Uint8Array())).toBe(false);
    });
});

function chunk(logTimeNs: bigint, data: Uint8Array): VideoChunk {
    return { logTimeNs, data };
}

describe('chunksForTarget', () => {
    const stream = [
        chunk(10n, h264Key),
        chunk(20n, h264Delta),
        chunk(30n, h264Delta),
        chunk(40n, h264Key),
        chunk(50n, h264Delta)
    ];

    it('starts at the keyframe the target depends on and ends on the target', () => {
        expect(chunksForTarget(stream, 30n, 'h264').map((item) => item.logTimeNs)).toEqual([
            10n,
            20n,
            30n
        ]);
    });

    it('starts over at a later keyframe rather than replaying the whole stream', () => {
        expect(chunksForTarget(stream, 50n, 'h264').map((item) => item.logTimeNs)).toEqual([
            40n,
            50n
        ]);
    });

    it('shows the last picture before a target that falls between chunks', () => {
        expect(chunksForTarget(stream, 35n, 'h264').map((item) => item.logTimeNs)).toEqual([
            10n,
            20n,
            30n
        ]);
    });

    it('gives up on a window that opened after its keyframe', () => {
        expect(chunksForTarget(stream.slice(1, 3), 30n, 'h264')).toEqual([]);
        expect(chunksForTarget(stream, 5n, 'h264')).toEqual([]);
        expect(chunksForTarget([], 30n, 'h264')).toEqual([]);
    });
});
