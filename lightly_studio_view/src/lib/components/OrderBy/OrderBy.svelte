<script lang="ts">
    import { SortDirection } from '$lib/api/lightly_studio_local';
    import type { SortFieldExpr } from '$lib/api/lightly_studio_local';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import * as Popover from '$lib/components/ui/popover/index.js';
    import { Button } from '$lib/components/ui/button';
    import { ArrowDown, ArrowUp } from '@lucide/svelte';
    import { cn } from '$lib/utils/shadcn';

    type SortField = {
        source: SortFieldExpr['source'];
        value: SortFieldExpr['field_name'];
        label: string;
    };

    const SORT_FIELDS: SortField[] = [
        { source: 'image', value: 'file_name', label: 'File Name' },
        { source: 'image', value: 'file_path_abs', label: 'File Path' },
        { source: 'image', value: 'created_at', label: 'Created At' },
        { source: 'image', value: 'width', label: 'Width' },
        { source: 'image', value: 'height', label: 'Height' }
    ];

    const { imageSortBy, updateSortBy } = useImageFilters();

    const selectedField = $derived($imageSortBy?.[0]?.field_name ?? null);
    const selectedSource = $derived($imageSortBy?.[0]?.source ?? null);
    const selectedDirection = $derived($imageSortBy?.[0]?.direction ?? SortDirection.ASC);
    const selectedLabel = $derived(
        SORT_FIELDS.find((f) => f.source === selectedSource && f.value === selectedField)?.label ??
            null
    );

    let open = $state(false);

    function handleFieldClick(field: SortField) {
        if (field.value === selectedField && field.source === selectedSource) {
            updateSortBy(null);
        } else {
            updateSortBy([
                { source: field.source, field_name: field.value, direction: selectedDirection }
            ]);
        }
        open = false;
    }

    function toggleDirection() {
        if (!selectedField || !selectedSource) return;
        const next =
            selectedDirection === SortDirection.ASC ? SortDirection.DESC : SortDirection.ASC;
        updateSortBy([{ source: selectedSource, field_name: selectedField, direction: next }]);
    }
</script>

<div class="flex items-center gap-1">
    <Popover.Root bind:open>
        <Popover.Trigger>
            <Button
                variant="outline"
                size="sm"
                class="h-8 min-w-20 gap-1 text-xs font-normal"
                data-testid="sort-by-trigger"
            >
                {selectedLabel ?? 'Sort by'}
            </Button>
        </Popover.Trigger>
        <Popover.Content class="w-40 p-1" align="start">
            {#each SORT_FIELDS as field}
                <button
                    class={cn(
                        'flex w-full items-center rounded-sm px-2 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground',
                        field.value === selectedField &&
                            field.source === selectedSource &&
                            'bg-accent text-accent-foreground'
                    )}
                    onclick={() => handleFieldClick(field)}
                    data-testid="sort-field-{field.value}"
                >
                    {field.label}
                </button>
            {/each}
        </Popover.Content>
    </Popover.Root>

    <Button
        variant={selectedField ? 'secondary' : 'ghost'}
        size="icon"
        class="h-8 w-8"
        disabled={!selectedField}
        onclick={toggleDirection}
        data-testid="sort-direction-button"
    >
        {#if selectedDirection === SortDirection.DESC}
            <ArrowDown class="size-4" />
        {:else}
            <ArrowUp class="size-4" />
        {/if}
    </Button>
</div>
