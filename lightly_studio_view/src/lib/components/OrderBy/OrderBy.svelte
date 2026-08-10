<script lang="ts">
    import { SortDirection } from '$lib/api/lightly_studio_local';
    import { useOrderBy } from '$lib/hooks/useOrderBy/useOrderBy';
    import { useGlobalStorage, usePostHog } from '$lib/hooks';
    import { Select, type SelectItem } from '$lib/components/Select';
    import { Button } from '$lib/components';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import { ArrowDown, ArrowUp } from '@lucide/svelte';

    interface Props {
        collectionId: string;
        datasetId: string;
    }

    const { collectionId, datasetId }: Props = $props();

    const { textEmbedding } = useGlobalStorage();
    const { trackEvent } = usePostHog();
    const isSimilaritySearchActive = $derived(!!$textEmbedding);

    const {
        allSortFields,
        selectedDirection,
        selectedLabel,
        isFieldSelected,
        handleFieldClick,
        toggleDirection,
        dispose
    } = useOrderBy({ collectionId: () => collectionId, datasetId: () => datasetId });

    $effect(() => {
        return () => dispose();
    });

    const selectValue = $derived.by(() => {
        const idx = $allSortFields.findIndex((field) => $isFieldSelected(field));
        return idx >= 0 ? String(idx) : '';
    });

    const sortItems = $derived<SelectItem[]>(
        $allSortFields.map((field, i) => ({
            value: String(i),
            label: field.label,
            testId:
                field.source === 'evaluation_metric'
                    ? `sort-field-${field.evaluation_run_name}-${field.metric_name}`
                    : `sort-field-${field.value}`
        }))
    );

    const handleValueChange = (value: string) => {
        if (value === '') {
            const idx = $allSortFields.findIndex((field) => $isFieldSelected(field));
            if (idx >= 0) handleFieldClick($allSortFields[idx]);
            return;
        }
        const field = $allSortFields[Number(value)];
        if (field) handleFieldClick(field);
    };

    const directionTooltip = $derived(
        $selectedDirection === SortDirection.DESC ? 'Sort descending' : 'Sort ascending'
    );
</script>

<div class="flex items-center gap-1">
    <Tooltip content="Sort items by attribute" position="top" triggerClass="inline-flex">
        <Select
            items={sortItems}
            value={selectValue}
            triggerLabel={$selectedLabel ?? undefined}
            allowDeselect
            onValueChange={handleValueChange}
            onOpenChange={(open) => {
                if (open) trackEvent('sort_by_opened', { collection_id: collectionId });
            }}
            disabled={isSimilaritySearchActive}
            placeholder="Sort by"
            size="xs"
            variant="ghost"
            class="w-[100px] min-w-20"
            testId="sort-by-trigger"
        />
    </Tooltip>

    <Tooltip content={directionTooltip} position="top">
        <Button
            variant="ghost"
            icon={$selectedDirection === SortDirection.DESC ? ArrowDown : ArrowUp}
            ariaLabel={directionTooltip}
            buttonProps={{
                size: 'icon',
                disabled: !$selectedLabel || isSimilaritySearchActive,
                onclick: toggleDirection,
                class: 'size-auto p-0 hover:bg-transparent [&>svg]:text-foreground [&>svg]:hover:text-muted-foreground',
                'data-testid': 'sort-direction-button'
            }}
        />
    </Tooltip>
</div>
