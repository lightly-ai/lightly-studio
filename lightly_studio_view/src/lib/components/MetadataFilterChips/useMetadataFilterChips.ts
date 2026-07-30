import { derived, writable, get } from 'svelte/store';
import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
import { formatFloat, formatInteger } from '$lib/utils';
import { usePostHog } from '$lib/hooks';
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
    const { trackEvent } = usePostHog();

    const lastRanges = writable<BoundsMap>({});
    const lastCategoricalValues = writable<Record<string, CategoricalMetadataValue[]>>({});

    // metadataValues.subscribe((values) => {
    //     const bounds = get(metadataBounds);
    //     lastRanges.update((last) => {
    //         let next = last;
    //         for (const key of Object.keys(values)) {
    //             const bound = bounds[key];
    //             const value = values[key];
    //             const narrowed =
    //                 !!bound && !!value && (value.min > bound.min || value.max < bound.max);
    //             if (!narrowed) continue;
    //             const existing = last[key];
    //             if (!existing || existing.min !== value.min || existing.max !== value.max) {
    //                 next = { ...next, [key]: { min: value.min, max: value.max } };
    //             }
    //         }
    //         return next;
    //     });
    // });

    // categoricalMetadataValues.subscribe((catValues) => {
    //     lastCategoricalValues.update((last) => {
    //         let next = last;
    //         for (const [key, values] of Object.entries(catValues)) {
    //             if (values.length === 0) continue;
    //             const previous = last[key] ?? [];
    //             const unchanged =
    //                 previous.length === values.length &&
    //                 previous.every((v, i) => Object.is(v, values[i]));
    //             if (!unchanged) {
    //                 next = { ...next, [key]: [...values] };
    //             }
    //         }
    //         return next;
    //     });
    // });

    const chips = derived(
        [
            metadataBounds,
            metadataValues,
            categoricalMetadataValues,
            lastRanges,
            lastCategoricalValues
        ],
        ([$bounds, $values, $catValues, $lastRanges, $lastCatValues]) => {
            const isNarrowed = (key: string): boolean => {
                const bound = $bounds[key];
                const value = $values[key];
                return !!bound && !!value && (value.min > bound.min || value.max < bound.max);
            };

            const numericKeys = new Set([
                ...Object.keys($lastRanges),
                ...Object.keys($values).filter(isNarrowed)
            ]);
            const numericChips = [...numericKeys]
                .filter((key) => $bounds[key])
                .map((key) => {
                    const active = isNarrowed(key);
                    const range: Range | undefined = active ? $values[key] : $lastRanges[key];
                    return range ? { key, active, range, kind: 'numeric' as const } : null;
                })
                .filter((chip): chip is NonNullable<typeof chip> => chip !== null);

            const categoricalKeys = new Set([
                ...Object.keys($lastCatValues),
                ...Object.entries($catValues)
                    .filter(([, values]) => values.length > 0)
                    .map(([key]) => key)
            ]);
            const categoricalChips: MetadataFilterChip[] = [...categoricalKeys].map((key) => {
                const current = $catValues[key] ?? [];
                return {
                    key,
                    active: current.length > 0,
                    kind: 'categorical',
                    values: current.length > 0 ? current : $lastCatValues[key]
                };
            });

            return [...numericChips, ...categoricalChips];
        }
    );

    const setRange = (key: string, range: Range) => {
        updateMetadataValues({ ...get(metadataValues), [key]: range });
    };

    const trackFilterChanged = (key: string, action: 'enabled' | 'disabled') => {
        if (!collectionId) return;
        trackEvent('metadata_filter_changed', {
            collection_id: collectionId,
            field_name: key,
            action
        });
    };

    const handleToggle = (key: string, checked: boolean | 'indeterminate') => {
        const $lastCatValues = get(lastCategoricalValues);
        if ($lastCatValues[key]) {
            updateCategoricalMetadataValues({
                ...get(categoricalMetadataValues),
                [key]: checked ? $lastCatValues[key] : []
            });
            return;
        }
        const bound = get(metadataBounds)[key];
        if (!bound) return;
        if (checked && get(lastRanges)[key]) {
            setRange(key, get(lastRanges)[key]);
        } else {
            setRange(key, { min: bound.min, max: bound.max });
        }
        trackFilterChanged(key, checked ? 'enabled' : 'disabled');
    };

    const handleClear = (key: string) => {
        const $lastCatValues = get(lastCategoricalValues);
        if ($lastCatValues[key]) {
            const next = { ...get(categoricalMetadataValues) };
            delete next[key];
            updateCategoricalMetadataValues(next);
            lastCategoricalValues.update((vals) => {
                const updated = { ...vals };
                delete updated[key];
                return updated;
            });
            return;
        }
        const bound = get(metadataBounds)[key];
        if (bound) setRange(key, { min: bound.min, max: bound.max });
        lastRanges.update((ranges) => {
            const updated = { ...ranges };
            delete updated[key];
            return updated;
        });
        trackFilterChanged(key, 'disabled');
    };

    const formatValue = (key: string, value: number): string => {
        const bound = get(metadataBounds)[key];
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
        chips,
        handleToggle,
        handleClear,
        formatValue,
        formatCategoricalValues
    };
}
