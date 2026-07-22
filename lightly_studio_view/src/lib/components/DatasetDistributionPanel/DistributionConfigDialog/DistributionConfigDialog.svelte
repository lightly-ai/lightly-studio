<script lang="ts">
    import { ClassSetConfigDialog } from '$lib/components/ClassSetConfig';
    import { Select, type SelectItem } from '$lib/components/Select';
    import {
        DISTRIBUTION_SORT_LABELS,
        type DistributionConfig,
        type DistributionSortOption
    } from '../types';
    import { AnnotationCountMode } from '$lib/api/lightly_studio_local/types.gen';

    interface Props {
        /** Two-way bound flag controlling dialog visibility. */
        open: boolean;
        /** Every class label available, used to bound top-N and populate the manual selector. */
        allClasses: string[];
        /** Stable values and display labels for manual selection. */
        items?: SelectItem[];
        /** The currently applied config. */
        config: DistributionConfig;
        /** Whether to show the Count by selector (default true). */
        showCountMode?: boolean;
        /** Singular/plural labels used by categorical distributions. */
        itemNounPlural?: string;
        /** Labels for the available sort modes. */
        sortLabels?: Record<DistributionSortOption, string>;
        /** Invoked with the new config when the user clicks Apply. */
        onApply: (config: DistributionConfig) => void;
    }

    let {
        open = $bindable(),
        allClasses,
        items,
        config,
        showCountMode = true,
        itemNounPlural = 'classes',
        sortLabels = DISTRIBUTION_SORT_LABELS,
        onApply
    }: Props = $props();

    const sortItems = $derived<SelectItem[]>(
        (Object.keys(sortLabels) as DistributionSortOption[]).map((value) => ({
            value,
            label: sortLabels[value]
        }))
    );

    const countModeItems: SelectItem[] = [
        { value: AnnotationCountMode.OBJECTS, label: 'Objects' },
        { value: AnnotationCountMode.SAMPLES, label: 'Samples' }
    ];

    let draftCountMode = $state<AnnotationCountMode>(
        config.countMode ?? AnnotationCountMode.OBJECTS
    );
    $effect(() => {
        if (open) draftCountMode = config.countMode ?? AnnotationCountMode.OBJECTS;
    });
</script>

<ClassSetConfigDialog
    bind:open
    {allClasses}
    {items}
    selection={config}
    {sortItems}
    description="Choose which {itemNounPlural} the distribution chart shows."
    testIdPrefix="distribution-config"
    showAllButton
    {itemNounPlural}
    onApply={(selection) =>
        onApply({ ...config, ...selection, countMode: draftCountMode } as DistributionConfig)}
>
    {#snippet extraSections()}
        {#if showCountMode}
            <label class="flex items-center justify-between gap-2 text-sm">
                Count by
                <Select
                    items={countModeItems}
                    value={draftCountMode}
                    size="xs"
                    class="w-44"
                    testId="distribution-config-count-mode"
                    onValueChange={(value) => (draftCountMode = value as AnnotationCountMode)}
                />
            </label>
        {/if}
    {/snippet}
</ClassSetConfigDialog>
