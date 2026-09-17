<script lang="ts">
    import type { CuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/domain';
    import { createAnnotationDetails } from './pointCloudAnnotationDetails';
    import Typography from '$lib/components/Typography/Typography.svelte';

    interface Props {
        /** Cuboid whose metadata is displayed. */
        annotation: CuboidAnnotation;
    }

    let { annotation }: Props = $props();

    const details = $derived(createAnnotationDetails({ annotation }));
</script>

<dl class="space-y-3 text-diffuse-foreground" data-testid="point-cloud-annotation-details">
    <div class="space-y-1">
        <Typography component="dt" variant="body2">Location:</Typography>
        <dd class="mt-1 grid grid-cols-3 gap-x-4">
            <Typography variant="body2">X {details.location[0]}</Typography>
            <Typography variant="body2">Y {details.location[1]}</Typography>
            <Typography variant="body2">Z {details.location[2]}</Typography>
        </dd>
    </div>

    <div class="space-y-1">
        <Typography component="dt" variant="body2">Dimensions (m):</Typography>
        <dd class="mt-1 grid grid-cols-3 gap-x-4">
            <Typography variant="body2">W {details.dimensions[0]}</Typography>
            <Typography variant="body2">H {details.dimensions[1]}</Typography>
            <Typography variant="body2">D {details.dimensions[2]}</Typography>
        </dd>
    </div>

    <div class="space-y-1">
        <Typography component="dt" variant="body2">Rotation:</Typography>
        <dd class="mt-1 grid grid-cols-3 gap-x-4">
            <Typography variant="body2">rx {details.rotation[0]}°</Typography>
            <Typography variant="body2">ry {details.rotation[1]}°</Typography>
            <Typography variant="body2">rz {details.rotation[2]}°</Typography>
        </dd>
    </div>

    <div class="grid grid-cols-[5rem_1fr] gap-x-2">
        <Typography component="dt" variant="body2">Annotation source:</Typography>
        <Typography component="dd" variant="body2">{details.annotationSourceId}</Typography>
    </div>

    {#if details.trackId}
        <div class="grid grid-cols-[5rem_1fr] gap-x-2">
            <Typography component="dt" variant="body2">Track ID:</Typography>
            <Typography component="dd" variant="body2">{details.trackId}</Typography>
        </div>
    {/if}
</dl>
