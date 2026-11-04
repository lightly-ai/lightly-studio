import { fromStore } from 'svelte/store';
import { useFiltersClearedSignal } from '$lib/hooks';
import { formatFloat, formatInteger } from '$lib/utils';

export type Range = { min: number; max: number };
export type RangeMap = Record<string, Range | undefined>;

export interface RangeChip {
    key: string;
    active: boolean;
    range: Range;
}

interface UseRangeChipsParams {
    getBounds: () => RangeMap;
    getValues: () => RangeMap;
    setRange: (key: string, range: Range) => void;
    onChanged?: (key: string, action: 'enabled' | 'disabled') => void;
}

/**
 * One chip per range filter that is narrowed now or was narrowed before.
 *
 * Unchecking a chip resets the range to its bounds and remembers the range, so checking
 * the chip again restores it. Clearing forgets the range.
 */
export function useRangeChips({ getBounds, getValues, setRange, onChanged }: UseRangeChipsParams) {
    const filtersCleared = fromStore(useFiltersClearedSignal().filtersCleared);
    let lastRanges = $state<Record<string, Range>>({});

    // Forget all remembered ranges when all filters are cleared at once.
    $effect(() => {
        void filtersCleared.current;
        lastRanges = {};
    });

    const isNarrowed = (key: string): boolean => {
        const bound = getBounds()[key];
        const value = getValues()[key];
        return !!bound && !!value && (value.min > bound.min || value.max < bound.max);
    };

    // Remember the latest narrowed range of every key.
    $effect(() => {
        for (const [key, value] of Object.entries(getValues())) {
            if (!value || !isNarrowed(key)) continue;
            const last = lastRanges[key];
            if (!last || last.min !== value.min || last.max !== value.max) {
                lastRanges = { ...lastRanges, [key]: { min: value.min, max: value.max } };
            }
        }
    });

    const chips = $derived.by<RangeChip[]>(() => {
        const keys = new Set([
            ...Object.keys(lastRanges),
            ...Object.keys(getValues()).filter(isNarrowed)
        ]);
        return [...keys].flatMap((key) => {
            if (!getBounds()[key]) return [];
            const active = isNarrowed(key);
            const range = active ? getValues()[key] : lastRanges[key];
            return range ? [{ key, active, range }] : [];
        });
    });

    const resetToBounds = (key: string) => {
        const bound = getBounds()[key];
        if (bound) setRange(key, { min: bound.min, max: bound.max });
    };

    const handleToggle = (key: string, checked: boolean | 'indeterminate') => {
        if (checked && lastRanges[key]) setRange(key, lastRanges[key]);
        else resetToBounds(key);
        onChanged?.(key, checked ? 'enabled' : 'disabled');
    };

    const handleClear = (key: string) => {
        resetToBounds(key);
        lastRanges = Object.fromEntries(
            Object.entries(lastRanges).filter(([rangeKey]) => rangeKey !== key)
        );
        onChanged?.(key, 'disabled');
    };

    const formatValue = (key: string, value: number): string => {
        const bound = getBounds()[key];
        const isInteger = !!bound && Number.isInteger(bound.min) && Number.isInteger(bound.max);
        return isInteger ? formatInteger(value) : formatFloat(value);
    };

    return {
        get chips() {
            return chips;
        },
        handleToggle,
        handleClear,
        formatValue
    };
}
