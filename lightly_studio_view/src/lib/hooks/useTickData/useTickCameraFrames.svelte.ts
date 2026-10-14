import { createQuery, type CreateQueryResult } from '@tanstack/svelte-query';
import type { TickData, TickDataParams } from './fetchTickData';
import { getTickDataOptions } from './getTickDataOptions';

interface UseTickCameraFramesReturn {
    /** Query result for the tick's camera images, keyed by channel id. */
    query: CreateQueryResult<TickData['cameraFrames'], Error>;
}

/**
 * Loads a tick's sensor data and exposes its camera images.
 *
 * Shares the cached tick request with the point-cloud view and the prefetch. The previous
 * tick's images stay available while the next tick loads.
 */
export const useTickCameraFrames = (
    getParams: () => Omit<TickDataParams, 'cameraHeight'>
): UseTickCameraFramesReturn => {
    const query = createQuery(() => {
        const params = getParams();
        return {
            ...getTickDataOptions(params),
            select: (data: TickData) => data.cameraFrames,
            enabled: Boolean(params.datasetId && params.sequenceId),
            placeholderData: (previous: TickData | undefined) => previous
        };
    });
    return { query };
};
