<script lang="ts">
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { Checkbox } from '$lib/components/ui/checkbox/index.js';
    import { Label } from '$lib/components/ui/label/index.js';
    import type { Annotation } from '$lib/types';
    import { formatInteger } from '$lib/utils';
    import { type Writable } from 'svelte/store';
    import AnnotationColorLegend from '../AnnotationColorLegend/AnnotationColorLegend.svelte';

    let {
        annotationFilters,
        onToggleAnnotationFilter
    }: {
        annotationFilters: Writable<Annotation[]>;
        onToggleAnnotationFilter: (label: string) => void;
    } = $props();
</script>

<Segment title="Labels">
    <div class="width-full space-y-2 overflow-hidden">
        {#each $annotationFilters as { label_name, current_count, total_count, selected } (label_name)}
            <div class="width-full flex items-center space-x-2" title={label_name}>
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
                    <AnnotationColorLegend labelName={label_name} className="h-3 w-3" {selected} />
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
                            >{formatInteger(current_count)} of {formatInteger(total_count)}</span
                        >
                    {/if}
                </Label>
            </div>
        {/each}
    </div>
</Segment>
