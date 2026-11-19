<script lang="ts">
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { FilterList } from '$lib/components/FilterList';
    import type { Annotation } from '$lib/types';
    import { formatInteger, resolveEffectiveColorBySource } from '$lib/utils';
    import { type Readable } from 'svelte/store';
    import AnnotationColorLegend from '../AnnotationColorLegend/AnnotationColorLegend.svelte';
    import { useAnnotationCollectionsFilter } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';
    import { useSettings } from '$lib/hooks/useSettings';
    import { useAnnotationClassVisibility, useUnannotatedSamplesFilter } from '$lib/hooks';
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
    const { includeUnannotatedSamples, setIncludeUnannotatedSamples } =
        useUnannotatedSamplesFilter();

    // Class names are free text, so the item IDs need a namespace to stay apart from the row.
    const NO_ANNOTATIONS_ITEM_ID = 'no-annotations';
    const CLASS_ITEM_ID_PREFIX = 'class:';
    const toClassName = (itemId: string) => itemId.slice(CLASS_ITEM_ID_PREFIX.length);

    const toggleItem = (itemId: string) => {
        if (itemId === NO_ANNOTATIONS_ITEM_ID) {
            setIncludeUnannotatedSamples(!$includeUnannotatedSamples);
            return;
        }
        onToggleAnnotationFilter(toClassName(itemId));
    };

    const changeSelection = (itemIds: string[]) => {
        setIncludeUnannotatedSamples(itemIds.includes(NO_ANNOTATIONS_ITEM_ID));
        onSelectionChange(
            itemIds.filter((itemId) => itemId !== NO_ANNOTATIONS_ITEM_ID).map(toClassName)
        );
    };

    const showClassColorLegend = $derived(
        !resolveEffectiveColorBySource({
            multipleSourcesVisible: $multipleSourcesVisible,
            enforceColoringByClass: $enforceColoringByClassStore
        })
    );

    const classItems = $derived(
        $annotationFilterRows.map((row) => ({
            id: row.isNoAnnotationsRow
                ? NO_ANNOTATIONS_ITEM_ID
                : `${CLASS_ITEM_ID_PREFIX}${row.label_name}`,
            label: row.label_name,
            selected: row.selected,
            count:
                row.current_count === undefined
                    ? undefined
                    : `${formatInteger(row.current_count)} of ${formatInteger(row.total_count)}`
        }))
    );
    const selectedById = $derived(new Map(classItems.map((item) => [item.id, item.selected])));
</script>

<Segment title="Annotation Classes">
    <div class="space-y-2">
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
                onToggle={toggleItem}
                onSelectionChange={changeSelection}
                testId="labels-menu"
                searchPlaceholder="Search classes…"
                paged={false}
            >
                {#snippet leading(item)}
                    {#if showClassColorLegend && item.id === NO_ANNOTATIONS_ITEM_ID}
                        <!-- Takes the width of the color legend, so the names line up. -->
                        <span class="size-3 shrink-0" aria-hidden="true"></span>
                    {:else if showClassColorLegend}
                        <AnnotationColorLegend
                            labelName={item.label}
                            className="h-3 w-3"
                            selected={selectedById.get(item.id) ?? false}
                            testId="label-color-legend"
                        />
                    {/if}
                {/snippet}
                {#snippet trailing(item)}
                    {#if showVisibilityToggle && item.id === NO_ANNOTATIONS_ITEM_ID}
                        <!-- Takes the width of the visibility toggle, so the counts line up. -->
                        <span class="size-4 shrink-0" aria-hidden="true"></span>
                    {:else if showVisibilityToggle}
                        <LabelVisibilityToggle
                            isHidden={$hiddenClassNamesStore.includes(item.label)}
                            labelName={item.label}
                            {toggleClassVisibility}
                        />
                    {/if}
                {/snippet}
            </FilterList>
        {/if}
    </div>
</Segment>
