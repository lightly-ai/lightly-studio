<script lang="ts">
    import { SortDirection } from '$lib/api/lightly_studio_local';
    import { useOrderBy } from '$lib/hooks/useOrderBy/useOrderBy';
    import * as Popover from '$lib/components/ui/popover/index.js';
    import { Button } from '$lib/components/ui/button';
    import { ArrowDown, ArrowUp } from '@lucide/svelte';
    import { cn } from '$lib/utils/shadcn';

    interface Props {
        datasetId: string;
    }

    const { datasetId }: Props = $props();

    const {
        allSortFields,
        selectedDirection,
        selectedLabel,
        isFieldSelected,
        handleFieldClick,
        toggleDirection
    } = $derived(useOrderBy({ datasetId }));

    let open = $state(false);
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
                {$selectedLabel ?? 'Sort by'}
            </Button>
        </Popover.Trigger>
        <Popover.Content class="min-w-20 p-1" align="start">
            <div class="max-h-64 overflow-y-auto dark:[color-scheme:dark]">
                {#each $allSortFields as field}
                    <button
                        class={cn(
                            'flex w-full items-center rounded-sm px-2 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground',
                            $isFieldSelected(field) && 'bg-accent text-accent-foreground'
                        )}
                        onclick={() => {
                            handleFieldClick(field);
                            open = false;
                        }}
                        data-testid={field.source === 'evaluation_metric'
                            ? `sort-field-${field.evaluation_run_name}-${field.metric_name}`
                            : `sort-field-${field.value}`}
                    >
                        {field.label}
                    </button>
                {/each}
            </div>
        </Popover.Content>
    </Popover.Root>

    <Button
        variant={$selectedLabel ? 'secondary' : 'ghost'}
        size="icon"
        class="h-8 w-8"
        disabled={!$selectedLabel}
        onclick={toggleDirection}
        data-testid="sort-direction-button"
        aria-label={$selectedDirection === SortDirection.DESC
            ? 'Sort descending'
            : 'Sort ascending'}
    >
        {#if $selectedDirection === SortDirection.DESC}
            <ArrowDown class="size-4" />
        {:else}
            <ArrowUp class="size-4" />
        {/if}
    </Button>
</div>
