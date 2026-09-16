<script lang="ts">
    import type { AnnotationTypeCount } from '$lib/api/lightly_studio_local';
    import AnnotationTypeGlyph from '$lib/components/AnnotationTypeGlyph/AnnotationTypeGlyph.svelte';
    import {
        ANNOTATION_TYPES,
        getAnnotationTypeGlyph
    } from '$lib/components/AnnotationTypeGlyph/annotationTypeGlyph';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { getSegmentRowStyles } from '$lib/components/Segment/segmentDensity';
    import { Checkbox } from '$lib/components/ui/checkbox/index.js';
    import { Label } from '$lib/components/ui/label/index.js';
    import { useAnnotationTypeFilter } from '$lib/hooks/useAnnotationTypeFilter/useAnnotationTypeFilter';
    import { cn, formatInteger } from '$lib/utils';

    interface Props {
        /** Per-type counts from the API, in the backend's enum order. */
        counts: AnnotationTypeCount[];
    }

    const { counts }: Props = $props();

    const { selectedAnnotationTypes, toggleAnnotationType } = useAnnotationTypeFilter();

    const rowStyles = getSegmentRowStyles();

    // Rows read most-to-least common in practice, which is not the enum's declaration order.
    const orderedCounts = $derived(
        [...counts].sort(
            (a, b) =>
                ANNOTATION_TYPES.indexOf(a.annotation_type) -
                ANNOTATION_TYPES.indexOf(b.annotation_type)
        )
    );
</script>

<!-- With only one type present the filter can never narrow anything, so it is not shown. -->
{#if orderedCounts.length > 1}
    <Segment title="Annotation Types">
        <div class="w-full space-y-1">
            {#each orderedCounts as { annotation_type, current_count, total_count } (annotation_type)}
                {@const glyph = getAnnotationTypeGlyph(annotation_type)}
                {@const isSelected = $selectedAnnotationTypes.has(annotation_type)}
                <div
                    class={cn('group flex items-center gap-2', rowStyles.row)}
                    data-testid="annotation-type-row"
                >
                    <Checkbox
                        id={annotation_type}
                        checked={isSelected}
                        class={rowStyles.checkbox}
                        aria-label={glyph.label}
                        onCheckedChange={() => toggleAnnotationType(annotation_type)}
                    />
                    <Label
                        id={`${annotation_type}-label`}
                        for={annotation_type}
                        class="flex min-w-0 flex-1 cursor-pointer items-center gap-2"
                    >
                        <AnnotationTypeGlyph type={annotation_type} size={14} />
                        <span class={cn('min-w-0 flex-1 truncate', rowStyles.label)}>
                            {glyph.label}
                        </span>
                        <span class={rowStyles.count}>
                            {formatInteger(current_count)} of {formatInteger(total_count)}
                        </span>
                    </Label>
                </div>
            {/each}
        </div>
    </Segment>
{/if}
