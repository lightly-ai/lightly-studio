<script lang="ts">
    import type { CuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/domain';
    import { createCuboidTooltip } from './cuboidTooltip';

    /** Displays the hover-only HTML overlay for one cuboid annotation. */
    interface Props {
        /** Cuboid whose metadata is shown. */
        annotation: CuboidAnnotation;
        /** Resolved human-readable annotation class name. */
        annotationClassName: string;
        /** Human-readable annotation source name, when available. */
        annotationSourceName?: string;
    }

    let { annotation, annotationClassName, annotationSourceName }: Props = $props();

    const tooltip = $derived(
        createCuboidTooltip({ annotation, annotationClassName, annotationSourceName })
    );
</script>

<div
    class="min-w-64 rounded-lg border border-border/80 bg-popover px-3 py-2.5 text-xs text-popover-foreground shadow-lg"
    data-testid="cuboid-tooltip"
>
    <p class="border-b border-border/70 pb-2 text-sm font-semibold">
        {tooltip.annotationClassName}
    </p>
    <dl class="space-y-2 pt-2">
        <div class="space-y-0.5">
            <dt class="font-medium text-muted-foreground">Location</dt>
            <dd>{tooltip.location}</dd>
        </div>
        <div class="space-y-0.5">
            <dt class="font-medium text-muted-foreground">Dimensions</dt>
            <dd>{tooltip.dimensions}</dd>
        </div>
        <div class="space-y-0.5">
            <dt class="font-medium text-muted-foreground">Rotation (rx / ry / rz)</dt>
            <dd>{tooltip.rotation}</dd>
        </div>
        {#if tooltip.annotationSourceName}
            <div class="space-y-0.5">
                <dt class="font-medium text-muted-foreground">Annotation source</dt>
                <dd>{tooltip.annotationSourceName}</dd>
            </div>
        {/if}
        {#if tooltip.trackNumber !== null}
            <div class="space-y-0.5">
                <dt class="font-medium text-muted-foreground">Track number</dt>
                <dd>{tooltip.trackNumber}</dd>
            </div>
        {/if}
    </dl>
</div>
