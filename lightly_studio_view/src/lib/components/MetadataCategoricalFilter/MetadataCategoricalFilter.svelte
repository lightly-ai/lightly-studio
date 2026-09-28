<script lang="ts">
    import { ChevronsUpDown, X } from '@lucide/svelte';
    import * as Popover from '$lib/components/ui/popover';
    import { Button } from '$lib/components';
    import { Checkbox } from '$lib/components/ui/checkbox';
    import { Input } from '$lib/components/ui/input';
    import { Button as IconButton } from '$lib/components/ui/button';
    import type { CategoricalMetadataBucket } from '$lib/hooks/useCategoricalMetadataDistribution/types';
    import type { CategoricalMetadataValue } from '$lib/services/types';
    import { getOptionLabel, getCheckboxLabel, buildOptions, type FilterOption } from './helpers';

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
    const optionLabel = (option: FilterOption) => getOptionLabel(option, options, buckets);
    const checkboxLabel = (option: FilterOption) => getCheckboxLabel(option, optionLabel(option));
    const showSearch = $derived(buckets.filter((bucket) => bucket.kind === 'value').length > 5);
    const hasOtherAggregate = $derived(buckets.some((b) => b.kind === 'other'));
    const disabled = $derived(loading && buckets.length === 0 && selectedValues.length === 0);
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

    let search = $state('');
    const visible = $derived(
        options.filter((option) => optionLabel(option).toLowerCase().includes(search.toLowerCase()))
    );
</script>

{#snippet valueOptions()}
    {#if showSearch}
        <Input
            bind:value={search}
            placeholder="Search values…"
            aria-label="Search values"
            class="max-sm:min-h-11"
        />
    {/if}
    <div class="mt-2 max-h-56 space-y-1 overflow-y-auto">
        {#each visible as option (option.bucket.id)}
            <label
                class="flex min-h-8 cursor-pointer items-center gap-2 rounded px-2 text-sm hover:bg-accent max-sm:min-h-11"
            >
                <Checkbox
                    checked={isSelected(option.bucket.value)}
                    onCheckedChange={() => onToggle(option.bucket.value)}
                    aria-label={checkboxLabel(option)}
                />
                <span class="min-w-0 flex-1 truncate" title={optionLabel(option)}
                    >{optionLabel(option)}</span
                >
                <span class="text-muted-foreground"
                    >{option.retained ? 'Not in current results' : option.bucket.count}</span
                >
            </label>
        {/each}
        {#if visible.length === 0}
            <p class="p-2 text-sm text-muted-foreground">
                {layout === 'list' && error && options.length === 0
                    ? 'Could not load metadata distribution.'
                    : layout === 'list' && loading && options.length === 0
                      ? 'Loading…'
                      : layout === 'list' && options.length === 0
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
        <Button
            variant="ghost"
            buttonProps={{ size: 'sm', class: 'mt-2 w-full max-sm:min-h-11', onclick: onClear }}
            >Clear</Button
        >
    {/if}
{/snippet}

{#snippet errorMessage()}
    {#if error && (buckets.length > 0 || layout === 'list')}
        <div
            class="mt-1 flex items-center justify-between gap-2 text-xs text-destructive"
            role="alert"
        >
            <span>
                {buckets.length === 0
                    ? 'Could not load metadata distribution.'
                    : 'Could not update metadata distribution.'}
            </span>
            {#if onRetry}
                <Button
                    variant="ghost"
                    buttonProps={{
                        size: 'sm',
                        type: 'button',
                        class: 'shrink-0 h-8 px-2 text-xs max-sm:min-h-11',
                        onclick: onRetry
                    }}>Retry</Button
                >
            {/if}
        </div>
    {/if}
{/snippet}

{#if layout === 'list'}
    <div
        class="rounded-md border border-input bg-background"
        data-testid="metadata-categorical-filter"
    >
        <div class="flex items-center justify-between gap-2 border-b px-3 py-2">
            <h3 class="min-w-0 truncate text-sm font-medium" title={fieldLabel}>{fieldLabel}</h3>
            <div class="flex shrink-0 items-center gap-1">
                {#if updating}
                    <span class="text-xs text-muted-foreground" role="status">Updating…</span>
                {/if}
                {#if onRemove}
                    <IconButton
                        variant="ghost"
                        size="icon"
                        class="size-6"
                        aria-label={`Remove metadata field ${fieldLabel}`}
                        onclick={onRemove}
                    >
                        <X class="size-4" />
                    </IconButton>
                {/if}
            </div>
        </div>
        <div class="p-2">
            <Popover.Root onOpenChange={(open) => !open && (search = '')}>
                <Popover.Trigger>
                    {#snippet child({ props })}
                        <Button
                            variant="outline"
                            buttonProps={{
                                ...props,
                                size: 'sm',
                                class: 'h-8 w-full justify-between px-3 text-xs font-normal max-sm:min-h-11',
                                disabled,
                                'data-testid': 'metadata-categorical-filter-trigger'
                            }}
                            ariaLabel="Select metadata values"
                        >
                            <span class="truncate"
                                >{loading && buckets.length === 0 ? 'Loading…' : summary}</span
                            >
                            <ChevronsUpDown class="opacity-50" />
                        </Button>
                    {/snippet}
                </Popover.Trigger>
                <Popover.Content class="w-[min(320px,calc(100vw-2rem))] p-2" align="start">
                    {@render valueOptions()}
                </Popover.Content>
            </Popover.Root>
            {@render errorMessage()}
        </div>
    </div>
{:else}
    <div class="mt-2 flex items-center gap-2" data-testid="metadata-categorical-filter">
        <span class="w-[100px] shrink-0 truncate text-xs text-muted-foreground" title={fieldLabel}
            >{fieldLabel}</span
        >
        <Popover.Root onOpenChange={(open) => !open && (search = '')}>
            <Popover.Trigger>
                {#snippet child({ props })}
                    <Button
                        variant="outline"
                        buttonProps={{
                            ...props,
                            size: 'sm',
                            // Match the neighbouring panel selects (Select size="xs").
                            class: 'h-8 min-w-0 flex-1 justify-between px-3 text-xs font-normal max-sm:min-h-11',
                            disabled,
                            'data-testid': 'metadata-categorical-filter-trigger'
                        }}
                        ariaLabel="Select metadata values"
                    >
                        <span class="truncate"
                            >{loading && buckets.length === 0 ? 'Loading…' : summary}</span
                        >
                        <ChevronsUpDown class="opacity-50" />
                    </Button>
                {/snippet}
            </Popover.Trigger>
            <Popover.Content class="w-[min(320px,calc(100vw-2rem))] p-2" align="end">
                {@render valueOptions()}
            </Popover.Content>
        </Popover.Root>
        {#if updating}
            <span class="shrink-0 text-xs text-muted-foreground" role="status">Updating…</span>
        {/if}
        {#if onRemove}
            <IconButton
                variant="ghost"
                size="icon"
                class="size-6 shrink-0"
                aria-label={`Remove metadata field ${fieldLabel}`}
                onclick={onRemove}
            >
                <X class="size-4" />
            </IconButton>
        {/if}
    </div>
    {@render errorMessage()}
{/if}
