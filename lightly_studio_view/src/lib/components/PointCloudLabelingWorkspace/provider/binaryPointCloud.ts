import { ProviderError } from './providerError';

const HEADER_BYTES = 24;
const MAGIC = 'LSPC';
const VERSION = 1;

export interface BinaryPointCloud {
    positions: Float32Array;
    timestampNs: string;
    sourcePointCount: number;
    frameId: string;
}

/** Decode the backend's LSPC/1 payload into buffers ready for Three.js. */
export function decodeBinaryPointCloud(payload: ArrayBuffer): BinaryPointCloud {
    if (payload.byteLength < HEADER_BYTES) {
        throw new ProviderError('corrupt', 'The binary point-cloud payload is truncated.');
    }
    const bytes = new Uint8Array(payload, 0, 4);
    if (new TextDecoder().decode(bytes) !== MAGIC) {
        throw new ProviderError('corrupt', 'The binary point-cloud payload has an invalid header.');
    }
    const view = new DataView(payload);
    if (view.getUint8(4) !== VERSION) {
        throw new ProviderError('source', 'The binary point-cloud version is not supported.');
    }
    const pointCount = view.getUint32(8, true);
    const sourcePointCount = view.getUint32(12, true);
    const expectedBytes = HEADER_BYTES + pointCount * 3 * Float32Array.BYTES_PER_ELEMENT;
    if (expectedBytes !== payload.byteLength) {
        throw new ProviderError('corrupt', 'The binary point-cloud payload has an invalid size.');
    }
    return {
        positions: new Float32Array(payload, HEADER_BYTES, pointCount * 3),
        timestampNs: view.getBigUint64(16, true).toString(),
        sourcePointCount,
        frameId: ''
    };
}
