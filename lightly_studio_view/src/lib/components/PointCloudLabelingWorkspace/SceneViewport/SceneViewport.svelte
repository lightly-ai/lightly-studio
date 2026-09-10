<script lang="ts">
    import { Box } from '@lucide/svelte';
    import { PointCloudViewer } from '$lib/components/PointCloudViewer';
    import type { PointCloudFrame } from '../domain';
    import { toPointBatch } from './toPointBatch';

    /**
     * The interactive 3D scene. Renders one canonical frame through the shared point-cloud
     * viewer, which keeps its buffers across frames and fits the camera once.
     */
    interface Props {
        /** The frame to draw. Absent before the first one has been decoded. */
        frame?: PointCloudFrame;
    }

    let { frame }: Props = $props();

    // Once per frame, never per render: the batch is what the renderer keeps and uploads.
    const batch = $derived(frame ? toPointBatch(frame) : undefined);
</script>

<div class="flex h-full w-full flex-1 flex-col" data-testid="workspace-scene-viewport">
    {#if batch}
        <PointCloudViewer {batch} colorMode="height" />
    {:else}
        <div
            class="flex flex-1 flex-col items-center justify-center gap-2 bg-muted/30 text-muted-foreground"
        >
            <Box class="size-8" aria-hidden="true" />
            <p class="text-sm">Decoding the first frame…</p>
        </div>
    {/if}
</div>
