import { untrack } from 'svelte';
import { fromStore } from 'svelte/store';
import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
import { useFiltersClearedSignal, usePostHog } from '$lib/hooks';
import type { CategoricalMetadataValue } from '$lib/services/types';
import { useRangeChips } from './useRangeChips.svelte';

type Range = Parameters<Parameters<typeof useRangeChips>[0]['setRange']>[1];

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
    const filtersCleared = fromStore(useFiltersClearedSignal().filtersCleared);

    const boundsStore = fromStore(metadataBounds);
    const valuesStore = fromStore(metadataValues);
    const categoricalStore = fromStore(categoricalMetadataValues);

    const trackFilterChanged = (key: string, action: 'enabled' | 'disabled') => {
        if (!collectionId) return;
        trackEvent('metadata_filter_changed', {
            collection_id: collectionId,
            field_name: key,
            action
        });
    };

    const numeric = useRangeChips({
        getBounds: () => boundsStore.current,
        getValues: () => valuesStore.current,
        setRange: (key, range) => updateMetadataValues({ ...valuesStore.current, [key]: range }),
        onChanged: trackFilterChanged
    });

    let lastCategoricalValues = $state<Record<string, CategoricalMetadataValue[]>>({});

    let handledClears = untrack(() => filtersCleared.current);
    let ignoredCategoricalValues: Record<string, CategoricalMetadataValue[]> = {};
    const sameValues = (a: CategoricalMetadataValue[] = [], b: CategoricalMetadataValue[]) =>
        a.length === b.length && a.every((value, index) => Object.is(value, b[index]));

    // Forget all remembered selections when all filters are cleared at once. Selections that
    // are still set at that moment must not be remembered again before they change.
    $effect(() => {
        const clears = filtersCleared.current;
        if (clears === handledClears) return;
        handledClears = clears;
        ignoredCategoricalValues = untrack(() => ({ ...categoricalStore.current }));
        lastCategoricalValues = {};
    });

    $effect(() => {
        for (const [key, values] of Object.entries(categoricalStore.current)) {
            if (values.length === 0) continue;
            if (sameValues(ignoredCategoricalValues[key], values)) continue;
            delete ignoredCategoricalValues[key];
            if (!sameValues(lastCategoricalValues[key], values)) {
                lastCategoricalValues = { ...lastCategoricalValues, [key]: [...values] };
            }
        }
    });

    // Active chips show the current filter, disabled ones the remembered filter.
    const chips = $derived.by<MetadataFilterChip[]>(() => {
        const numericChips = numeric.chips.map((chip) => ({ ...chip, kind: 'numeric' as const }));
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

    const handleToggle = (key: string, checked: boolean | 'indeterminate') => {
        if (!lastCategoricalValues[key]) {
            numeric.handleToggle(key, checked);
            return;
        }
        updateCategoricalMetadataValues({
            ...categoricalStore.current,
            [key]: checked ? lastCategoricalValues[key] : []
        });
    };

    const handleClear = (key: string) => {
        if (!lastCategoricalValues[key]) {
            numeric.handleClear(key);
            return;
        }
        const next = { ...categoricalStore.current };
        delete next[key];
        updateCategoricalMetadataValues(next);
        lastCategoricalValues = Object.fromEntries(
            Object.entries(lastCategoricalValues).filter(([valueKey]) => valueKey !== key)
        );
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
        formatValue: numeric.formatValue,
        formatCategoricalValues
    };
}
