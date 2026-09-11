<script lang="ts">
    import { CameraOff } from '@lucide/svelte';
    import type { CameraFrame } from '../domain';

    /**
     * One camera's picture for the frame on screen.
     *
     * Drawn onto a canvas rather than put in an `img`: the picture arrives as a decoded
     * bitmap the session owns and closes, and drawing it copies what the tile needs without
     * the tile taking a reference it would then have to release.
     */
    interface Props {
        camera: CameraFrame;
        /** Absent when the camera published nothing for this moment, or its picture expired. */
        image?: ImageBitmap;
    }

    let { camera, image }: Props = $props();

    let canvas = $state<HTMLCanvasElement | undefined>(undefined);

    $effect(() => {
        const target = canvas;
        const picture = image;
        if (!target || !picture) return;
        target.width = picture.width;
        target.height = picture.height;
        target.getContext('2d')?.drawImage(picture, 0, 0);
    });
</script>

<figure
    class="flex h-full min-w-40 shrink-0 flex-col items-center justify-center gap-1 overflow-hidden rounded-md border bg-muted/30 text-muted-foreground"
    data-testid="workspace-camera-tile"
>
    {#if image}
        <canvas bind:this={canvas} class="min-h-0 flex-1 object-contain" aria-label={camera.id}
        ></canvas>
    {:else}
        <CameraOff class="size-5" aria-hidden="true" />
    {/if}
    <figcaption class="w-full truncate px-2 text-center text-xs">{camera.id}</figcaption>
</figure>
