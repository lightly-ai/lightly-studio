import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get, type Writable } from 'svelte/store';

const mocks = vi.hoisted(() => ({
    store: null as unknown as Writable<string[]>
}));

vi.mock('$lib/hooks/useSessionStorage/useSessionStorage', async () => {
    const { writable } = await import('svelte/store');
    mocks.store = writable<string[]>([]);
    return { useSessionStorage: () => mocks.store };
});

import { useAnnotationClassVisibility } from './useAnnotationClassVisibility';

describe('useAnnotationClassVisibility', () => {
    beforeEach(() => {
        mocks.store.set([]);
    });

    it('initializes with an empty list', () => {
        const { hiddenClassNamesStore } = useAnnotationClassVisibility();
        expect(get(hiddenClassNamesStore)).toEqual([]);
    });

    it('toggleClassVisibility adds a label when not hidden', () => {
        const { hiddenClassNamesStore, toggleClassVisibility } = useAnnotationClassVisibility();

        toggleClassVisibility('car');

        expect(get(hiddenClassNamesStore)).toContain('car');
    });

    it('toggleClassVisibility removes a label when already hidden', () => {
        const { hiddenClassNamesStore, toggleClassVisibility } = useAnnotationClassVisibility();

        toggleClassVisibility('car');
        toggleClassVisibility('car');

        expect(get(hiddenClassNamesStore)).not.toContain('car');
    });

    it('toggleClassVisibility handles multiple labels independently', () => {
        const { hiddenClassNamesStore, toggleClassVisibility } = useAnnotationClassVisibility();

        toggleClassVisibility('car');
        toggleClassVisibility('person');

        expect(get(hiddenClassNamesStore)).toContain('car');
        expect(get(hiddenClassNamesStore)).toContain('person');

        toggleClassVisibility('car');

        expect(get(hiddenClassNamesStore)).not.toContain('car');
        expect(get(hiddenClassNamesStore)).toContain('person');
    });

    it('isClassHidden returns false for a visible label', () => {
        const { isClassHidden } = useAnnotationClassVisibility();

        expect(get(isClassHidden('car'))).toBe(false);
    });

    it('isClassHidden returns true for a hidden label', () => {
        const { isClassHidden, toggleClassVisibility } = useAnnotationClassVisibility();

        toggleClassVisibility('car');

        expect(get(isClassHidden('car'))).toBe(true);
    });

    it('isClassHidden reacts to toggleClassVisibility changes', () => {
        const { isClassHidden, toggleClassVisibility } = useAnnotationClassVisibility();

        const hidden = isClassHidden('car');
        expect(get(hidden)).toBe(false);

        toggleClassVisibility('car');
        expect(get(hidden)).toBe(true);

        toggleClassVisibility('car');
        expect(get(hidden)).toBe(false);
    });
});
