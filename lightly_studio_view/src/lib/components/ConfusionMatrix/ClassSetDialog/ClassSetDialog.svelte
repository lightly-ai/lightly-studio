<script lang="ts">
    import { ClassSetConfigDialog } from '$lib/components/ClassSetConfig';
    import type { SelectItem } from '$lib/components/Select';
    import { CLASS_SORT_LABELS, type ClassSortOption } from '../topNMatrix';
    import type { ClassSetConfig, ColorConfig } from './types';
    import ColoringControls from './ColoringControls/ColoringControls.svelte';

    interface Props {
        /** Two-way bound flag controlling dialog visibility. */
        open: boolean;
        /** Every real class label available in the underlying matrix. */
        allClasses: string[];
        /** The currently applied class-set selection. */
        config: ClassSetConfig;
        /** The currently applied coloring options. Copied into a draft each time the dialog opens. */
        color: ColorConfig;
        /** Invoked with the new config and color when the user clicks Apply. */
        onApply: (config: ClassSetConfig, color: ColorConfig) => void;
    }

    let { open = $bindable(), allClasses, config, color, onApply }: Props = $props();

    // Coloring is confusion-matrix-specific; it lives here and commits together
    // with the class selection when the shared dialog fires Apply.
    let colorDraft: ColorConfig = $state({ ...color });
    $effect(() => {
        if (open) colorDraft = { ...color };
    });

    const sortItems: SelectItem[] = (Object.keys(CLASS_SORT_LABELS) as ClassSortOption[]).map(
        (value) => ({ value, label: CLASS_SORT_LABELS[value] })
    );
</script>

<ClassSetConfigDialog
    bind:open
    {allClasses}
    selection={config}
    {sortItems}
    description="Choose which classes the confusion matrix shows."
    testIdPrefix="class-set"
    onApply={(selection) =>
        onApply({ ...config, ...selection } as ClassSetConfig, { ...colorDraft })}
>
    {#snippet extraSections()}
        <ColoringControls
            bind:intensity={colorDraft.intensity}
            bind:logScale={colorDraft.logScale}
        />
    {/snippet}
</ClassSetConfigDialog>
