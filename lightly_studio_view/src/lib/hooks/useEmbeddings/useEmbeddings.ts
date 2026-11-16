import { get2dEmbeddingsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { GetEmbeddings2dRequest } from '$lib/api/lightly_studio_local/types.gen';

import { createQuery } from '@tanstack/svelte-query';

type EmbeddingsColorBy = GetEmbeddings2dRequest['color_by'];
type EmbeddingsAxes = GetEmbeddings2dRequest['axes'];

export function useEmbeddings(
    collectionId: string,
    filters: GetEmbeddings2dRequest['filters'] | null,
    colorBy: EmbeddingsColorBy = null,
    axes: EmbeddingsAxes = null,
    enabled = true,
    getIsComputing: () => boolean = () => false
) {
    return createQuery(() => {
        const options = get2dEmbeddingsOptions({
            path: { collection_id: collectionId },
            body: { filters: filters ?? {}, color_by: colorBy, axes }
        });
        const fetchPlot = options.queryFn;
        // The server keeps computing after an abort, and a second request conflicts with it.
        // TanStack aborts on unmount only if the signal is read, so a compute is not given it:
        // the fetch outlives a closed panel and a reopened panel joins it.
        const queryFn: typeof fetchPlot =
            typeof fetchPlot === 'function'
                ? (context) => {
                      if (!getIsComputing()) return fetchPlot(context);
                      const { client, queryKey, meta } = context;
                      const signal = new AbortController().signal;
                      return fetchPlot({ client, queryKey, meta, signal });
                  }
                : fetchPlot;
        return {
            ...options,
            queryFn,
            enabled,
            // The status query refetches on focus and decides whether a compute may start.
            refetchOnWindowFocus: false
        };
    });
}
