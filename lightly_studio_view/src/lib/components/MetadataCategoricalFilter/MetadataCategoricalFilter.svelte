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
        onClear: () => void;
        onRemove?: () => void;
        layout?: 'dropdown' | 'list';
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
        onClear,
        onRemove,
        layout = 'dropdown'
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
    const disabled = $derived(loading && buckets.length === 0 && selectedValues.length === 0);
    let search = $state('');
</script>

<MetadataCategoricalFilterLayout
    {fieldLabel}
    {layout}
    {summary}
    {disabled}
    {loading}
    {updating}
    {onRemove}
    onOpenChange={(open) => !open && (search = '')}
>
    {#snippet children()}
        <MetadataCategoricalFilterOptions
            {buckets}
            {selectedValues}
            {loading}
            {error}
            listMode={layout === 'list'}
            {search}
            onSearchChange={(value) => (search = value)}
            {onToggle}
            {onClear}
        />
    {/snippet}
</MetadataCategoricalFilterLayout>
<MetadataCategoricalFilterStatus
    bucketCount={buckets.length}
    error={error && (buckets.length > 0 || layout === 'list') ? error : undefined}
    {onRetry}
/>
