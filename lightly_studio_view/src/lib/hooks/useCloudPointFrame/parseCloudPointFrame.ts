import { tableFromIPC, type Table } from 'apache-arrow';
import type { PointBatch } from '$lib/components/PointCloudViewer';
import type { CloudPointFrame } from './types';

/** Identifies the channel and fallback timestamp a raw frame buffer came from. */
interface CloudPointFrameSource {
    channelId: number;
    timestampNs: string;
}

/**
 * Parses an Arrow IPC point-cloud buffer into a renderable {@link CloudPointFrame}.
 *
 * @param buffer - The Arrow IPC bytes for a single frame.
 * @param source - The channel and fallback timestamp the buffer came from.
 * @returns The packed point batch together with the frame's metadata.
 */
export async function parseCloudPointFrame(
    buffer: ArrayBuffer,
    source: CloudPointFrameSource
): Promise<CloudPointFrame> {
    const table = await tableFromIPC(new Uint8Array(buffer));
    const batch = packBatch(table);
    return buildFrame(table, batch, source);
}

/**
 * Extracts and packs the x/y/z, intensity, and optional r/g/b columns into
 * flat typed arrays.
 *
 * @param table - The parsed Arrow table.
 * @returns The packed positions, intensities, optional colors, and point count.
 * @throws If x/y/z are missing or mismatched, or if r/g/b are partially present.
 */
function packBatch(table: Table): PointBatch {
    const xColumn = table.getChild('x');
    const yColumn = table.getChild('y');
    const zColumn = table.getChild('z');
    const x = xColumn?.toArray();
    const y = yColumn?.toArray();
    const z = zColumn?.toArray();
    if (!x || !y || !z || x.length !== y.length || x.length !== z.length) {
        throw new Error('Point-cloud Arrow data must contain matching x, y, and z columns.');
    }
    if (xColumn?.nullCount || yColumn?.nullCount || zColumn?.nullCount) {
        throw new Error('Point-cloud Arrow data must not contain null x, y, or z values.');
    }
    const intensity = table.getChild('intensity')?.toArray();
    const red = table.getChild('r')?.toArray();
    const green = table.getChild('g')?.toArray();
    const blue = table.getChild('b')?.toArray();
    if (Boolean(red) !== Boolean(green) || Boolean(red) !== Boolean(blue)) {
        throw new Error('Point-cloud Arrow data must contain all or none of r, g, and b columns.');
    }
    const positions = new Float32Array(x.length * 3);
    const intensities = new Float32Array(x.length);
    const colors = red && green && blue ? new Float32Array(x.length * 3) : undefined;
    for (let index = 0; index < x.length; index++) {
        positions[index * 3] = Number(x[index]);
        positions[index * 3 + 1] = Number(y[index]);
        positions[index * 3 + 2] = Number(z[index]);
        intensities[index] = intensity ? Number(intensity[index]) : 0;
        if (colors && red && green && blue) {
            colors[index * 3] = Number(red[index]);
            colors[index * 3 + 1] = Number(green[index]);
            colors[index * 3 + 2] = Number(blue[index]);
        }
    }
    return { positions, intensities, ...(colors ? { colors } : {}), count: x.length };
}

/**
 * Assembles a {@link CloudPointFrame} from a packed batch and the table's
 * schema metadata, falling back to {@link CloudPointFrameSource} values when a
 * metadata key is absent.
 *
 * @param table - The parsed Arrow table carrying the frame metadata.
 * @param batch - The packed point batch from {@link packBatch}.
 * @param source - The channel and fallback timestamp the frame came from.
 * @returns The fully assembled frame.
 */
function buildFrame(
    table: Table,
    batch: PointBatch,
    source: CloudPointFrameSource
): CloudPointFrame {
    const metadata = table.schema.metadata;
    const boundsText = readMetadata(metadata, 'bounds');
    const timestampNs = readMetadata(metadata, 'log_time_ns') ?? source.timestampNs;
    const frameId = readMetadata(metadata, 'frame_id') ?? '';
    return {
        batch,
        channelId: source.channelId,
        timestampNs,
        frameId,
        sourcePointCount: readSourcePointCount(metadata, batch.count),
        bounds: boundsText ? JSON.parse(boundsText) : null,
        channels: [{ channelId: source.channelId, timestampNs, frameId }]
    };
}

/**
 * Reads the `source_point_count` metadata as a non-negative integer, falling
 * back to the packed count when the key is absent or malformed.
 *
 * @param metadata - The Arrow schema metadata map, if any.
 * @param fallback - The count to use when the metadata is missing or invalid.
 * @returns The validated source point count.
 */
function readSourcePointCount(
    metadata: Map<string, string | Uint8Array> | undefined,
    fallback: number
): number {
    const text = readMetadata(metadata, 'source_point_count');
    if (text === undefined) return fallback;
    const value = Number(text);
    return Number.isInteger(value) && value >= 0 ? value : fallback;
}

/**
 * Reads a metadata value by key, decoding it to text when stored as bytes.
 *
 * @param metadata - The Arrow schema metadata map, if any.
 * @param key - The metadata key to look up.
 * @returns The decoded string, or `undefined` when the key is absent.
 */
function readMetadata(
    metadata: Map<string, string | Uint8Array> | undefined,
    key: string
): string | undefined {
    const value = metadata?.get(key);
    return value instanceof Uint8Array ? new TextDecoder().decode(value) : value;
}
