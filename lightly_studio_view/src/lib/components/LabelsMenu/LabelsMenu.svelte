<script lang="ts">
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { FilterList } from '$lib/components/FilterList';
    import type { Annotation } from '$lib/types';
    import { formatInteger, resolveEffectiveColorBySource } from '$lib/utils';
    import { type Readable } from 'svelte/store';
    import AnnotationColorLegend from '../AnnotationColorLegend/AnnotationColorLegend.svelte';
    import { useAnnotationCollectionsFilter } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';
    import { useSettings } from '$lib/hooks/useSettings';
    import { useAnnotationClassVisibility } from '$lib/hooks';
    import LabelVisibilityToggle from './LabelVisibilityToggle/LabelVisibilityToggle.svelte';

    interface Props {
        /** A list of filtered annotations */
        annotationFilterRows: Readable<Annotation[]>;
        /** Called when the user toggles an annotation class filter checkbox */
        onToggleAnnotationFilter: (label: string) => void;
        /** Called with the selected class names after "Select all" or "Clear" */
        onSelectionChange: (labels: string[]) => void;
        /** Whether to show the label visibility toggle */
        showVisibilityToggle?: boolean;
    }

    let {
        annotationFilterRows,
        onToggleAnnotationFilter,
        onSelectionChange,
        showVisibilityToggle = false
    }: Props = $props();

    const { multipleSourcesVisible, allSourcesHidden } = useAnnotationCollectionsFilter();
    const { enforceColoringByClassStore } = useSettings();
    const { hiddenClassNamesStore, toggleClassVisibility } = useAnnotationClassVisibility();

    const showClassColorLegend = $derived(
        !resolveEffectiveColorBySource({
            multipleSourcesVisible: $multipleSourcesVisible,
            enforceColoringByClass: $enforceColoringByClassStore
        })
    );

    const classItems = $derived(
        $annotationFilterRows.map(({ label_name, current_count, total_count, selected }) => ({
            id: label_name,
            label: label_name,
            selected,
            count:
                current_count === undefined
                    ? undefined
                    : `${formatInteger(current_count)} of ${formatInteger(total_count)}`
        }))
    );
    const selectedById = $derived(new Map(classItems.map((item) => [item.id, item.selected])));
</script>

<Segment title="Annotation Classes">
    <div class="width-full min-w-0 space-y-2">
        {#if $allSourcesHidden}
            <!-- The rows are empty here because every source is unchecked, not because the
                 dataset has no annotations. Say so, otherwise the message below sends the user
                 off to add annotations they already have. -->
            <p class="text-sm text-diffuse-foreground" data-testid="labels-menu-no-sources">
                No annotation sources selected. Select one to see its annotation classes.
            </p>
        {:else if $annotationFilterRows.length === 0}
            <p class="text-sm text-diffuse-foreground">
                No annotations yet.
                <a
                    href="https://docs.lightly.ai/studio/workflows/annotations"
                    target="_blank"
                    rel="noreferrer"
                    class="text-primary underline-offset-4 hover:underline"
                >
                    Label samples directly in LightlyStudio or add annotations from code.
                </a>
            </p>
        {:else}
            <FilterList
                items={classItems}
                onToggle={onToggleAnnotationFilter}
                {onSelectionChange}
                testId="labels-menu"
                searchPlaceholder="Search classes…"
            >
                {#snippet leading(item)}
                    {#if showClassColorLegend}
                        <AnnotationColorLegend
                            labelName={item.label}
                            className="h-3 w-3"
                            selected={selectedById.get(item.id) ?? false}
                            testId="label-color-legend"
                        />
                    {/if}
                {/snippet}
                {#snippet trailing(item)}
                    {#if showVisibilityToggle}
                        <LabelVisibilityToggle
                            isHidden={$hiddenClassNamesStore.includes(item.id)}
                            labelName={item.label}
                            {toggleClassVisibility}
                        />
                    {/if}
                {/snippet}
            </FilterList>
        {/if}
    </div>
</Segment>
