import { untrack } from 'svelte';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { getBoundingBox } from '$lib/components/SampleAnnotation/utils';
import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import type { BoundingBox } from '$lib/types';

/**
 * The box the card sits beside. After a move or resize of the annotation it is the dropped box,
 * so the card doesn't wait for the save and the refetch. The next annotation from the server
 * wins again. Call during component init.
 */
export const useCardBox = (getAnnotation: () => AnnotationView) => {
    const { context } = useAnnotationLabelContext();
    const savedBox = $derived(getBoundingBox(getAnnotation()));
    let droppedBox = $state<BoundingBox | null>(null);
    // A move from before the card opened may be undone since, so only later moves count.
    let lastMove = untrack(() => context.movedAnnotation);

    $effect(() => {
        const move = context.movedAnnotation;
        if (move === lastMove) return;
        lastMove = move;
        if (move && move.annotationId === untrack(getAnnotation).sample_id) {
            droppedBox = move.bbox;
        }
    });
    $effect(() => {
        void savedBox;
        droppedBox = null;
    });

    return {
        get current() {
            return droppedBox ?? savedBox;
        }
    };
};
