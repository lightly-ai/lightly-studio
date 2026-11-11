import { untrack } from 'svelte';
import { fromStore } from 'svelte/store';
import { useFiltersClearedSignal } from '$lib/hooks';
import { formatFloat, formatInteger } from '$lib/utils';

type Range = { min: number; max: number };
type RangeMap = Record<string, Range | undefined>;

interface RangeChip {
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

interface UseRangeChipsReturn {
    readonly chips: RangeChip[];
    handleToggle: (key: string, checked: boolean | 'indeterminate') => void;
    handleClear: (key: string) => void;
    formatValue: (key: string, value: number) => string;
}

/**
 * One chip per range filter that is narrowed now or was narrowed before.
 *
 * Unchecking a chip resets the range to its bounds and remembers the range, so checking
 * the chip again restores it. Clearing forgets the range. A remembered range is also
 * forgotten when the bounds of its key change, for example in another collection.
 */
export function useRangeChips({
    getBounds,
    getValues,
    setRange,
    onChanged
}: UseRangeChipsParams): UseRangeChipsReturn {
    const memory = useRememberedRanges(getBounds, getValues);
    const chips = $derived(buildChips(getBounds(), getValues(), memory.ranges));

    const resetToBounds = (key: string) => {
        const bound = getBounds()[key];
        if (bound) setRange(key, { min: bound.min, max: bound.max });
    };

    return {
        get chips() {
            return chips;
        },
        handleToggle: (key, checked) => {
            const last = memory.ranges[key];
            if (checked && last) setRange(key, last);
            else resetToBounds(key);
            onChanged?.(key, checked ? 'enabled' : 'disabled');
        },
        handleClear: (key) => {
            resetToBounds(key);
            memory.forget(key);
            onChanged?.(key, 'disabled');
        },
        formatValue: (key, value) => formatRangeValue(getBounds()[key], value)
    };
}

/** Remembers the latest narrowed range of every key. */
function useRememberedRanges(getBounds: () => RangeMap, getValues: () => RangeMap) {
    const filtersCleared = fromStore(useFiltersClearedSignal().filtersCleared);
    let ranges = $state<Record<string, Range>>({});
    let handledClears = untrack(() => filtersCleared.current);
    // Ranges still narrowed when all filters were cleared; not remembered until they change.
    let ignoredRanges: RangeMap = {};
    let previousBounds: RangeMap = {};

    $effect(() => {
        const clears = filtersCleared.current;
        if (clears === handledClears) return;
        handledClears = clears;
        ignoredRanges = untrack(() => ({ ...getValues() }));
        ranges = {};
    });

    $effect(() => {
        const bounds = getBounds();
        const remembered = untrack(() => ranges);
        const kept = Object.entries(remembered).filter(([key]) =>
            isSameRange(bounds[key], previousBounds[key])
        );
        previousBounds = bounds;
        if (kept.length !== Object.keys(remembered).length) ranges = Object.fromEntries(kept);
    });

    $effect(() => {
        const bounds = getBounds();
        for (const [key, value] of Object.entries(getValues())) {
            if (!value || !isNarrowed(bounds[key], value)) continue;
            if (isSameRange(ignoredRanges[key], value)) continue;
            delete ignoredRanges[key];
            if (
                !isSameRange(
                    untrack(() => ranges[key]),
                    value
                )
            ) {
                ranges = { ...ranges, [key]: { min: value.min, max: value.max } };
            }
        }
    });

    return {
        get ranges() {
            return ranges;
        },
        forget: (key: string) => {
            ranges = Object.fromEntries(Object.entries(ranges).filter(([k]) => k !== key));
        }
    };
}

function buildChips(bounds: RangeMap, values: RangeMap, remembered: RangeMap): RangeChip[] {
    const narrowedKeys = Object.keys(values).filter((key) => isNarrowed(bounds[key], values[key]));
    const keys = new Set([...Object.keys(remembered), ...narrowedKeys]);
    return [...keys].flatMap((key) => {
        if (!bounds[key]) return [];
        const active = isNarrowed(bounds[key], values[key]);
        const range = active ? values[key] : remembered[key];
        return range ? [{ key, active, range }] : [];
    });
}

function isNarrowed(bound: Range | undefined, value: Range | undefined): boolean {
    return !!bound && !!value && (value.min > bound.min || value.max < bound.max);
}

function isSameRange(a: Range | undefined, b: Range | undefined): boolean {
    return a?.min === b?.min && a?.max === b?.max;
}

function formatRangeValue(bound: Range | undefined, value: number): string {
    const isInteger = !!bound && Number.isInteger(bound.min) && Number.isInteger(bound.max);
    return isInteger ? formatInteger(value) : formatFloat(value);
}
