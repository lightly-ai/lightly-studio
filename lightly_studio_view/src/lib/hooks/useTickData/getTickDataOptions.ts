import { fetchTickData, type TickDataParams } from './fetchTickData';

/** Height of the camera images of a tick; the strip tiles are smaller than this. */
export const TICK_CAMERA_HEIGHT_PX = 360;

/** Builds the cacheable query for one tick's sensor data, shared by every view and the prefetch. */
export const getTickDataOptions = (params: Omit<TickDataParams, 'cameraHeight'>) => ({
    queryKey: [
        'tick-data',
        params.datasetId,
        params.sequenceId,
        params.seqNumber,
        params.displayFrameId ?? ''
    ],
    queryFn: ({ signal }: { signal?: AbortSignal }) =>
        fetchTickData({ ...params, cameraHeight: TICK_CAMERA_HEIGHT_PX }, signal)
});
