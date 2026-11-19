import { readonly, writable } from 'svelte/store';

const includeUnannotatedSamples = writable(false);

/** Holds whether the image and video grids also show the samples without annotations. */
export function useUnannotatedSamplesFilter() {
    return {
        includeUnannotatedSamples: readonly(includeUnannotatedSamples),
        setIncludeUnannotatedSamples: (include: boolean) => includeUnannotatedSamples.set(include)
    };
}
