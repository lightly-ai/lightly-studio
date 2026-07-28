<script lang="ts">
    import type { CategoricalMetadataBucket } from '$lib/hooks/useCategoricalMetadataDistribution/types';
    import type { CategoricalMetadataValue } from '$lib/services/types';
    import { getOptionLabel, getCheckboxLabel, buildOptions, type FilterOption } from './helpers';

    import MetadataCategoricalFilterPopover from './MetadataCategoricalFilterPopover/MetadataCategoricalFilterPopover.svelte';

    interface Props {
        buckets: CategoricalMetadataBucket[];
        selectedValues: CategoricalMetadataValue[];
        loading?: boolean;
        onToggle: (value: CategoricalMetadataValue) => void;
        onClear: () => void;
    }

    const { buckets, selectedValues, loading = false, onToggle, onClear }: Props = $props();

    const options = $derived(buildOptions(buckets, selectedValues));
    const optionLabel = (option: FilterOption) => getOptionLabel(option, options, buckets);
    const checkboxLabel = (option: FilterOption) => getCheckboxLabel(option, optionLabel(option));
    const showSearch = $derived(buckets.filter((b) => b.kind === 'value').length > 5);
    const hasOtherAggregate = $derived(buckets.some((b) => b.kind === 'other'));
    const disabled = $derived(loading && buckets.length === 0);
    const isSelected = (value: CategoricalMetadataValue) =>
        selectedValues.some((selected) => Object.is(selected, value));
    const summary = $derived(
        selectedValues.length === 0
            ? 'All values'
            : selectedValues.length === 1
              ? optionLabel(
                    options.find(({ bucket }) => Object.is(bucket.value, selectedValues[0]))!
                )
              : `${selectedValues.length} selected`
    );
</script>

<div class="mt-2 flex items-center gap-2" data-testid="metadata-categorical-filter">
    <span class="w-[100px] shrink-0 text-xs text-muted-foreground">Values</span>
    <MetadataCategoricalFilterPopover
        {options}
        {showSearch}
        {hasOtherAggregate}
        {disabled}
        {loading}
        {summary}
        {selectedValues}
        {isSelected}
        {optionLabel}
        {checkboxLabel}
        {onToggle}
        {onClear}
    />
</div>
