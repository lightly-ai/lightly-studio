import { useOrthographicDrag } from '../useOrthographicDrag.svelte';
import { applyRotationDrag, createRotationDrag } from './rotationRing';

export function useRotationRing(params: Parameters<typeof useOrthographicDrag>[0]) {
    return useOrthographicDrag(params, { create: createRotationDrag, apply: applyRotationDrag });
}
