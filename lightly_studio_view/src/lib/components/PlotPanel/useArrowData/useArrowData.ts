import { tableFromIPC } from 'apache-arrow';
import { writable, type Writable } from 'svelte/store';

const dataColumns = ['x', 'y', 'fulfils_filter', 'sample_id'] as const;
type TableColumn = (typeof dataColumns)[number];

export type ArrowData = Record<TableColumn, unknown>;

type UseArrowDataReturn = {
    data: Writable<ArrowData>;
    error: Writable<string | undefined>;
};

/**
 * Hook to read Arrow data from a Blob.
 *
 * @param dataBlob
 * @returns
 */
export function useArrowData({ blobData }: { blobData: Blob }): UseArrowDataReturn {
    const error = writable<string | undefined>();

    const data = writable<ArrowData>();

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
        } catch (e) {
            error.set(`Error reading Arrow data: ${String(e)}`);
        }
    };

    readData();
    return { data, error };
}
