<script lang="ts">
    import { EvaluationMatchSortField, SortDirection } from '$lib/api/lightly_studio_local';
    import { Select, type SelectItem } from '$lib/components/Select';
    import { Button } from '$lib/components/ui/button';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import {
        MATCH_SORT_FIELD_LABELS,
        MATCH_SORT_FIELD_ORDER,
        useMatchSort
    } from '$lib/hooks/useMatchSort/useMatchSort';
    import { ArrowDown, ArrowUp } from '@lucide/svelte';

    const { sortField, sortDirection, setField, toggleDirection } = useMatchSort();

    const sortItems: SelectItem[] = MATCH_SORT_FIELD_ORDER.map((field) => ({
        value: field,
        label: MATCH_SORT_FIELD_LABELS[field],
        testId: `sort-field-${field}`
    }));

    const handleValueChange = (value: string) => {
        if (value) {
            setField(value as EvaluationMatchSortField);
        }
    };

    const directionTooltip = $derived(
        $sortDirection === SortDirection.DESC ? 'Sort descending' : 'Sort ascending'
    );
</script>

<div class="flex items-center gap-1">
    <Tooltip content="Sort items by attribute" position="top" triggerClass="inline-flex">
        <Select
            items={sortItems}
            value={$sortField}
            onValueChange={handleValueChange}
            placeholder="Sort by"
            size="xs"
            variant="ghost"
            class="min-w-20"
            testId="match-sort-trigger"
        />
    </Tooltip>

    <Tooltip content={directionTooltip} position="top">
        <Button
            variant="ghost"
            size="icon"
            onclick={toggleDirection}
            class="size-auto p-0 hover:bg-transparent [&>svg]:text-foreground [&>svg]:hover:text-muted-foreground"
            data-testid="match-sort-direction-button"
            aria-label={directionTooltip}
        >
            {#if $sortDirection === SortDirection.DESC}
                <ArrowDown class="size-4" />
            {:else}
                <ArrowUp class="size-4" />
            {/if}
        </Button>
    </Tooltip>
</div>
