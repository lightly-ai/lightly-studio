<script lang="ts">
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { Checkbox } from '$lib/components/ui/checkbox/index.js';
    import { Label } from '$lib/components/ui/label/index.js';
    import type { Annotation } from '$lib/types';
    import { formatInteger, resolveEffectiveColorBySource } from '$lib/utils';
    import { type Readable } from 'svelte/store';
    import AnnotationColorLegend from '../AnnotationColorLegend/AnnotationColorLegend.svelte';
    import { useAnnotationCollectionsFilter } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';
    import { useSettings } from '$lib/hooks/useSettings';
    import { useAnnotationClassVisibility } from '$lib/hooks';
    import LabelVisibilityToggle from './LabelVisibilityToggle/LabelVisibilityToggle.svelte';

    interface Props {
        annotationFilterRows: Readable<Annotation[]>;
        onToggleAnnotationFilter: (label: string) => void;
        showVisibilityToggle?: boolean;
    }

    let {
        annotationFilterRows,
        onToggleAnnotationFilter,
        showVisibilityToggle = false
    }: Props = $props();

    const { selectedCollectionIds } = useAnnotationCollectionsFilter();
    const { enforceColoringByClassStore } = useSettings();
    const { hiddenClassNamesStore, toggleClassVisibility } = useAnnotationClassVisibility();

    const showClassColorLegend = $derived(
        !resolveEffectiveColorBySource({
            multipleSourcesVisible: $selectedCollectionIds.length > 1,
            enforceColoringByClass: $enforceColoringByClassStore
        })
    );
</script>

<Segment title="Annotation Classes">
    <div class="width-full space-y-2 overflow-hidden">
        {#if $annotationFilterRows.length === 0}
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
            {#each $annotationFilterRows as { label_name, current_count, total_count, selected } (label_name)}
                {@const isHidden = $hiddenClassNamesStore.includes(label_name)}
                <div class="width-full group flex items-center space-x-2" title={label_name}>
                    <Checkbox
                        id={label_name}
                        checked={selected}
                        aria-labelledby={`${label_name}-label`}
                        onCheckedChange={() => onToggleAnnotationFilter(label_name)}
                    />

                    <Label
                        id={`${label_name}-label`}
                        for={label_name}
                        data-testid="labels-menu-item"
                        class="flex min-w-0 flex-1 cursor-pointer items-center space-x-2 text-nowrap peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                    >
                        {#if showClassColorLegend}
                            <AnnotationColorLegend
                                labelName={label_name}
                                className="h-3 w-3"
                                {selected}
                                testId="label-color-legend"
                            />
                        {/if}
                        <p
                            class="flex-1 truncate text-base font-normal"
                            data-testid="label-menu-label-name"
                        >
                            {label_name}
                        </p>
                        {#if current_count}
                            <span
                                class="text-sm text-diffuse-foreground"
                                data-testid="label-menu-label-count"
                                >{formatInteger(current_count)} of {formatInteger(
                                    total_count
                                )}</span
                            >
                        {/if}
                    </Label>

                    {#if showVisibilityToggle}
                        <LabelVisibilityToggle
                            {isHidden}
                            labelName={label_name}
                            {toggleClassVisibility}
                        />
                    {/if}
                </div>
            {/each}
        {/if}
    </div>
</Segment>
