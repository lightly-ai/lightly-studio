<script lang="ts">
    import { FilterList, type FilterListItem } from '$lib/components/FilterList';
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
        onClear: () => void;
    }

    const { buckets, selectedValues, loading, error, listMode, onToggle, onClear }: Props =
        $props();
    const options = $derived(buildOptions(buckets, selectedValues));
    const isSelected = (value: CategoricalMetadataValue) =>
        selectedValues.some((selected) => Object.is(selected, value));
    const items = $derived(
        options.map((option): FilterListItem => {
            const label = getOptionLabel(option, options, buckets);
            return {
                id: option.bucket.id,
                label,
                selected: isSelected(option.bucket.value),
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
        options
            .filter(({ bucket }) => wanted.has(bucket.id) && !isSelected(bucket.value))
            .forEach(({ bucket }) => onToggle(bucket.value));
    };
</script>

<div class="max-h-56 overflow-y-auto">
    <FilterList
        {items}
        onToggle={toggleById}
        onSelectionChange={changeSelection}
        testId="metadata-value-list"
        {showSearch}
        searchPlaceholder="Search values…"
        {emptyText}
        noMatchText="No values found."
    />
    {#if hasOtherAggregate}
        <p class="p-2 text-xs text-muted-foreground">
            Other is an aggregate and cannot be selected.
        </p>
    {/if}
</div>
