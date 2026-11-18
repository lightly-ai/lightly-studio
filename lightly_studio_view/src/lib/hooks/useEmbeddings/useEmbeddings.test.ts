import { afterEach, describe, expect, it, vi } from 'vitest';
import * as tanstackQuery from '@tanstack/svelte-query';
import { QueryClient, QueryObserver, type QueryFunctionContext } from '@tanstack/svelte-query';
import { useEmbeddings } from './useEmbeddings';

const mocks = vi.hoisted(() => ({
    failuresBeforeSuccess: 0,
    requestCount: 0,
    isPending: false,
    resolveRequest: () => {}
}));

vi.mock('$lib/api/lightly_studio_local/@tanstack/svelte-query.gen', () => ({
    get2dEmbeddingsOptions: () => ({
        queryKey: ['embeddings2d'],
        queryFn: async ({ signal }: QueryFunctionContext) => {
            mocks.requestCount += 1;
            if (mocks.failuresBeforeSuccess > 0) {
                mocks.failuresBeforeSuccess -= 1;
                throw new Error('Server error');
            }
            if (!mocks.isPending) return new Blob();
            return new Promise<Blob>((resolve, reject) => {
                mocks.resolveRequest = () => resolve(new Blob());
                signal.addEventListener('abort', () => reject(signal.reason));
            });
        }
    })
}));

interface EmbeddingsQueryOptions {
    enabled?: boolean;
    refetchOnWindowFocus?: boolean;
    queryFn: (context: QueryFunctionContext) => Promise<Blob>;
}

function getQueryOptions(
    enabled?: boolean,
    getIsComputing?: () => boolean,
    onCompute?: (compute: Promise<unknown>) => void
): EmbeddingsQueryOptions {
    const createQuerySpy = vi
        .spyOn(tanstackQuery, 'createQuery')
        .mockReturnValue({} as ReturnType<typeof tanstackQuery.createQuery>);
    useEmbeddings('collection-1', null, null, null, { enabled, getIsComputing, onCompute });
    const getOptions = createQuerySpy.mock.lastCall?.[0] as () => EmbeddingsQueryOptions;
    return getOptions();
}

// Closes the panel while its plot request runs, reopens it, and counts the plot requests.
async function closeAndReopenPanel(getIsComputing: () => boolean): Promise<number> {
    mocks.isPending = true;
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const options = { ...getQueryOptions(true, getIsComputing), queryKey: ['embeddings2d'] };
    const closePanel = new QueryObserver(client, options).subscribe(() => {});
    await vi.waitFor(() => expect(mocks.requestCount).toBe(1));
    closePanel();

    const reopenedPanel = new QueryObserver(client, options);
    reopenedPanel.subscribe(() => {});
    mocks.resolveRequest();
    await vi.waitFor(() => expect(reopenedPanel.getCurrentResult().isSuccess).toBe(true));
    return mocks.requestCount;
}

describe('useEmbeddings', () => {
    afterEach(() => {
        vi.restoreAllMocks();
        mocks.failuresBeforeSuccess = 0;
        mocks.requestCount = 0;
        mocks.isPending = false;
    });

    it.each([
        [undefined, true],
        [true, true],
        [false, false]
    ])('passes enabled %s to the query as %s', (enabled, expected) => {
        expect(getQueryOptions(enabled).enabled).toBe(expected);
    });

    it('does not refetch the plot on window focus', () => {
        expect(getQueryOptions().refetchOnWindowFocus).toBe(false);
    });

    it('joins a running compute when the panel closes and opens again', async () => {
        expect(await closeAndReopenPanel(() => true)).toBe(1);
    });

    it('aborts a saved plot download when the panel closes', async () => {
        expect(await closeAndReopenPanel(() => false)).toBe(2);
    });

    it('gives onCompute one promise for a compute that settles after the last retry', async () => {
        mocks.failuresBeforeSuccess = 1;
        const onCompute = vi.fn();
        const options = getQueryOptions(true, () => true, onCompute);

        const plot = await new QueryClient().fetchQuery({
            queryKey: ['embeddings2d'],
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
        const options = getQueryOptions(true, () => false, onCompute);

        await new QueryClient().fetchQuery({
            queryKey: ['embeddings2d'],
            queryFn: options.queryFn
        });

        expect(onCompute).not.toHaveBeenCalled();
    });
});
