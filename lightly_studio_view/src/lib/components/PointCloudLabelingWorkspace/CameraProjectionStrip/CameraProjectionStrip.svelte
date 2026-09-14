<script lang="ts">
    import { Camera, SquareDashed } from '@lucide/svelte';
    import type { CameraFrame } from '../domain';
    import CameraTile from './CameraTile.svelte';

    /**
     * Horizontal strip of the camera images and orthographic frame projections that belong to the
     * active point-cloud frame. It sits directly under the 3D viewport so a selected cuboid can be
     * checked against every available view without leaving the scene.
     *
     * The camera tiles follow the frame: stepping, scrubbing and playback all hand over a new
     * frame, and each tile draws the picture its camera was showing at that moment. The
     * orthographic projections are still placeholders; they come with the renderer views.
     */
    interface Props {
        /** Cameras of the frame on screen. Empty until a frame with imagery is decoded. */
        cameras?: readonly CameraFrame[];
        /** Resolves a camera's decoded picture, which the frame refers to by id. */
        resolveImage?: (resourceId: string) => ImageBitmap | undefined;
    }

    let { cameras = [], resolveImage }: Props = $props();

    const projections = ['Top (BEV)', 'Side', 'Front'];
</script>

<div
    class="flex h-full min-h-0 flex-col border-t bg-background"
    data-testid="workspace-projection-strip"
>
    <div class="flex shrink-0 items-center gap-2 px-3 py-1.5 text-xs text-muted-foreground">
        <span class="font-medium text-foreground">Cameras &amp; projections</span>
        <span>· synchronized with the 3D selection</span>
    </div>
    <div class="flex min-h-0 flex-1 gap-2 overflow-x-auto px-3 pb-2">
        {#if cameras.length === 0}
            <figure
                class="flex h-full min-w-40 shrink-0 flex-col items-center justify-center gap-1 rounded-md border bg-muted/30 text-muted-foreground"
            >
                <Camera class="size-5" aria-hidden="true" />
                <figcaption class="px-2 text-center text-xs">No camera for this frame</figcaption>
            </figure>
        {:else}
            {#each cameras as camera (camera.id)}
                <CameraTile
                    {camera}
                    image={camera.image?.kind === 'uri'
                        ? camera.image.uri
                        : camera.image?.kind === 'decoded'
                          ? resolveImage?.(camera.image.resourceId)
                          : undefined}
                />
            {/each}
        {/if}
        {#each projections as projection (projection)}
            <figure
                class="flex h-full min-w-40 shrink-0 flex-col items-center justify-center gap-1 rounded-md border bg-muted/30 text-muted-foreground"
            >
                <SquareDashed class="size-5" aria-hidden="true" />
                <figcaption class="px-2 text-center text-xs">{projection}</figcaption>
            </figure>
        {/each}
    </div>
</div>
