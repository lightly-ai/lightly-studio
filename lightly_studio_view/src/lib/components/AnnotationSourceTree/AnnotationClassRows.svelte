<script lang="ts">
    import FilterListRow from '$lib/components/FilterList/FilterListRow.svelte';
    import type { FilterListItem } from '$lib/components/FilterList';
    import AnnotationColorLegend from '$lib/components/AnnotationColorLegend/AnnotationColorLegend.svelte';
    import LabelVisibilityToggle from '$lib/components/LabelsMenu/LabelVisibilityToggle/LabelVisibilityToggle.svelte';
    import { useAnnotationClassVisibility } from '$lib/hooks/useAnnotationClassVisibility/useAnnotationClassVisibility';

    interface Props {
        items: FilterListItem[];
        showClassColor: boolean;
        showVisibilityToggle: boolean;
        onToggle: (labelId: string) => void;
    }

    let { items, showClassColor, showVisibilityToggle, onToggle }: Props = $props();

    // Visibility is per class name, so hiding a class hides it under every source.
    const { hiddenClassNamesStore, toggleClassVisibility } = useAnnotationClassVisibility();
</script>

{#snippet leading(item: FilterListItem)}
    {#if showClassColor}
        <AnnotationColorLegend
            labelName={item.label}
            className="h-3 w-3"
            selected={item.selected}
            testId="label-color-legend"
            enableColorPicker={false}
        />
    {/if}
{/snippet}

{#snippet trailing(item: FilterListItem)}
    {#if showVisibilityToggle}
        <LabelVisibilityToggle
            isHidden={$hiddenClassNamesStore.includes(item.label)}
            labelName={item.label}
            {toggleClassVisibility}
        />
    {/if}
{/snippet}

{#each items as item (item.id)}
    <div class="group">
        <FilterListRow
            {item}
            checked={item.selected}
            onToggle={() => onToggle(item.id)}
            testId="annotation-class"
            {leading}
            {trailing}
        />
    </div>
{/each}
