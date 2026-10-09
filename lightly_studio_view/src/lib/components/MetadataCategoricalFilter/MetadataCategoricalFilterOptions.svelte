<script lang="ts">
    import { Checkbox } from '$lib/components/ui/checkbox';
    import { Input } from '$lib/components/ui/input';
    import { Button } from '$lib/components/ui/button';
    import type { CategoricalMetadataBucket } from '$lib/hooks/useCategoricalMetadataDistribution/types';
    import type { CategoricalMetadataValue } from '$lib/services/types';
    import { buildOptions, getCheckboxLabel, getOptionLabel } from './helpers';

    interface Props {
        buckets: CategoricalMetadataBucket[];
        selectedValues: CategoricalMetadataValue[];
        loading: boolean;
        error?: string;
        listMode: boolean;
        search: string;
        onSearchChange: (search: string) => void;
        onToggle: (value: CategoricalMetadataValue) => void;
        onClear: () => void;
    }

    const {
        buckets,
        selectedValues,
        loading,
        error,
        listMode,
        search,
        onSearchChange,
        onToggle,
        onClear
    }: Props = $props();
    const options = $derived(buildOptions(buckets, selectedValues));
    const optionLabel = (option: (typeof options)[number]) =>
        getOptionLabel(option, options, buckets);
    const showSearch = $derived(buckets.filter((bucket) => bucket.kind === 'value').length > 5);
    const hasOtherAggregate = $derived(buckets.some((bucket) => bucket.kind === 'other'));
    const visible = $derived(
        options.filter((option) => optionLabel(option).toLowerCase().includes(search.toLowerCase()))
    );
    const isSelected = (value: CategoricalMetadataValue) =>
        selectedValues.some((selected) => Object.is(selected, value));
</script>

{#if showSearch}
    <Input
        value={search}
        oninput={(event) => onSearchChange(event.currentTarget.value)}
        placeholder="Search values…"
        aria-label="Search values"
        class="max-sm:min-h-11"
    />
{/if}
<div class="mt-2 max-h-56 space-y-1 overflow-y-auto">
    {#each visible as option (option.bucket.id)}
        {@const label = optionLabel(option)}
        <label
            class="flex min-h-8 cursor-pointer items-center gap-2 rounded px-2 text-sm hover:bg-accent max-sm:min-h-11"
        >
            <Checkbox
                checked={isSelected(option.bucket.value)}
                onCheckedChange={() => onToggle(option.bucket.value)}
                aria-label={getCheckboxLabel(option, label)}
            />
            <span class="min-w-0 flex-1 truncate" title={label}>{label}</span>
            <span class="text-muted-foreground"
                >{option.retained ? 'Not in current results' : option.bucket.count}</span
            >
        </label>
    {/each}
    {#if visible.length === 0}
        <p class="p-2 text-sm text-muted-foreground">
            {listMode && error && options.length === 0
                ? 'Could not load metadata distribution.'
                : listMode && loading && options.length === 0
                  ? 'Loading…'
                  : listMode && options.length === 0
                    ? 'No values are available under the current filters.'
                    : 'No values found.'}
        </p>
    {/if}
    {#if hasOtherAggregate}
        <p class="p-2 text-xs text-muted-foreground">
            Other is an aggregate and cannot be selected.
        </p>
    {/if}
</div>
{#if selectedValues.length > 0}
    <Button variant="ghost" size="sm" class="mt-2 w-full max-sm:min-h-11" onclick={onClear}
        >Clear</Button
    >
{/if}
