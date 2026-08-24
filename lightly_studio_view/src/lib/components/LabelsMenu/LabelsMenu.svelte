<script lang="ts">
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { getSegmentDensity, getSegmentRowStyles } from '$lib/components/Segment/segmentDensity';
    import { Checkbox } from '$lib/components/ui/checkbox/index.js';
    import { Input } from '$lib/components/ui/input/index.js';
    import { Label } from '$lib/components/ui/label/index.js';
    import type { Annotation } from '$lib/types';
    import { cn, formatInteger, getColorByLabel, resolveEffectiveColorBySource } from '$lib/utils';
    import { Search } from '@lucide/svelte';
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
        /** Whether to show the label visibility toggle */
        showVisibilityToggle?: boolean;
    }

    let {
        annotationFilterRows,
        onToggleAnnotationFilter,
        showVisibilityToggle = false
    }: Props = $props();

    const { multipleSourcesVisible, allSourcesHidden } = useAnnotationCollectionsFilter();
    const { enforceColoringByClassStore } = useSettings();
    const { hiddenClassNamesStore, toggleClassVisibility } = useAnnotationClassVisibility();

    const rowStyles = getSegmentRowStyles();
    // A dataset can carry ~70 classes; the search only earns its place in the sidebar, where
    // the whole list has to fit in a 264px rail.
    const showSearch = getSegmentDensity() === 'compact';

    let search = $state('');
    const normalizedSearch = $derived(search.trim().toLowerCase());
    const visibleRows = $derived(
        normalizedSearch
            ? $annotationFilterRows.filter((row) =>
                  row.label_name.toLowerCase().includes(normalizedSearch)
              )
            : $annotationFilterRows
    );

    const showClassColorLegend = $derived(
        !resolveEffectiveColorBySource({
            multipleSourcesVisible: $multipleSourcesVisible,
            enforceColoringByClass: $enforceColoringByClassStore
        })
    );

    // Paints the class color onto the checkbox, so a single control carries both the
    // filter state and the class identity — no separate swatch. `twMerge` keeps these
    // last, overriding the neutral defaults from `rowStyles.checkbox` and the primitive.
    const classColorCheckbox =
        'data-[state=unchecked]:border-[color:var(--class-color)] ' +
        'data-[state=unchecked]:bg-[color:var(--class-fill)] ' +
        'data-[state=checked]:border-[color:var(--class-color)] ' +
        'data-[state=checked]:bg-[color:var(--class-color)] ' +
        'data-[state=checked]:text-[color:var(--class-check)]';

    // The class color at full alpha for the border, a faint wash for the unchecked fill,
    // and a legible check-mark color chosen by luminance (see `readableCheckColor`).
    function classColorVars(labelName: string): string {
        return (
            `--class-color: ${getColorByLabel(labelName, 1).color};` +
            `--class-fill: ${getColorByLabel(labelName, 0.22).color};` +
            `--class-check: ${readableCheckColor(labelName)};`
        );
    }

    // `getColorByLabel`'s own contrast color is a plain channel inversion, which is
    // near-invisible on the palette's light hues. Pick black or white by luminance so
    // the check mark stays readable on every class color.
    function readableCheckColor(labelName: string): string {
        const channels = getColorByLabel(labelName, 1).color.match(/\d+/g);
        if (!channels) return '#ffffff';
        const [r, g, b] = channels.map(Number);
        // Rec. 601 luma — enough to pick a legible check color.
        const luma = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
        return luma > 0.6 ? '#000000' : '#ffffff';
    }
</script>

<Segment title="Annotation Classes" count={$annotationFilterRows.length || undefined}>
    <div class="width-full space-y-1 overflow-hidden">
        {#if $allSourcesHidden}
            <!-- The rows are empty here because every source is unchecked, not because the
                 dataset has no annotations. Say so, otherwise the message below sends the user
                 off to import annotations they already have. -->
            <p class="text-sm text-diffuse-foreground" data-testid="labels-menu-no-sources">
                No annotation sources selected. Select one to see its annotation classes.
            </p>
        {:else if $annotationFilterRows.length === 0}
            <p class="text-sm text-diffuse-foreground">
                No annotations yet.
                <a
                    href="https://docs.lightly.ai/studio/concepts_and_tools/annotations"
                    target="_blank"
                    rel="noreferrer"
                    class="text-primary underline-offset-4 hover:underline"
                >
                    Label samples directly in LightlyStudio or import annotations from code.
                </a>
            </p>
        {:else}
            {#if showSearch}
                <div class="relative mb-1.5 pl-[22px] pr-2">
                    <Search
                        class="pointer-events-none absolute left-[31px] top-1/2 size-3 -translate-y-1/2 text-muted-foreground"
                    />
                    <Input
                        type="text"
                        placeholder="Filter classes"
                        bind:value={search}
                        class={cn(rowStyles.input, 'pl-[26px]')}
                        data-testid="labels-menu-search"
                    />
                </div>
            {/if}
            {#each visibleRows as { label_name, current_count, total_count, selected } (label_name)}
                {@const isHidden = $hiddenClassNamesStore.includes(label_name)}
                <div
                    class={cn('width-full group flex items-center space-x-2', rowStyles.row)}
                    title={label_name}
                >
                    <Checkbox
                        id={label_name}
                        checked={selected}
                        class={cn(rowStyles.checkbox, showClassColorLegend && classColorCheckbox)}
                        style={showClassColorLegend ? classColorVars(label_name) : undefined}
                        aria-labelledby={`${label_name}-label`}
                        onCheckedChange={() => onToggleAnnotationFilter(label_name)}
                    />

                    <Label
                        id={`${label_name}-label`}
                        for={label_name}
                        data-testid="labels-menu-item"
                        class="flex min-w-0 flex-1 cursor-pointer items-center space-x-2 text-nowrap peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                    >
                        <p
                            class={cn('flex-1 truncate text-base font-normal', rowStyles.label)}
                            data-testid="label-menu-label-name"
                        >
                            {label_name}
                        </p>
                        {#if current_count}
                            <!-- "N of M" only once a filter has actually narrowed the class;
                                 otherwise the two numbers are the same and one will do. -->
                            <span
                                class={cn('text-sm text-diffuse-foreground', rowStyles.count)}
                                data-testid="label-menu-label-count"
                                >{current_count === total_count
                                    ? formatInteger(total_count)
                                    : `${formatInteger(current_count)} of ${formatInteger(total_count)}`}</span
                            >
                        {/if}
                    </Label>

                    <div class="flex shrink-0 items-center gap-1">
                        {#if showClassColorLegend}
                            <!-- The class color now lives on the checkbox; this pencil only
                                 recolors the class, revealed on hover like the eye toggle. -->
                            <AnnotationColorLegend
                                labelName={label_name}
                                className="size-4"
                                {selected}
                                variant="edit"
                                ariaLabel={`Change color of ${label_name}`}
                                testId="label-color-legend"
                            />
                        {/if}
                        {#if showVisibilityToggle}
                            <LabelVisibilityToggle
                                {isHidden}
                                labelName={label_name}
                                {toggleClassVisibility}
                            />
                        {/if}
                    </div>
                </div>
            {/each}
        {/if}
    </div>
</Segment>
