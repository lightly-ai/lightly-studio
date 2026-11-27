import { useQueryClient } from '@tanstack/svelte-query';
import { createMcapTickPrefetchExecutor } from './createMcapTickPrefetchExecutor';
import { getBufferedTickRanges } from './getBufferedTickRanges';
import type { McapTickDetailsPrefetchParams, TickRange } from './types';

/** Executes requested tick ranges with bounded concurrency and exposes prefetch state. */
export const useMcapTickDetailsPrefetch = (params: McapTickDetailsPrefetchParams) => {
    const client = useQueryClient();
    let bufferedRanges = $state<TickRange[]>([]);
    let errors = $state<Map<number, unknown>>(new Map());

    const executor = createMcapTickPrefetchExecutor({
        ...params,
        client,
        onStateChange: (completed, nextErrors) => {
            bufferedRanges = getBufferedTickRanges(completed);
            errors = new Map(nextErrors);
        }
    });

    return {
        cancel: executor.cancel,
        prefetchRanges: executor.prefetchRanges,
        get bufferedRanges() {
            return bufferedRanges;
        },
        get errors() {
            return errors;
        }
    };
};
