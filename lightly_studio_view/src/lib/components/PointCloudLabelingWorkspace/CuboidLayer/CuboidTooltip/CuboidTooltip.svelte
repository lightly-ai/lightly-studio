<script lang="ts">
    import { HTML } from '@threlte/extras';
    import type { CuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/domain';
    import { createCuboidTooltip } from './cuboidTooltip';

    /** Displays the hover-only HTML overlay for one cuboid annotation. */
    interface Props {
        /** Cuboid whose metadata is shown. */
        annotation: CuboidAnnotation;
        /** Resolved human-readable annotation class name. */
        annotationClassName: string;
    }

    let { annotation, annotationClassName }: Props = $props();

    const tooltip = $derived(createCuboidTooltip({ annotation, annotationClassName }));
</script>

<HTML center pointerEvents="none">
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
                <dt class="font-medium text-muted-foreground">Rotation</dt>
                <dd>{tooltip.rotation}</dd>
            </div>
            <div class="space-y-0.5">
                <dt class="font-medium text-muted-foreground">Annotation source</dt>
                <dd>{tooltip.annotationSourceId}</dd>
            </div>
            {#if tooltip.trackId}
                <div class="space-y-0.5">
                    <dt class="font-medium text-muted-foreground">Track ID</dt>
                    <dd>{tooltip.trackId}</dd>
                </div>
            {/if}
        </dl>
    </div>
</HTML>
