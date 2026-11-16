<script lang="ts">
    import { FilterList } from '$lib/components/FilterList';
    import type { CategoricalMetadataBucket } from '$lib/hooks/useCategoricalMetadataDistribution/types';
    import type { CategoricalMetadataValue } from '$lib/services/types';
    import { buildOptions, getCheckboxLabel, getOptionLabel } from './helpers';

    interface Props {
        buckets: CategoricalMetadataBucket[];
        selectedValues: CategoricalMetadataValue[];
        loading: boolean;
        error?: string;
        listMode: boolean;
        onToggle: (value: CategoricalMetadataValue) => void;
        onSetValues: (values: CategoricalMetadataValue[]) => void;
        onClear: () => void;
    }

    const {
        buckets,
        selectedValues,
        loading,
        error,
        listMode,
        onToggle,
        onSetValues,
        onClear
    }: Props = $props();
    const options = $derived(buildOptions(buckets, selectedValues));
    const selected = $derived(new Set(selectedValues));
    const items = $derived(
        options.map((option) => {
            const label = getOptionLabel(option, options, buckets);
            return {
                id: option.bucket.id,
                label,
                selected: selected.has(option.bucket.value),
                count: option.retained ? 'Not in current results' : String(option.bucket.count),
                ariaLabel: getCheckboxLabel(option, label)
            };
        })
    );
    const showSearch = $derived(buckets.filter((bucket) => bucket.kind === 'value').length > 5);
    const hasOtherAggregate = $derived(buckets.some((bucket) => bucket.kind === 'other'));
    const emptyText = $derived(
        listMode && error
            ? 'Could not load metadata distribution.'
            : listMode && loading
              ? 'Loading…'
              : listMode
                ? 'No values are available under the current filters.'
                : 'No values found.'
    );

    const toggleById = (id: string) => {
        const option = options.find(({ bucket }) => bucket.id === id);
        if (option) onToggle(option.bucket.value);
    };
    const changeSelection = (ids: string[]) => {
        if (ids.length === 0) {
            onClear();
            return;
        }
        const wanted = new Set(ids);
        onSetValues(
            options.filter(({ bucket }) => wanted.has(bucket.id)).map(({ bucket }) => bucket.value)
        );
    };
</script>

<FilterList
    {items}
    onToggle={toggleById}
    onSelectionChange={changeSelection}
    testId="metadata-value-list"
    {showSearch}
    searchPlaceholder="Search values…"
    {emptyText}
    noMatchText="No values found."
    rowsClass="-mx-1 -mb-1 max-h-56 overflow-y-auto p-1"
/>
{#if hasOtherAggregate}
    <p class="p-2 text-xs text-muted-foreground">Other is an aggregate and cannot be selected.</p>
{/if}
