import { get } from 'svelte/store';
import { afterEach, describe, expect, it } from 'vitest';
import {
    ANNOTATE_VARIANT_STORAGE_KEY,
    resetAnnotateVariantForTest,
    resolveAnnotateVariant,
    TARGET_PICK_MESSAGES,
    useAnnotateVariant
} from './useAnnotateVariant';
import { getTargetBlockedReason } from '$lib/hooks/useAnnotationTarget/resolveTargetSource';

describe('resolveAnnotateVariant', () => {
    it('shows the pencil when nothing is set', () => {
        expect(resolveAnnotateVariant(null, null)).toBe('pencil');
    });

    it('takes the URL param over the stored variant', () => {
        expect(resolveAnnotateVariant('radio', 'pencil')).toBe('radio');
        expect(resolveAnnotateVariant('pencil', 'radio')).toBe('pencil');
    });

    it('keeps the stored variant when the URL has none', () => {
        expect(resolveAnnotateVariant(null, 'radio')).toBe('radio');
    });

    it('ignores unknown values', () => {
        expect(resolveAnnotateVariant('b', 'radio')).toBe('radio');
        expect(resolveAnnotateVariant('b', 'garbage')).toBe('pencil');
    });
});

describe('useAnnotateVariant', () => {
    afterEach(() => {
        localStorage.clear();
        window.history.replaceState(null, '', '/');
        resetAnnotateVariantForTest();
    });

    it('reads the URL param and keeps it for later page loads', () => {
        window.history.replaceState(null, '', '/?annotateVariant=radio');

        expect(get(useAnnotateVariant().annotateVariant)).toBe('radio');
        expect(localStorage.getItem(ANNOTATE_VARIANT_STORAGE_KEY)).toBe('radio');
    });

    it('shows the stored variant on a page without the param', () => {
        localStorage.setItem(ANNOTATE_VARIANT_STORAGE_KEY, 'radio');

        expect(get(useAnnotateVariant().annotateVariant)).toBe('radio');
    });
});

describe('TARGET_PICK_MESSAGES', () => {
    it('tells the user how to pick a source in the words of the variant', () => {
        expect(getTargetBlockedReason(null, false, TARGET_PICK_MESSAGES.radio)).toBe(
            'Choose where new annotations go: pick a source in the Annotations panel.'
        );
        expect(getTargetBlockedReason(null, false, TARGET_PICK_MESSAGES.pencil)).toContain(
            'pencil'
        );
    });
});
