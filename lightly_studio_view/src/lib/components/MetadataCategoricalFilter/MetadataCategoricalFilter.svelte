<script lang="ts">
    import type { CategoricalMetadataBucket } from '$lib/hooks/useCategoricalMetadataDistribution/types';
    import type { CategoricalMetadataValue } from '$lib/services/types';
    import { buildOptions, getOptionLabel } from './helpers';
    import MetadataCategoricalFilterLayout from './MetadataCategoricalFilterLayout.svelte';
    import MetadataCategoricalFilterOptions from './MetadataCategoricalFilterOptions.svelte';
    import MetadataCategoricalFilterStatus from './MetadataCategoricalFilterStatus.svelte';

    interface Props {
        fieldLabel?: string;
        buckets: CategoricalMetadataBucket[];
        selectedValues: CategoricalMetadataValue[];
        loading?: boolean;
        updating?: boolean;
        error?: string;
        onRetry?: () => void;
        onToggle: (value: CategoricalMetadataValue) => void;
        /** Replaces the selected values in one update; used by "Select all". */
        onSetValues: (values: CategoricalMetadataValue[]) => void;
        onClear: () => void;
        onRemove?: () => void;
        layout?: 'dropdown' | 'list';
        /** List layout only: whether the values show under the field name. */
        expanded?: boolean;
        /** List layout only: lets the user show or hide the values. */
        onToggleExpanded?: () => void;
        /** List layout only: shows a checkbox that is checked when the field has an active filter. */
        checked?: boolean;
        /** List layout only: clears the field filter when the checkbox is unchecked. */
        onClearField?: () => void;
    }

    const {
        fieldLabel = 'Values',
        buckets,
        selectedValues,
        loading = false,
        updating = false,
        error,
        onRetry,
        onToggle,
        onSetValues,
        onClear,
        onRemove,
        layout = 'dropdown',
        expanded = true,
        onToggleExpanded,
        checked,
        onClearField
    }: Props = $props();

    const options = $derived(buildOptions(buckets, selectedValues));
    const summary = $derived(
        selectedValues.length === 0
            ? 'All values'
            : selectedValues.length === 1
              ? getOptionLabel(
                    options.find(({ bucket }) => Object.is(bucket.value, selectedValues[0]))!,
                    options,
                    buckets
                )
              : `${selectedValues.length} selected`
    );
    const status = $derived(updating ? 'Updating…' : undefined);
    // No summary until the values load, so the total in "N of M" is known.
    const headerSummary = $derived(
        buckets.length > 0 ? `${selectedValues.length} of ${buckets.length}` : undefined
    );
    const disabled = $derived(loading && buckets.length === 0 && selectedValues.length === 0);
</script>

<MetadataCategoricalFilterLayout
    {fieldLabel}
    {layout}
    {summary}
    {disabled}
    {loading}
    {updating}
    {status}
    {onRemove}
    {expanded}
    {onToggleExpanded}
    {checked}
    {headerSummary}
    {onClearField}
>
    {#snippet children()}
        <MetadataCategoricalFilterOptions
            {buckets}
            {selectedValues}
            {loading}
            {error}
            listMode={layout === 'list'}
            {onToggle}
            {onSetValues}
            {onClear}
        />
    {/snippet}
</MetadataCategoricalFilterLayout>
<MetadataCategoricalFilterStatus
    bucketCount={buckets.length}
    error={error && (buckets.length > 0 || layout === 'list') ? error : undefined}
    {onRetry}
/>
