import { fromStore } from 'svelte/store';
import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
import { formatFloat, formatInteger } from '$lib/utils';
import type { CategoricalMetadataValue } from '$lib/services/types';

type Range = { min: number; max: number };
type BoundsMap = Record<string, Range>;

export interface MetadataFilterChip {
    key: string;
    active: boolean;
    kind: 'numeric' | 'categorical';
    range?: Range;
    values?: CategoricalMetadataValue[];
}

export function useMetadataFilterChips(collectionId: string | undefined) {
    const {
        metadataBounds,
        metadataValues,
        categoricalMetadataValues,
        updateMetadataValues,
        updateCategoricalMetadataValues
    } = useMetadataFilters(collectionId);

    const boundsStore = fromStore(metadataBounds);
    const valuesStore = fromStore(metadataValues);
    const categoricalStore = fromStore(categoricalMetadataValues);

    let lastRanges = $state<BoundsMap>({});
    let lastCategoricalValues = $state<Record<string, CategoricalMetadataValue[]>>({});

    const isNarrowed = (key: string): boolean => {
        const bound = boundsStore.current[key];
        const value = valuesStore.current[key];
        return !!bound && !!value && (value.min > bound.min || value.max < bound.max);
    };

    // Remember the latest narrowed range of every key.
    $effect(() => {
        for (const key of Object.keys(valuesStore.current)) {
            if (!isNarrowed(key)) continue;
            const value = valuesStore.current[key];
            const last = lastRanges[key];
            if (!last || last.min !== value.min || last.max !== value.max) {
                lastRanges = { ...lastRanges, [key]: { min: value.min, max: value.max } };
            }
        }
    });

    $effect(() => {
        for (const [key, values] of Object.entries(categoricalStore.current)) {
            if (values.length === 0) continue;
            const previous = lastCategoricalValues[key] ?? [];
            const unchanged =
                previous.length === values.length &&
                previous.every((value, index) => Object.is(value, values[index]));
            if (!unchanged) {
                lastCategoricalValues = { ...lastCategoricalValues, [key]: [...values] };
            }
        }
    });

    // One chip per key that is narrowed now or has a remembered range: active
    // chips show the current range, disabled ones the remembered range.
    const chips = $derived.by<MetadataFilterChip[]>(() => {
        const keys = new Set([
            ...Object.keys(lastRanges),
            ...Object.keys(valuesStore.current).filter(isNarrowed)
        ]);
        const numericChips = [...keys]
            .filter((key) => boundsStore.current[key])
            .map((key) => {
                const active = isNarrowed(key);
                const range: Range | undefined = active
                    ? valuesStore.current[key]
                    : lastRanges[key];
                return range ? { key, active, range, kind: 'numeric' as const } : null;
            })
            .filter((chip): chip is NonNullable<typeof chip> => chip !== null);
        const categoricalKeys = new Set([
            ...Object.keys(lastCategoricalValues),
            ...Object.entries(categoricalStore.current)
                .filter(([, values]) => values.length > 0)
                .map(([key]) => key)
        ]);
        const categoricalChips: MetadataFilterChip[] = [...categoricalKeys].map((key) => {
            const current = categoricalStore.current[key] ?? [];
            return {
                key,
                active: current.length > 0,
                kind: 'categorical',
                values: current.length > 0 ? current : lastCategoricalValues[key]
            };
        });
        return [...numericChips, ...categoricalChips];
    });

    const setRange = (key: string, range: Range) => {
        updateMetadataValues({ ...valuesStore.current, [key]: range });
    };

    const handleToggle = (key: string, checked: boolean | 'indeterminate') => {
        if (lastCategoricalValues[key]) {
            updateCategoricalMetadataValues({
                ...categoricalStore.current,
                [key]: checked ? lastCategoricalValues[key] : []
            });
            return;
        }
        const bound = boundsStore.current[key];
        if (!bound) return;
        if (checked && lastRanges[key]) {
            setRange(key, lastRanges[key]);
        } else {
            setRange(key, { min: bound.min, max: bound.max });
        }
    };

    const handleClear = (key: string) => {
        if (lastCategoricalValues[key]) {
            const next = { ...categoricalStore.current };
            delete next[key];
            updateCategoricalMetadataValues(next);
            lastCategoricalValues = Object.fromEntries(
                Object.entries(lastCategoricalValues).filter(([valueKey]) => valueKey !== key)
            );
            return;
        }
        const bound = boundsStore.current[key];
        if (bound) setRange(key, { min: bound.min, max: bound.max });
        lastRanges = Object.fromEntries(
            Object.entries(lastRanges).filter(([rangeKey]) => rangeKey !== key)
        );
    };

    const formatValue = (key: string, value: number): string => {
        const bound = boundsStore.current[key];
        const isInteger = !!bound && Number.isInteger(bound.min) && Number.isInteger(bound.max);
        return isInteger ? formatInteger(value) : formatFloat(value);
    };

    const formatCategoricalValues = (values: CategoricalMetadataValue[] = []): string => {
        const hasMissingValue = values.includes('Missing');
        const hasNoValue = values.includes(null);
        return values
            .map((value) => {
                if (value === null) return hasMissingValue ? 'Missing (no value)' : 'Missing';
                if (value === 'Missing' && hasNoValue) return 'Missing (value)';
                if (value === 'Other') return 'Other (value)';
                return String(value);
            })
            .join(', ');
    };

    return {
        get chips() {
            return chips;
        },
        handleToggle,
        handleClear,
        formatValue,
        formatCategoricalValues
    };
}
