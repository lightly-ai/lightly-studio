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
    import { Eye, EyeOff } from '@lucide/svelte';
    import { Tooltip } from '$lib/components/ui/tooltip';

    const { selectedCollectionIds } = useAnnotationCollectionsFilter();
    const { enforceColoringByClassStore } = useSettings();
    const { hiddenClassNamesStore, toggleClassVisibility } = useAnnotationClassVisibility();

    const showClassColorLegend = $derived(
        !resolveEffectiveColorBySource({
            multipleSourcesVisible: $selectedCollectionIds.length > 1,
            enforceColoringByClass: $enforceColoringByClassStore
        })
    );

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
                        {#if isHidden}
                            <Tooltip content="Show annotation class">
                                <button
                                    type="button"
                                    aria-label="Show annotation class {label_name}"
                                    data-testid="label-visibility-toggle"
                                    class="flex shrink-0 items-center"
                                    onclick={() => toggleClassVisibility(label_name)}
                                >
                                    <EyeOff class="size-4 text-muted-foreground" />
                                </button>
                            </Tooltip>
                        {:else}
                            <Tooltip content="Hide annotation class">
                                <button
                                    type="button"
                                    aria-label="Hide annotation class {label_name}"
                                    data-testid="label-visibility-toggle"
                                    class="flex shrink-0 items-center opacity-0 group-hover:opacity-100"
                                    onclick={() => toggleClassVisibility(label_name)}
                                >
                                    <Eye class="size-4" />
                                </button>
                            </Tooltip>
                        {/if}
                    {/if}
                </div>
            {/each}
        {/if}
    </div>
</Segment>
