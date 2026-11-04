import { afterEach, describe, expect, it, vi } from 'vitest';
import { flushSync } from 'svelte';
import { useRangeChips, type RangeMap } from './useRangeChips.svelte';

const bounds: RangeMap = { confidence: { min: 0, max: 1 } };

let cleanup: (() => void) | undefined;

const setup = (initial: RangeMap) => {
    let values = $state<RangeMap>(initial);
    const setRange = vi.fn((key: string, range: { min: number; max: number }) => {
        values = { ...values, [key]: range };
    });
    const onChanged = vi.fn();
    let hook!: ReturnType<typeof useRangeChips>;
    cleanup = $effect.root(() => {
        hook = useRangeChips({
            getBounds: () => bounds,
            getValues: () => values,
            setRange,
            onChanged
        });
    });
    flushSync();
    return { hook, setRange, onChanged, setValues: (next: RangeMap) => (values = next) };
};

describe('useRangeChips', () => {
    afterEach(() => cleanup?.());

    it('gives no chip for a range equal to its bounds', () => {
        const { hook } = setup({ confidence: { min: 0, max: 1 } });

        expect(hook.chips).toEqual([]);
    });

    it('activates the chip when the range is narrowed', () => {
        const { hook, setValues } = setup({ confidence: { min: 0, max: 1 } });

        setValues({ confidence: { min: 0.25, max: 0.75 } });
        flushSync();

        expect(hook.chips).toEqual([
            { key: 'confidence', active: true, range: { min: 0.25, max: 0.75 } }
        ]);
    });

    it('resets to the bounds when a chip is removed and reports it', () => {
        const { hook, setRange, onChanged } = setup({ confidence: { min: 0.25, max: 0.75 } });

        hook.handleClear('confidence');
        flushSync();

        expect(setRange).toHaveBeenCalledWith('confidence', { min: 0, max: 1 });
        expect(onChanged).toHaveBeenCalledWith('confidence', 'disabled');
        expect(hook.chips).toEqual([]);
    });

    it('keeps an unchecked chip inactive and restores its range when checked again', () => {
        const { hook, setRange, onChanged } = setup({ confidence: { min: 0.25, max: 0.75 } });

        hook.handleToggle('confidence', false);
        flushSync();
        expect(hook.chips).toEqual([
            { key: 'confidence', active: false, range: { min: 0.25, max: 0.75 } }
        ]);

        hook.handleToggle('confidence', true);
        expect(setRange).toHaveBeenLastCalledWith('confidence', { min: 0.25, max: 0.75 });
        expect(onChanged).toHaveBeenLastCalledWith('confidence', 'enabled');
    });
});
