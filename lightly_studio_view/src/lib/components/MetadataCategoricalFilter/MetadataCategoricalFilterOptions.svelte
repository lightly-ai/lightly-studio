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
        onClear: () => void;
    }

    const { buckets, selectedValues, loading, error, listMode, onToggle, onClear }: Props =
        $props();
    const options = $derived(buildOptions(buckets, selectedValues));
    const valueById = $derived(new Map(options.map(({ bucket }) => [bucket.id, bucket.value])));
    const showSearch = $derived(buckets.filter((bucket) => bucket.kind === 'value').length > 5);
    const hasOtherAggregate = $derived(buckets.some((bucket) => bucket.kind === 'other'));
    const isSelected = (value: CategoricalMetadataValue) =>
        selectedValues.some((selected) => Object.is(selected, value));

    const items = $derived(
        options.map((option) => {
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
    const emptyText = $derived(
        listMode && error
            ? 'Could not load metadata distribution.'
            : listMode && loading
              ? 'Loading…'
              : listMode
                ? 'No values are available under the current filters.'
                : 'No values found.'
    );

    // Apply a full selection, e.g. from "Select all", as toggles of the changed values.
    const handleSelectionChange = (ids: string[]) => {
        if (ids.length === 0) {
            onClear();
            return;
        }
        items
            .filter((item) => ids.includes(item.id) !== item.selected)
            .forEach((item) => onToggle(valueById.get(item.id)!));
    };
</script>

<div class="max-h-72 overflow-y-auto">
    <FilterList
        {items}
        onToggle={(id) => onToggle(valueById.get(id)!)}
        onSelectionChange={handleSelectionChange}
        testId="metadata-values"
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
