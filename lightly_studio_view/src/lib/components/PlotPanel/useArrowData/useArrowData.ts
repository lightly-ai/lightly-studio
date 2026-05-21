import { tableFromIPC } from 'apache-arrow';
import { writable, type Writable } from 'svelte/store';

const dataColumns = ['x', 'y', 'fulfils_filter', 'color_category', 'sample_id'] as const;
type TableColumn = (typeof dataColumns)[number];

export type ArrowData = Record<TableColumn, unknown>;

export type ReferencePoint = {
    x: number;
    y: number;
    label: string;
    kind: 'axis' | 'label';
};

type UseArrowDataReturn = {
    data: Writable<ArrowData>;
    colorLegend: Writable<Map<number, string>>;
    referencePoints: Writable<ReferencePoint[]>;
    error: Writable<string | undefined>;
};

const decodeMetadata = (
    metadata: Map<string, string | Uint8Array> | undefined,
    key: string
): string | undefined => {
    const raw = metadata?.get(key);
    if (!raw) return undefined;
    return raw instanceof Uint8Array ? new TextDecoder().decode(raw) : raw;
};

const parseColorLegend = (metadata: Map<string, string | Uint8Array> | undefined) => {
    const legendText = decodeMetadata(metadata, 'color_legend');
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

const parseReferencePoints = (
    metadata: Map<string, string | Uint8Array> | undefined
): ReferencePoint[] => {
    const text = decodeMetadata(metadata, 'reference_points');
    if (!text) return [];
    try {
        const parsed = JSON.parse(text) as Array<Partial<ReferencePoint>>;
        if (!Array.isArray(parsed)) return [];
        return parsed.map(
            (p): ReferencePoint => ({
                x: typeof p.x === 'number' ? p.x : 0,
                y: typeof p.y === 'number' ? p.y : 0,
                label: typeof p.label === 'string' ? p.label : '',
                kind: p.kind === 'axis' ? 'axis' : 'label'
            })
        );
    } catch (error) {
        console.warn('Invalid reference_points metadata in Arrow data.', error);
        return [];
    }
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
    const referencePoints = writable<ReferencePoint[]>([]);

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
                if (!table.getChild(col)) {
                    error.set(`Missing required column "${col}" in Arrow data.`);
                    return;
                }
                columnData.set(col, table.getChild(col)?.toArray());
            }
            data.set(Object.fromEntries(columnData) as Record<TableColumn, unknown>);
            colorLegend.set(parseColorLegend(table.schema?.metadata));
            referencePoints.set(parseReferencePoints(table.schema?.metadata));
        } catch (e) {
            error.set(`Error reading Arrow data: ${String(e)}`);
        }
    };

    readData();
    return { data, colorLegend, referencePoints, error };
}
