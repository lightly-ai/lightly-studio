import { QueryClient, QueryObserver } from '@tanstack/svelte-query';
import { tableFromIPC, type Table } from 'apache-arrow';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { get2dEmbeddings } from '$lib/api/lightly_studio_local/sdk.gen';
import { getEmbeddingsQueryOptions } from './useEmbeddings';

vi.mock('$lib/api/lightly_studio_local/sdk.gen', async (importOriginal) => ({
    ...(await importOriginal<object>()),
    get2dEmbeddings: vi.fn()
}));
vi.mock('apache-arrow', () => ({ tableFromIPC: vi.fn() }));

// A table with empty columns and the given legend.
const tableWithLegend = (legend: string) =>
    ({
        schema: { metadata: new Map([['color_legend', legend]]) },
        getChild: () => ({ length: 0, toArray: () => [] })
    }) as unknown as Table;

const observeEmbeddings = () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return new QueryObserver(queryClient, getEmbeddingsQueryOptions('collection-1', null));
};

describe('getEmbeddingsQueryOptions', () => {
    beforeEach(() => {
        // Each response is a new ArrayBuffer, as for a real refetch.
        vi.mocked(get2dEmbeddings)
            .mockReset()
            .mockImplementation(async () => ({ data: new ArrayBuffer(8) }) as never);
        vi.mocked(tableFromIPC).mockReset().mockReturnValue(tableWithLegend('{"3":"car"}'));
    });

    it('fetches an ArrayBuffer and keeps the legend object while the legend is equal', async () => {
        const observer = observeEmbeddings();

        const first = await observer.refetch();
        const equalLegend = await observer.refetch();
        vi.mocked(tableFromIPC).mockReturnValue(tableWithLegend('{"3":"bus"}'));
        const newLegend = await observer.refetch();

        expect(get2dEmbeddings).toHaveBeenCalledWith(
            expect.objectContaining({ parseAs: 'arrayBuffer' })
        );
        expect(equalLegend.data).not.toBe(first.data);
        expect(equalLegend.data?.legend).toBe(first.data?.legend);
        expect(newLegend.data?.legend).toEqual(new Map([[3, 'bus']]));

        // New options keep the module-level select, so the data is not parsed again.
        observer.setOptions(getEmbeddingsQueryOptions('collection-1', null));
        expect(tableFromIPC).toHaveBeenCalledTimes(3);
    });

    it('reports a parse error as the query error', async () => {
        vi.mocked(tableFromIPC).mockImplementation(() => {
            throw new Error('bad table');
        });

        const result = await observeEmbeddings().refetch();

        expect(result.isError).toBe(true);
        expect(result.error?.message).toBe('bad table');
    });
});
