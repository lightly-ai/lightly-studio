<script lang="ts">
    import { Camera, SquareDashed } from '@lucide/svelte';

    /**
     * Horizontal strip of the camera images and orthographic frame projections that belong to the
     * active point-cloud frame. It sits directly under the 3D viewport so a selected cuboid can be
     * checked against every available view without leaving the scene.
     *
     * Placeholder tiles: the real ones come from the frame's `cameras` plus the orthographic
     * renderer views, and stay synchronized with the 3D selection.
     */
    const views: { label: string; kind: 'camera' | 'projection' }[] = [
        { label: 'Front camera', kind: 'camera' },
        { label: 'Left camera', kind: 'camera' },
        { label: 'Right camera', kind: 'camera' },
        { label: 'Rear camera', kind: 'camera' },
        { label: 'Top (BEV)', kind: 'projection' },
        { label: 'Side', kind: 'projection' },
        { label: 'Front', kind: 'projection' }
    ];
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
        {#each views as view (view.label)}
            <figure
                class="flex h-full min-w-40 shrink-0 flex-col items-center justify-center gap-1 rounded-md border bg-muted/30 text-muted-foreground"
            >
                {#if view.kind === 'camera'}
                    <Camera class="size-5" aria-hidden="true" />
                {:else}
                    <SquareDashed class="size-5" aria-hidden="true" />
                {/if}
                <figcaption class="px-2 text-center text-xs">{view.label}</figcaption>
            </figure>
        {/each}
    </div>
</div>
