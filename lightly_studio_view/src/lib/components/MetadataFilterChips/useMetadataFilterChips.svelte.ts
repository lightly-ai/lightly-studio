import { get } from 'svelte/store';
import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
import { formatFloat, formatInteger } from '$lib/utils';

type Range = { min: number; max: number };
type BoundsMap = Record<string, Range>;

export interface MetadataFilterChip {
    key: string;
    active: boolean;
    range: Range;
}

export function useMetadataFilterChips(collectionId: string | undefined) {
    const { metadataBounds, metadataValues, updateMetadataValues } =
        useMetadataFilters(collectionId);

    // Mirror the stores into reactive state so rune-based derivations track them.
    let bounds = $state<BoundsMap>(get(metadataBounds));
    let values = $state<BoundsMap>(get(metadataValues));

    $effect(() => {
        const unsubBounds = metadataBounds.subscribe((v) => {
            bounds = v;
        });
        const unsubValues = metadataValues.subscribe((v) => {
            values = v;
        });
        return () => {
            unsubBounds();
            unsubValues();
        };
    });

    let lastRanges = $state<BoundsMap>({});

    const isNarrowed = (key: string): boolean => {
        const bound = bounds[key];
        const value = values[key];
        return !!bound && !!value && (value.min > bound.min || value.max < bound.max);
    };

    // Remember the latest narrowed range of every key.
    $effect(() => {
        for (const key of Object.keys(values)) {
            if (!isNarrowed(key)) continue;
            const value = values[key];
            const last = lastRanges[key];
            if (!last || last.min !== value.min || last.max !== value.max) {
                lastRanges = { ...lastRanges, [key]: { min: value.min, max: value.max } };
            }
        }
    });

    // One chip per key that is narrowed now or has a remembered range: active
    // chips show the current range, disabled ones the remembered range.
    const chips = $derived.by<MetadataFilterChip[]>(() => {
        const keys = new Set([
            ...Object.keys(lastRanges),
            ...Object.keys(values).filter(isNarrowed)
        ]);
        return [...keys]
            .filter((key) => bounds[key])
            .map((key) => {
                const active = isNarrowed(key);
                const range: Range | undefined = active ? values[key] : lastRanges[key];
                return { key, active, range };
            })
            .filter((chip): chip is MetadataFilterChip => !!chip.range);
    });

    const setRange = (key: string, range: Range) => {
        updateMetadataValues({ ...values, [key]: range });
    };

    const handleToggle = (key: string, checked: boolean | 'indeterminate') => {
        const bound = bounds[key];
        if (!bound) return;
        if (checked && lastRanges[key]) {
            setRange(key, lastRanges[key]);
        } else {
            setRange(key, { min: bound.min, max: bound.max });
        }
    };

    const handleClear = (key: string) => {
        const bound = bounds[key];
        if (bound) setRange(key, { min: bound.min, max: bound.max });
        lastRanges = Object.fromEntries(
            Object.entries(lastRanges).filter(([rangeKey]) => rangeKey !== key)
        );
    };

    const formatValue = (key: string, value: number): string => {
        const bound = bounds[key];
        const isInteger = !!bound && Number.isInteger(bound.min) && Number.isInteger(bound.max);
        return isInteger ? formatInteger(value) : formatFloat(value);
    };

    return { chips, handleToggle, handleClear, formatValue };
}
