import { tableFromIPC, type Table } from 'apache-arrow';
import type { PointBatch } from '$lib/components/PointCloudViewer';
import type { CloudPointFrame, Vec3 } from './types';

/** Identifies the channel and fallback timestamp a raw frame buffer came from. */
interface CloudPointFrameSource {
    channelId: number;
    timestampNs: string;
}

type ColumnValues = ReturnType<NonNullable<ReturnType<Table['getChild']>>['toArray']>;

interface CoordinateColumns {
    x: ColumnValues;
    y: ColumnValues;
    z: ColumnValues;
}

interface ColorColumns {
    red: ColumnValues;
    green: ColumnValues;
    blue: ColumnValues;
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
    const coordinates = readCoordinates(table);
    const intensity = table.getChild('intensity')?.toArray();
    const colors = readColors(table);
    return {
        positions: packCoordinates(coordinates),
        intensities: packIntensity(coordinates.x.length, intensity),
        ...(colors ? { colors: packColors(colors, coordinates.x.length) } : {}),
        count: coordinates.x.length
    };
}

function readCoordinates(table: Table): CoordinateColumns {
    const x = readCoordinate(table, 'x');
    const y = readCoordinate(table, 'y');
    const z = readCoordinate(table, 'z');
    if (x.length !== y.length || x.length !== z.length) {
        throw new Error('Point-cloud Arrow data must contain matching x, y, and z columns.');
    }
    return { x, y, z };
}

function readCoordinate(table: Table, name: 'x' | 'y' | 'z'): ColumnValues {
    const column = table.getChild(name);
    if (!column) {
        throw new Error('Point-cloud Arrow data must contain matching x, y, and z columns.');
    }
    if (column.nullCount) {
        throw new Error('Point-cloud Arrow data must not contain null x, y, or z values.');
    }
    return column.toArray();
}

function readColors(table: Table): ColorColumns | undefined {
    const red = table.getChild('r')?.toArray();
    const green = table.getChild('g')?.toArray();
    const blue = table.getChild('b')?.toArray();
    if (!red && !green && !blue) return undefined;
    if (!red || !green || !blue) {
        throw new Error('Point-cloud Arrow data must contain all or none of r, g, and b columns.');
    }
    return { red, green, blue };
}

function packCoordinates({ x, y, z }: CoordinateColumns): Float32Array {
    const positions = new Float32Array(x.length * 3);
    for (let index = 0; index < x.length; index++) {
        positions[index * 3] = Number(x[index]);
        positions[index * 3 + 1] = Number(y[index]);
        positions[index * 3 + 2] = Number(z[index]);
    }
    return positions;
}

function packIntensity(count: number, intensity?: ColumnValues): Float32Array {
    const intensities = new Float32Array(count);
    if (!intensity) return intensities;
    for (let index = 0; index < count; index++) intensities[index] = Number(intensity[index]);
    return intensities;
}

function packColors({ red, green, blue }: ColorColumns, count: number): Float32Array {
    const colors = new Float32Array(count * 3);
    for (let index = 0; index < count; index++) {
        colors[index * 3] = Number(red[index]);
        colors[index * 3 + 1] = Number(green[index]);
        colors[index * 3 + 2] = Number(blue[index]);
    }
    return colors;
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
    const timestampNs = readMetadata(metadata, 'log_time_ns') ?? source.timestampNs;
    const frameId = readMetadata(metadata, 'frame_id') ?? '';
    return {
        batch,
        channelId: source.channelId,
        timestampNs,
        frameId,
        sourcePointCount: readSourcePointCount(metadata, batch.count),
        bounds: readBounds(metadata),
        channels: [{ channelId: source.channelId, timestampNs, frameId }]
    };
}

/** Reads and validates point-cloud bounds metadata. */
function readBounds(
    metadata: Map<string, string | Uint8Array> | undefined
): CloudPointFrame['bounds'] {
    const text = readMetadata(metadata, 'bounds');
    if (text === undefined) return null;
    const value: unknown = JSON.parse(text);
    if (value === null) return null;
    if (!isBounds(value)) throw new Error('Point-cloud bounds metadata is invalid.');
    return value;
}

function isBounds(value: unknown): value is NonNullable<CloudPointFrame['bounds']> {
    if (typeof value !== 'object' || value === null) return false;
    const bounds = value as Record<string, unknown>;
    return isVec3(bounds.min) && isVec3(bounds.max);
}

function isVec3(value: unknown): value is Vec3 {
    return Array.isArray(value) && value.length === 3 && value.every(Number.isFinite);
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
