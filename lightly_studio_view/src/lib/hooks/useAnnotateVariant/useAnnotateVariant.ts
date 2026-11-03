import { readable, type Readable } from 'svelte/store';
import { PENCIL_PICK_MESSAGE } from '$lib/hooks/useAnnotationTarget/resolveTargetSource';

// Prototype switch between ways of picking the annotation source new annotations go to, so
// people can try each one. Delete the losing variant and this switch once one is chosen.

export const ANNOTATE_VARIANT_PARAM = 'annotateVariant';
export const ANNOTATE_VARIANT_STORAGE_KEY = 'lightly-studio.annotate-variant';

/**
 * - `pencil`: a pencil on each source group in the Annotations panel (the prototype as shown).
 * - `radio`: a radio on each source group, the picked one says "New annotations go here".
 */
export const ANNOTATE_VARIANTS = ['pencil', 'radio'] as const;
export type AnnotateVariant = (typeof ANNOTATE_VARIANTS)[number];

export const DEFAULT_ANNOTATE_VARIANT: AnnotateVariant = 'pencil';

/** What the "no source picked" toast tells the user to do, in the words of each variant. */
export const TARGET_PICK_MESSAGES: Record<AnnotateVariant, string> = {
    pencil: PENCIL_PICK_MESSAGE,
    radio: 'Choose where new annotations go: pick a source in the Annotations panel.'
};

const isAnnotateVariant = (value: string | null): value is AnnotateVariant =>
    ANNOTATE_VARIANTS.some((variant) => variant === value);

/**
 * Returns the variant to show, given the `annotateVariant` URL param and the value stored by an
 * earlier visit. Either may be null or any string a user typed.
 */
export const resolveAnnotateVariant = (
    urlParam: string | null,
    stored: string | null
): AnnotateVariant => {
    if (isAnnotateVariant(urlParam)) return urlParam;
    if (isAnnotateVariant(stored)) return stored;
    return DEFAULT_ANNOTATE_VARIANT;
};

/** Reads the URL param once per page load and keeps a valid one for later visits. */
function loadVariant(): AnnotateVariant {
    try {
        const urlParam = new URLSearchParams(window.location.search).get(ANNOTATE_VARIANT_PARAM);
        const variant = resolveAnnotateVariant(
            urlParam,
            localStorage.getItem(ANNOTATE_VARIANT_STORAGE_KEY)
        );
        localStorage.setItem(ANNOTATE_VARIANT_STORAGE_KEY, variant);
        return variant;
    } catch {
        // No window or storage (SSR, private mode): show the default.
        return DEFAULT_ANNOTATE_VARIANT;
    }
}

let variantStore: Readable<AnnotateVariant> | null = null;

/** The annotation source picker variant to show in sample details. */
export function useAnnotateVariant(): { annotateVariant: Readable<AnnotateVariant> } {
    variantStore ??= readable(loadVariant());
    return { annotateVariant: variantStore };
}

/** Resets the cached variant, so a test can load it again. */
export function resetAnnotateVariantForTest(): void {
    variantStore = null;
}
