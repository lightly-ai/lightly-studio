import { createQuery, type CreateQueryResult } from '@tanstack/svelte-query';
import type { TickData, TickDataParams } from './fetchTickData';
import { getTickDataOptions } from './getTickDataOptions';

interface UseTickCameraFramesReturn {
    /** Query result for the tick's camera images, keyed by channel id. */
    query: CreateQueryResult<TickData['cameraFrames'], Error>;
}

/**
 * Exposes the camera images of a tick from the shared tick-data query. Keeps the previous
 * tick's images while the next tick loads.
 */
export const useTickCameraFrames = (getParams: () => TickDataParams): UseTickCameraFramesReturn => {
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
