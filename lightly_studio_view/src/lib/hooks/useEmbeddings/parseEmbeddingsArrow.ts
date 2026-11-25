import { tableFromIPC, type Vector } from 'apache-arrow';

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

export interface EmbeddingsArrow {
    columns: ArrowData;
    legend: Map<number, string>;
}

const parseColorLegend = (metadata: Map<string, string | Uint8Array> | undefined) => {
    const rawLegend = metadata?.get('color_legend');
    if (!rawLegend) {
        return new Map<number, string>();
    }

    const legendText =
        rawLegend instanceof Uint8Array ? new TextDecoder().decode(rawLegend) : rawLegend;

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
 * Parses the Arrow IPC response of the embeddings endpoint into plot columns and a legend.
 * Extracts x/y coordinates, filter status, and sample IDs from the Arrow table
 * and validates that all required columns are present.
 */
export function parseEmbeddingsArrow(buffer: ArrayBuffer): EmbeddingsArrow {
    const table = tableFromIPC(new Uint8Array(buffer));
    const columnData = new Map<TableColumn, unknown>();
    for (const col of dataColumns) {
        const child = table.getChild(col);
        if (!child) {
            throw new Error(`Missing required column "${col}" in Arrow data.`);
        }
        columnData.set(col, col === 'color_categories' ? readListColumn(child) : child.toArray());
    }
    return {
        columns: Object.fromEntries(columnData) as ArrowData,
        legend: parseColorLegend(table.schema?.metadata)
    };
}
