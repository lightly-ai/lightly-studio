import { afterEach, describe, expect, it, vi } from 'vitest';
import * as tanstackQuery from '@tanstack/svelte-query';
import { QueryClient, type QueryFunctionContext } from '@tanstack/svelte-query';
import { useEmbeddings } from './useEmbeddings';

const mocks = vi.hoisted(() => ({ failuresBeforeSuccess: 0 }));

vi.mock('$lib/api/lightly_studio_local/@tanstack/svelte-query.gen', () => ({
    get2dEmbeddingsOptions: () => ({
        queryKey: ['embeddings2d'],
        queryFn: async (context: QueryFunctionContext) => {
            void context.signal;
            if (mocks.failuresBeforeSuccess > 0) {
                mocks.failuresBeforeSuccess -= 1;
                throw new Error('Server error');
            }
            return new Blob();
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

// TanStack aborts a fetch on unmount only if the query function read the signal.
async function readsAbortSignal(options: EmbeddingsQueryOptions): Promise<boolean> {
    let isSignalRead = false;
    const context = {
        client: new QueryClient(),
        queryKey: ['embeddings2d'],
        meta: undefined,
        get signal() {
            isSignalRead = true;
            return new AbortController().signal;
        }
    } as unknown as QueryFunctionContext;
    await options.queryFn(context);
    return isSignalRead;
}

describe('useEmbeddings', () => {
    afterEach(() => {
        vi.restoreAllMocks();
        mocks.failuresBeforeSuccess = 0;
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

    it('keeps a running compute alive when the panel closes', async () => {
        const options = getQueryOptions(true, () => true);

        expect(await readsAbortSignal(options)).toBe(false);
    });

    it('lets a saved plot download abort when the panel closes', async () => {
        const options = getQueryOptions(true, () => false);

        expect(await readsAbortSignal(options)).toBe(true);
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
