<script lang="ts">
    import { SortDirection } from '$lib/api/lightly_studio_local';
    import { useOrderBy } from '$lib/hooks/useOrderBy/useOrderBy';
    import { useGlobalStorage } from '$lib/hooks';
    import * as Select from '$lib/components/ui/select';
    import { Button } from '$lib/components/ui/button';
    import { ArrowDown, ArrowUp } from '@lucide/svelte';

    interface Props {
        datasetId: string;
    }

    const { datasetId }: Props = $props();

    const { textEmbedding } = useGlobalStorage();
    const isSimilaritySearchActive = $derived(!!$textEmbedding);

    const {
        allSortFields,
        selectedDirection,
        selectedLabel,
        isFieldSelected,
        handleFieldClick,
        toggleDirection,
        dispose
    } = useOrderBy({ datasetId });

    $effect(() => {
        return () => dispose();
    });

    const selectValue = $derived.by(() => {
        const idx = $allSortFields.findIndex((field) => $isFieldSelected(field));
        return idx >= 0 ? String(idx) : '';
    });

    const handleValueChange = (value: string) => {
        if (value === '') {
            const idx = $allSortFields.findIndex((field) => $isFieldSelected(field));
            if (idx >= 0) handleFieldClick($allSortFields[idx]);
            return;
        }
        const field = $allSortFields[Number(value)];
        if (field) handleFieldClick(field);
    };
</script>

<div class="flex items-center gap-1">
    <Select.Root
        type="single"
        value={selectValue}
        allowDeselect
        onValueChange={handleValueChange}
        disabled={isSimilaritySearchActive}
    >
        <Select.Trigger
            class="h-8 w-[100px] min-w-20 gap-1 px-2.5 text-xs font-normal"
            data-testid="sort-by-trigger"
        >
            <span class="truncate">{$selectedLabel ?? 'Sort by'}</span>
        </Select.Trigger>
        <Select.Content class="max-h-64">
            {#each $allSortFields as field, i}
                <Select.Item
                    value={String(i)}
                    label={field.label}
                    data-testid={field.source === 'evaluation_metric'
                        ? `sort-field-${field.evaluation_run_name}-${field.metric_name}`
                        : `sort-field-${field.value}`}
                >
                    {field.label}
                </Select.Item>
            {/each}
        </Select.Content>
    </Select.Root>

    <Button
        variant="ghost"
        size="icon"
        disabled={!$selectedLabel || isSimilaritySearchActive}
        onclick={toggleDirection}
        class="size-auto p-0 hover:bg-transparent [&>svg]:text-foreground [&>svg]:hover:text-muted-foreground"
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
