import { readonly, writable } from 'svelte/store';

/** ID of the "No annotations" row in the annotation class filter. */
export const NO_ANNOTATIONS_ROW_ID = '__no_annotations__';

const includeUnannotatedSamples = writable(false);

/** Holds whether the image and video grids also show the samples without annotations. */
export function useUnannotatedSamplesFilter() {
    return {
        includeUnannotatedSamples: readonly(includeUnannotatedSamples),
        setIncludeUnannotatedSamples: (include: boolean) => includeUnannotatedSamples.set(include)
    };
}
