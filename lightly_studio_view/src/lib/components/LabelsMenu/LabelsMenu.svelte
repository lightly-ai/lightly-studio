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
        /** Called with the full list of selected class names, e.g. after "Select all" */
        onSetAnnotationFilter?: (labels: string[]) => void;
        /** Whether to show the label visibility toggle */
        showVisibilityToggle?: boolean;
        /** The "No annotations" row, pinned above the classes. Omit to hide it. */
        unannotatedRow?: {
            current_count: number;
            total_count: number;
            selected: boolean;
            onToggle: () => void;
        };
    }

    let {
        annotationFilterRows,
        onToggleAnnotationFilter,
        onSetAnnotationFilter = () => {},
        showVisibilityToggle = false,
        unannotatedRow
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

    const formatCount = (current: number | undefined, total: number) =>
        current === undefined ? undefined : `${formatInteger(current)} of ${formatInteger(total)}`;

    const items = $derived(
        $annotationFilterRows.map(({ label_name, current_count, total_count, selected }) => ({
            id: label_name,
            label: label_name,
            selected: !!selected,
            count: formatCount(current_count, total_count)
        }))
    );
    const pinnedItem = $derived(
        unannotatedRow && {
            id: 'no-annotations',
            label: 'No annotations',
            selected: unannotatedRow.selected,
            count: formatCount(unannotatedRow.current_count, unannotatedRow.total_count),
            onToggle: unannotatedRow.onToggle
        }
    );
</script>

<Segment title="Annotation Classes">
    {#if $allSourcesHidden}
        <!-- The rows are empty here because every source is unchecked, not because the
             dataset has no annotations. Say so, otherwise the message below sends the user
             off to add annotations they already have. -->
        <p class="text-sm text-diffuse-foreground" data-testid="labels-menu-no-sources">
            No annotation sources selected. Select one to see its annotation classes.
        </p>
    {:else if items.length === 0}
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
            {items}
            {pinnedItem}
            onToggle={onToggleAnnotationFilter}
            onSelectionChange={onSetAnnotationFilter}
            testId="labels-menu"
            searchPlaceholder="Search classes…"
        >
            {#snippet leading(item)}
                {#if showClassColorLegend}
                    <AnnotationColorLegend
                        labelName={item.id}
                        className="h-3 w-3"
                        selected={item.selected}
                        testId="label-color-legend"
                        enableColorPicker={false}
                    />
                {/if}
            {/snippet}
            {#snippet trailing(item)}
                {#if showVisibilityToggle}
                    <LabelVisibilityToggle
                        isHidden={$hiddenClassNamesStore.includes(item.id)}
                        labelName={item.id}
                        {toggleClassVisibility}
                    />
                {/if}
            {/snippet}
        </FilterList>
    {/if}
</Segment>
