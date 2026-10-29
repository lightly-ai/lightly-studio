import { tableFromIPC, type Vector } from 'apache-arrow';
import { writable, type Writable } from 'svelte/store';

const dataColumns = ['x', 'y', 'fulfils_filter', 'color_categories', 'sample_id'];
type TableColumn = (typeof dataColumns)[number];

// Reads a list<uint8> column row by row into a plain number[][], where each row holds all
// the categories a sample belongs to, in priority order.
const readListColumn = (column: Vector): number[][] => {
    const rows: number[][] = [];
    for (let row = 0; row < column.length; row++) {
        rows.push(Array.from<number>(column.get(row) ?? []));
    }
    return rows;
};

export type ArrowData = Record<TableColumn, unknown>;

/** Gradient of a numeric color-by field: its value range and the position of each category. */
export interface ColorGradient {
    min: number;
    max: number;
    positions: Map<number, number>;
}

type UseArrowDataReturn = {
    data: Writable<ArrowData>;
    colorLegend: Writable<Map<number, string>>;
    colorGradient: Writable<ColorGradient | null>;
    error: Writable<string | undefined>;
};

type ArrowMetadata = Map<string, string | Uint8Array> | undefined;

const readMetadataText = (metadata: ArrowMetadata, key: string): string | null => {
    const raw = metadata?.get(key);
    if (!raw) {
        return null;
    }
    return raw instanceof Uint8Array ? new TextDecoder().decode(raw) : raw;
};

const parseColorGradient = (metadata: ArrowMetadata): ColorGradient | null => {
    const gradientText = readMetadataText(metadata, 'color_gradient');
    if (!gradientText) {
        return null;
    }
    try {
        const parsed = JSON.parse(gradientText) as {
            min: number;
            max: number;
            positions: Record<string, number>;
        };
        return {
            min: parsed.min,
            max: parsed.max,
            positions: new Map(
                Object.entries(parsed.positions).map(([key, value]) => [Number(key), value])
            )
        };
    } catch (error) {
        console.warn('Invalid color_gradient metadata in Arrow data.', error);
        return null;
    }
};

const parseColorLegend = (metadata: ArrowMetadata) => {
    const legendText = readMetadataText(metadata, 'color_legend');
    if (!legendText) {
        return new Map<number, string>();
    }

    let parsedLegend: Record<string, string> = {};
    try {
        parsedLegend = JSON.parse(legendText) as Record<string, string>;
    } catch (error) {
        console.warn('Invalid color_legend metadata in Arrow data.', error);
    }

    return new Map(
        Object.entries(parsedLegend).map(([key, value]) => [Number(key), value] as const)
    );
};

/**
 * Parses Apache Arrow IPC format blob data into reactive Svelte stores.
 * Extracts x/y coordinates, filter status, and sample IDs from the Arrow table
 * and validates that all required columns are present.
 *
 * @param blobData - Binary blob containing Arrow IPC formatted embeddings data
 * @returns Object containing reactive stores for the parsed data and any error messages
 */
export function useArrowData({ blobData }: { blobData: Blob }): UseArrowDataReturn {
    const error = writable<string | undefined>();

    const data = writable<ArrowData>();
    const colorLegend = writable<Map<number, string>>(new Map());
    const colorGradient = writable<ColorGradient | null>(null);

    const readData = async () => {
        try {
            const buf = await (blobData as Blob).arrayBuffer();
            const table = await tableFromIPC(new Uint8Array(buf));
            if (!table) {
                error.set('Failed to read Arrow table from embeddings data.');
                return;
            }
            const columnData = new Map<TableColumn, unknown>();
            for (const col of dataColumns) {
                const child = table.getChild(col);
                if (!child) {
                    error.set(`Missing required column "${col}" in Arrow data.`);
                    return;
                }
                columnData.set(
                    col,
                    col === 'color_categories' ? readListColumn(child) : child.toArray()
                );
            }
            data.set(Object.fromEntries(columnData) as Record<TableColumn, unknown>);
            colorLegend.set(parseColorLegend(table.schema?.metadata));
            colorGradient.set(parseColorGradient(table.schema?.metadata));
        } catch (e) {
            error.set(`Error reading Arrow data: ${String(e)}`);
        }
    };

    readData();
    return { data, colorLegend, colorGradient, error };
}
