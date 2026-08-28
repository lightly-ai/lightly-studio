<script lang="ts">
    import { onMount } from 'svelte';
    import type { PointCloudFrame } from './types';
    import type { PointCloudScene } from './pointCloudScene';

    let { frame }: { frame?: PointCloudFrame } = $props();
    let container: HTMLDivElement;
    let scene: PointCloudScene | undefined;

    onMount(() => {
        let disposed = false;
        let observer: ResizeObserver | undefined;
        void import('./pointCloudScene').then(async ({ PointCloudScene }) => {
            const created = await PointCloudScene.create(container);
            if (disposed) return created.dispose();
            scene = created;
            if (frame) scene.setPoints(frame.points);
            observer = new ResizeObserver(([entry]) => {
                scene?.resize(entry.contentRect.width, entry.contentRect.height);
            });
            observer.observe(container);
        });
        return () => {
            disposed = true;
            observer?.disconnect();
            scene?.dispose();
        };
    });

    $effect(() => {
        if (scene && frame) scene.setPoints(frame.points);
    });
</script>

<div
    class="relative min-h-[32rem] overflow-hidden rounded-lg border bg-slate-950"
    bind:this={container}
>
    {#if !frame}
        <div
            class="pointer-events-none absolute inset-0 z-10 grid place-items-center text-sm text-slate-400"
        >
            Run either processing path to render a point-cloud frame.
        </div>
    {/if}
</div>
