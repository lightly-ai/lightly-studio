import { QueryClient, QueryObserver } from '@tanstack/svelte-query';
import { tableFromIPC, type Table } from 'apache-arrow';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { get2dEmbeddings } from '$lib/api/lightly_studio_local/sdk.gen';
import { shouldRetryQuery } from '$lib/api/shouldRetryQuery';
import type { GetEmbeddings2dRequest } from '$lib/api/lightly_studio_local/types.gen';
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
    resolve: () => {},
    reject: () => {}
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
        requests.reject = () => reject(new Error('Server error'));
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
// Retries as the app does, without the delay.
const newRetryingQueryClient = () =>
    new QueryClient({ defaultOptions: { queries: { retry: shouldRetryQuery, retryDelay: 0 } } });

const observeEmbeddings = () =>
    new QueryObserver(newQueryClient(), getEmbeddingsQueryOptions('collection-1', null));

const TAG_FILTER: GetEmbeddings2dRequest['filters'] = {
    filter_type: 'image',
    sample_filter: { tag_ids: ['tag-a'] }
};

const getComputeOptions = (
    getIsComputing: () => boolean,
    onCompute?: (compute: Promise<unknown>) => void,
    filters: GetEmbeddings2dRequest['filters'] | null = null
) => getEmbeddingsQueryOptions('collection-1', filters, null, null, { getIsComputing, onCompute });

// Starts a compute, then a compute request with a filter while the first one runs.
async function requestFilteredPlotDuringCompute() {
    requests.isPending = true;
    const client = newQueryClient();
    new QueryObserver(
        client,
        getComputeOptions(() => true)
    ).subscribe(() => {});
    await vi.waitFor(() => expect(requests.count).toBe(1));
    const filteredPanel = new QueryObserver(
        client,
        getComputeOptions(() => true, undefined, TAG_FILTER)
    );
    filteredPanel.subscribe(() => {});
    await new Promise((resolve) => setTimeout(resolve));
    const requestsWhileComputing = requests.count;
    requests.isPending = false;
    return { filteredPanel, requestsWhileComputing };
}

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

    it('does not refetch the plot on window focus', () => {
        expect(getEmbeddingsQueryOptions('collection-1', null).refetchOnWindowFocus).toBe(false);
    });

    it('joins a running compute when the panel closes and opens again', async () => {
        expect(await closeAndReopenPanel(() => true)).toBe(1);
    });

    it('aborts a saved plot download when the panel closes', async () => {
        expect(await closeAndReopenPanel(() => false)).toBe(2);
    });

    it('joins a running compute when the plot is refreshed', async () => {
        let isComputing = false;
        const onCompute = vi.fn();
        const client = newQueryClient();
        const panel = new QueryObserver(
            client,
            getComputeOptions(() => isComputing, onCompute)
        );
        panel.subscribe(() => {});
        await vi.waitFor(() => expect(panel.getCurrentResult().isSuccess).toBe(true));

        isComputing = true;
        requests.isPending = true;
        void panel.refetch();
        await vi.waitFor(() => expect(requests.count).toBe(2));
        void client.invalidateQueries();
        requests.resolve();
        await vi.waitFor(() => expect(panel.getCurrentResult().isFetching).toBe(false));

        expect(requests.count).toBe(2);
        expect(onCompute).toHaveBeenCalledOnce();
        await expect(onCompute.mock.calls[0][0]).resolves.toBeInstanceOf(ArrayBuffer);
    });

    it('waits for a running compute before a compute request with another filter', async () => {
        const { filteredPanel, requestsWhileComputing } = await requestFilteredPlotDuringCompute();
        requests.resolve();
        await vi.waitFor(() => expect(filteredPanel.getCurrentResult().isSuccess).toBe(true));

        expect(requestsWhileComputing).toBe(1);
        expect(requests.count).toBe(2);
    });

    it('fails a waiting compute request without a request when the running compute fails', async () => {
        const { filteredPanel } = await requestFilteredPlotDuringCompute();
        requests.reject();
        await vi.waitFor(() => expect(filteredPanel.getCurrentResult().isError).toBe(true));

        expect(requests.count).toBe(1);
    });

    it('does not retry a failed compute', async () => {
        requests.failuresBeforeSuccess = 1;
        const onCompute = vi.fn();
        const options = getComputeOptions(() => true, onCompute);

        const result = await new QueryObserver(newRetryingQueryClient(), options).refetch();

        expect(result.isError).toBe(true);
        expect(requests.count).toBe(1);
        await expect(onCompute.mock.calls[0][0]).rejects.toThrow('Server error');
    });

    it('retries a failed saved plot download', async () => {
        requests.failuresBeforeSuccess = 1;
        const options = getComputeOptions(() => false);

        const result = await new QueryObserver(newRetryingQueryClient(), options).refetch();

        expect(result.isSuccess).toBe(true);
        expect(requests.count).toBe(2);
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
