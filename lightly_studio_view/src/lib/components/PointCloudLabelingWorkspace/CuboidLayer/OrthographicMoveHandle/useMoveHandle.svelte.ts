import { useOrthographicDrag } from '../useOrthographicDrag.svelte';
import { applyMoveDrag, createMoveDrag } from './moveHandle';

export function useMoveHandle(params: Parameters<typeof useOrthographicDrag>[0]) {
    return useOrthographicDrag(params, { create: createMoveDrag, apply: applyMoveDrag });
}
