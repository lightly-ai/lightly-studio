/** Encoding of a tick payload, as sent by the tick data endpoint. */
export const TickPayloadKind = {
    POINT_CLOUD: 0,
    CAMERA_JPEG: 1
} as const;

/** One channel's payload of a tick data response. */
interface TickPayload {
    /** MCAP channel the payload was read from. */
    channelId: number;
    /** Encoding of `bytes`, one of `TickPayloadKind`. */
    kind: number;
    /** Log time of the message, in nanoseconds (string to preserve precision). */
    logTimeNs: string;
    /** The encoded payload: an Arrow IPC stream or a JPEG. */
    bytes: ArrayBuffer;
}

// channel_id u32, kind u8, log_time_ns u64, length u64, little-endian and unpadded.
const HEADER_BYTES = 21;

/** Splits a tick data response body into its payloads. */
export function decodeTickPayloads(buffer: ArrayBuffer): TickPayload[] {
    const view = new DataView(buffer);
    const payloads: TickPayload[] = [];
    let offset = 0;
    while (offset < buffer.byteLength) {
        if (offset + HEADER_BYTES > buffer.byteLength) {
            throw new Error('Tick data body is truncated.');
        }
        const channelId = view.getUint32(offset, true);
        const kind = view.getUint8(offset + 4);
        const logTimeNs = view.getBigUint64(offset + 5, true).toString();
        const length = Number(view.getBigUint64(offset + 13, true));
        offset += HEADER_BYTES;
        if (offset + length > buffer.byteLength) {
            throw new Error('Tick data body is truncated.');
        }
        payloads.push({ channelId, kind, logTimeNs, bytes: buffer.slice(offset, offset + length) });
        offset += length;
    }
    return payloads;
}
