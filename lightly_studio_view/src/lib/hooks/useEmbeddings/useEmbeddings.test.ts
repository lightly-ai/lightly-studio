import { QueryClient, QueryObserver } from '@tanstack/svelte-query';
import { tableFromIPC, type Table } from 'apache-arrow';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { get2dEmbeddings } from '$lib/api/lightly_studio_local/sdk.gen';
import { getEmbeddingsQueryOptions } from './useEmbeddings';

vi.mock('$lib/api/lightly_studio_local/sdk.gen', async (importOriginal) => ({
    ...(await importOriginal<object>()),
    get2dEmbeddings: vi.fn()
}));
vi.mock('apache-arrow', () => ({ tableFromIPC: vi.fn() }));

const requests = {
    count: 0,
    failuresBeforeSuccess: 0,
    isPending: false,
    resolve: () => {}
};

// Each response is a new ArrayBuffer, as for a real refetch.
const respond = async ({ signal }: { signal?: AbortSignal }) => {
    requests.count += 1;
    if (requests.failuresBeforeSuccess > 0) {
        requests.failuresBeforeSuccess -= 1;
        throw new Error('Server error');
    }
    const response = { data: new ArrayBuffer(8) };
    if (!requests.isPending) return response;
    return new Promise((resolve, reject) => {
        requests.resolve = () => resolve(response);
        signal?.addEventListener('abort', () => reject(signal.reason));
    });
};

// A table with empty columns and the given legend.
const tableWithLegend = (legend: string) =>
    ({
        schema: { metadata: new Map([['color_legend', legend]]) },
        getChild: () => ({ length: 0, toArray: () => [] })
    }) as unknown as Table;

const newQueryClient = () => new QueryClient({ defaultOptions: { queries: { retry: false } } });

const observeEmbeddings = () =>
    new QueryObserver(newQueryClient(), getEmbeddingsQueryOptions('collection-1', null));

const getComputeOptions = (
    getIsComputing: () => boolean,
    onCompute?: (compute: Promise<unknown>) => void
) => getEmbeddingsQueryOptions('collection-1', null, null, null, { getIsComputing, onCompute });

// Closes the panel while its plot request runs, reopens it, and counts the plot requests.
async function closeAndReopenPanel(getIsComputing: () => boolean): Promise<number> {
    requests.isPending = true;
    const client = newQueryClient();
    const options = getComputeOptions(getIsComputing);
    const closePanel = new QueryObserver(client, options).subscribe(() => {});
    await vi.waitFor(() => expect(requests.count).toBe(1));
    closePanel();

    const reopenedPanel = new QueryObserver(client, options);
    reopenedPanel.subscribe(() => {});
    requests.resolve();
    await vi.waitFor(() => expect(reopenedPanel.getCurrentResult().isSuccess).toBe(true));
    return requests.count;
}

describe('getEmbeddingsQueryOptions', () => {
    beforeEach(() => {
        vi.mocked(get2dEmbeddings)
            .mockReset()
            .mockImplementation(respond as never);
        vi.mocked(tableFromIPC).mockReset().mockReturnValue(tableWithLegend('{"3":"car"}'));
    });

    afterEach(() => {
        requests.count = 0;
        requests.failuresBeforeSuccess = 0;
        requests.isPending = false;
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

    it.each([
        [undefined, true],
        [true, true],
        [false, false]
    ])('passes enabled %s to the query as %s', (enabled, expected) => {
        expect(
            getEmbeddingsQueryOptions('collection-1', null, null, null, { enabled }).enabled
        ).toBe(expected);
    });

    it('does not refetch the plot on window focus', () => {
        expect(getEmbeddingsQueryOptions('collection-1', null).refetchOnWindowFocus).toBe(false);
    });

    it('joins a running compute when the panel closes and opens again', async () => {
        expect(await closeAndReopenPanel(() => true)).toBe(1);
    });

    it('aborts a saved plot download when the panel closes', async () => {
        expect(await closeAndReopenPanel(() => false)).toBe(2);
    });

    it('gives onCompute one promise for a compute that settles after the last retry', async () => {
        requests.failuresBeforeSuccess = 1;
        const onCompute = vi.fn();
        const options = getComputeOptions(() => true, onCompute);

        const plot = await new QueryClient().fetchQuery({
            queryKey: options.queryKey,
            queryFn: options.queryFn,
            retry: 1,
            retryDelay: 0
        });

        const [firstCompute, retryCompute] = onCompute.mock.calls.map(([compute]) => compute);
        expect(onCompute).toHaveBeenCalledTimes(2);
        expect(retryCompute).toBe(firstCompute);
        await expect(firstCompute).resolves.toBe(plot);
    });

    it('does not call onCompute for a saved plot download', async () => {
        const onCompute = vi.fn();
        const options = getComputeOptions(() => false, onCompute);

        await new QueryClient().fetchQuery({
            queryKey: options.queryKey,
            queryFn: options.queryFn
        });

        expect(onCompute).not.toHaveBeenCalled();
    });
});
