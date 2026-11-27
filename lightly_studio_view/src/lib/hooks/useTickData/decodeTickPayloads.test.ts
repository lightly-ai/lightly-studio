import { describe, expect, it } from 'vitest';
import { decodeTickPayloads, TickPayloadKind } from './decodeTickPayloads';

interface Item {
    channelId: number;
    kind: number;
    logTimeNs: bigint;
    bytes: number[];
}

function encode(items: Item[]): ArrayBuffer {
    const size = items.reduce((total, item) => total + 21 + item.bytes.length, 0);
    const buffer = new ArrayBuffer(size);
    const view = new DataView(buffer);
    let offset = 0;
    for (const { channelId, kind, logTimeNs, bytes } of items) {
        view.setUint32(offset, channelId, true);
        view.setUint8(offset + 4, kind);
        view.setBigUint64(offset + 5, logTimeNs, true);
        view.setBigUint64(offset + 13, BigInt(bytes.length), true);
        new Uint8Array(buffer, offset + 21, bytes.length).set(bytes);
        offset += 21 + bytes.length;
    }
    return buffer;
}

describe('decodeTickPayloads', () => {
    it('returns no payload for an empty body', () => {
        expect(decodeTickPayloads(new ArrayBuffer(0))).toEqual([]);
    });

    it('splits the payloads and keeps 64-bit log times exact', () => {
        // 2^53 + 1 cannot be represented exactly as a JavaScript number.
        const payloads = decodeTickPayloads(
            encode([
                {
                    channelId: 7,
                    kind: TickPayloadKind.POINT_CLOUD,
                    logTimeNs: 9_007_199_254_740_993n,
                    bytes: [1, 2]
                },
                {
                    channelId: 3,
                    kind: TickPayloadKind.CAMERA_JPEG,
                    logTimeNs: 9_007_199_254_740_994n,
                    bytes: [3]
                }
            ])
        );

        expect(
            payloads.map(({ channelId, kind, logTimeNs }) => ({ channelId, kind, logTimeNs }))
        ).toEqual([
            { channelId: 7, kind: TickPayloadKind.POINT_CLOUD, logTimeNs: '9007199254740993' },
            { channelId: 3, kind: TickPayloadKind.CAMERA_JPEG, logTimeNs: '9007199254740994' }
        ]);
        expect(new Uint8Array(payloads[0].bytes)).toEqual(new Uint8Array([1, 2]));
        expect(new Uint8Array(payloads[1].bytes)).toEqual(new Uint8Array([3]));
    });

    it('throws for a truncated body', () => {
        const buffer = encode([
            { channelId: 1, kind: TickPayloadKind.CAMERA_JPEG, logTimeNs: 1n, bytes: [1, 2, 3] }
        ]);

        expect(() => decodeTickPayloads(buffer.slice(0, buffer.byteLength - 1))).toThrow(
            'Tick data body is truncated.'
        );
    });
});
