<script lang="ts">
    import { ChevronsUpDown } from '@lucide/svelte';
    import * as Popover from '$lib/components/ui/popover';
    import { Button } from '$lib/components/ui/button';
    import { Checkbox } from '$lib/components/ui/checkbox';
    import { Input } from '$lib/components/ui/input';
    import type { CategoricalMetadataBucket } from '$lib/hooks/useCategoricalMetadataDistribution/types';
    import type { CategoricalMetadataValue } from '$lib/services/types';

    interface Props {
        buckets: CategoricalMetadataBucket[];
        selectedValues: CategoricalMetadataValue[];
        loading?: boolean;
        onToggle: (value: CategoricalMetadataValue) => void;
        onClear: () => void;
    }

    const { buckets, selectedValues, loading = false, onToggle, onClear }: Props = $props();
    let search = $state('');
    type SelectableBucket = Exclude<CategoricalMetadataBucket, { kind: 'other' }>;
    type FilterOption = { bucket: SelectableBucket; retained: boolean };

    const returnedSelectable = $derived(
        buckets.filter((bucket): bucket is SelectableBucket => bucket.kind !== 'other')
    );
    const options = $derived.by<FilterOption[]>(() => {
        const returned: FilterOption[] = returnedSelectable.map((bucket) => ({
            bucket,
            retained: false
        }));
        const retained: FilterOption[] = selectedValues
            .filter((value) => !returnedSelectable.some((bucket) => Object.is(bucket.value, value)))
            .map((value) => ({
                bucket:
                    value === null
                        ? {
                              id: JSON.stringify(['missing']),
                              kind: 'missing',
                              value: null,
                              label: 'Missing',
                              count: 0
                          }
                        : {
                              id: JSON.stringify(['retained', typeof value, value]),
                              kind: 'value',
                              value,
                              label: String(value),
                              count: 0
                          },
                retained: true
            }));
        return [...returned, ...retained];
    });
    const optionLabel = (option: FilterOption): string => {
        const hasMissing = options.some(({ bucket }) => bucket.kind === 'missing');
        const hasOtherAggregate = buckets.some((bucket) => bucket.kind === 'other');
        if (
            option.bucket.kind === 'missing' &&
            options.some(({ bucket }) => bucket.value === 'Missing')
        ) {
            return 'Missing (no value)';
        }
        if (option.bucket.kind === 'value' && option.bucket.value === 'Missing' && hasMissing) {
            return 'Missing (value)';
        }
        if (
            option.bucket.kind === 'value' &&
            option.bucket.value === 'Other' &&
            hasOtherAggregate
        ) {
            return 'Other (value)';
        }
        return option.bucket.label;
    };
    const visible = $derived(
        options.filter((option) => optionLabel(option).toLowerCase().includes(search.toLowerCase()))
    );
    const showSearch = $derived(buckets.filter((bucket) => bucket.kind === 'value').length > 5);
    const summary = $derived(
        selectedValues.length === 0
            ? 'All values'
            : selectedValues.length === 1
              ? optionLabel(
                    options.find(({ bucket }) => Object.is(bucket.value, selectedValues[0]))!
                )
              : `${selectedValues.length} selected`
    );
    const isSelected = (value: CategoricalMetadataValue) =>
        selectedValues.some((selected) => Object.is(selected, value));
    const checkboxLabel = (option: FilterOption) =>
        `${
            option.bucket.kind === 'missing'
                ? 'Select missing metadata'
                : `Select value ${optionLabel(option)}`
        }, ${option.retained ? 'count unavailable' : `${option.bucket.count} samples`}`;
</script>

<div class="mt-2 flex items-center gap-2" data-testid="metadata-categorical-filter">
    <span class="w-[100px] shrink-0 text-xs text-muted-foreground">Values</span>
    <Popover.Root onOpenChange={(open) => !open && (search = '')}>
        <Popover.Trigger>
            {#snippet child({ props })}
                <Button
                    {...props}
                    variant="outline"
                    size="sm"
                    class="min-w-0 flex-1 justify-between max-sm:min-h-11"
                    disabled={loading && buckets.length === 0}
                    aria-label="Select metadata values"
                    data-testid="metadata-categorical-filter-trigger"
                >
                    <span class="truncate">{loading ? 'Loading…' : summary}</span>
                    <ChevronsUpDown class="opacity-50" />
                </Button>
            {/snippet}
        </Popover.Trigger>
        <Popover.Content class="w-[min(320px,calc(100vw-2rem))] p-2" align="end">
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
                            >{option.retained ? 'Not in top 20' : option.bucket.count}</span
                        >
                    </label>
                {/each}
                {#if visible.length === 0}<p class="p-2 text-sm text-muted-foreground">
                        No values found.
                    </p>{/if}
                {#if buckets.some((bucket) => bucket.kind === 'other')}
                    <p class="p-2 text-xs text-muted-foreground">
                        Other is an aggregate and cannot be selected.
                    </p>
                {/if}
            </div>
            {#if selectedValues.length > 0}
                <Button
                    variant="ghost"
                    size="sm"
                    class="mt-2 w-full max-sm:min-h-11"
                    onclick={onClear}>Clear</Button
                >
            {/if}
        </Popover.Content>
    </Popover.Root>
</div>
