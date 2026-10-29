import { readonly, writable } from 'svelte/store';

// Whether the images grid also shows images without annotations. The backend combines it
// with the selected annotation classes by OR.
const includeUnannotated = writable(false);

/**
 * The "No annotations" row of the annotation class filter on the images grid.
 */
export function useUnannotatedImagesFilter() {
    return {
        includeUnannotated: readonly(includeUnannotated),
        toggleIncludeUnannotated: () => includeUnannotated.update((value) => !value),
        clearIncludeUnannotated: () => includeUnannotated.set(false)
    };
}
