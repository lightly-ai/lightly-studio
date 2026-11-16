import { afterEach, describe, expect, it, vi } from 'vitest';
import * as tanstackQuery from '@tanstack/svelte-query';
import type { QueryFunctionContext } from '@tanstack/svelte-query';
import { useEmbeddings } from './useEmbeddings';

vi.mock('$lib/api/lightly_studio_local/@tanstack/svelte-query.gen', () => ({
    get2dEmbeddingsOptions: () => ({
        queryKey: ['embeddings2d'],
        queryFn: async (context: QueryFunctionContext) => {
            void context.signal;
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
    getIsComputing?: () => boolean
): EmbeddingsQueryOptions {
    const createQuerySpy = vi
        .spyOn(tanstackQuery, 'createQuery')
        .mockReturnValue({} as ReturnType<typeof tanstackQuery.createQuery>);
    useEmbeddings('collection-1', null, null, null, enabled, getIsComputing);
    const getOptions = createQuerySpy.mock.lastCall?.[0] as () => EmbeddingsQueryOptions;
    return getOptions();
}

// TanStack aborts a fetch on unmount only if the query function read the signal.
async function readsAbortSignal(options: EmbeddingsQueryOptions): Promise<boolean> {
    let isSignalRead = false;
    const context = {
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
});
