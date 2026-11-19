import { readonly, writable } from 'svelte/store';

const includeUnannotatedSamples = writable(false);
let scopedCollectionId: string | undefined;

/** Holds whether the image and video grids also show the samples without annotations. */
export function useUnannotatedSamplesFilter() {
    return {
        includeUnannotatedSamples: readonly(includeUnannotatedSamples),
        setIncludeUnannotatedSamples: (include: boolean) => includeUnannotatedSamples.set(include),
        /** Clears the filter when the collection changes, so it never leaks across datasets. */
        scopeToCollection: (collectionId: string) => {
            if (collectionId === scopedCollectionId) return;
            scopedCollectionId = collectionId;
            includeUnannotatedSamples.set(false);
        }
    };
}
