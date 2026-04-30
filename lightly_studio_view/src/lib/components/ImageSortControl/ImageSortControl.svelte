<script lang="ts">
    import { createQuery } from '@tanstack/svelte-query';
    import { ArrowDown, ArrowUp, ChevronDown } from '@lucide/svelte';
    import { getImageSortFieldsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
    import type { SortFieldExpr, SortFieldSpec } from '$lib/api/lightly_studio_local';
    import { Button } from '$lib/components/ui/button';
    import * as Popover from '$lib/components/ui/popover';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import { cn } from '$lib/utils/shadcn';

    interface Props {
        datasetId: string;
    }

    const { datasetId }: Props = $props();
    const { imageSort, updateImageSort, removeImageSort, clearImageSort } = useImageFilters();
    const sortFields = createQuery(
        getImageSortFieldsOptions({
            path: {
                dataset_id: datasetId
            }
        })
    );

    let open = $state(false);

    const selectedLabels = $derived(
        $imageSort
            .map((sort) => $sortFields.data?.find((field) => field.id === sort.id)?.label)
            .filter(Boolean)
    );

    const getNextDirection = (fieldId: string): SortFieldExpr['direction'] => {
        const existing = $imageSort.find((s) => s.id === fieldId);
        if (!existing) {
            return 'desc';
        }
        return existing.direction === 'asc' ? 'desc' : 'asc';
    };

    const handleSelectField = (field: SortFieldSpec) => {
        const existing = $imageSort.find((s) => s.id === field.id);

        if (existing) {
            removeImageSort(field.id);
            return;
        }

        updateImageSort(field, getNextDirection(field.id));
    };

    const isFieldSelected = (fieldId: string): boolean => {
        return $imageSort.some((s) => s.id === fieldId);
    };

    const handleDirectionChange = (field: SortFieldSpec) => {
        updateImageSort(field, getNextDirection(field.id));
    };
</script>

<Popover.Root bind:open>
    <Popover.Trigger>
        {#snippet child({ props })}
            <Button
                {...props}
                variant="outline"
                class="min-w-32 justify-between border-border-hard bg-background px-3 text-muted-foreground hover:text-foreground"
                disabled={$sortFields.isLoading || $sortFields.isError}
                data-testid="image-sort-trigger"
            >
                <span class="truncate"
                    >{$imageSort.length > 0 ? selectedLabels.join(', ') : 'Sort by'}</span
                >
                <span class="flex items-center gap-1">
                    {#if $imageSort.length > 0}
                        <span class="text-xs opacity-70">+{$imageSort.length}</span>
                    {/if}
                    <ChevronDown class="size-4 opacity-70" />
                </span>
            </Button>
        {/snippet}
    </Popover.Trigger>

    <Popover.Content class="w-60 p-1" align="end">
        <div class="flex max-h-80 flex-col overflow-y-auto">
            {#if $imageSort.length > 0}
                <button
                    type="button"
                    class="flex h-9 items-center px-3 text-left text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                    onclick={() => {
                        clearImageSort();
                        open = false;
                    }}
                >
                    Clear all
                </button>
            {/if}
            {#each $sortFields.data ?? [] as field (field.id)}
                {@const isSelected = isFieldSelected(field.id)}
                {@const sort = $imageSort.find((s) => s.id === field.id)}
                {@const direction = sort?.direction ?? 'desc'}
                <div
                    class={cn(
                        'flex h-9 items-center justify-between gap-3 px-3 text-left text-sm hover:bg-accent hover:text-accent-foreground',
                        isSelected ? 'text-foreground' : 'text-muted-foreground'
                    )}
                    data-testid={`image-sort-field-${field.id}`}
                >
                    <button
                        type="button"
                        class="min-w-0 flex-1 text-left"
                        onclick={() => handleSelectField(field)}
                    >
                        <span class="block truncate">{field.label}</span>
                    </button>

                    <button
                        type="button"
                        class="shrink-0"
                        onclick={(e) => {
                            e.stopPropagation();
                            handleDirectionChange(field);
                        }}
                        aria-label={`Change sort direction for ${field.label}`}
                    >
                        {#if direction === 'asc'}
                            <ArrowUp class="size-4" />
                        {:else}
                            <ArrowDown class="size-4" />
                        {/if}
                    </button>
                </div>
            {/each}
        </div>
    </Popover.Content>
</Popover.Root>
