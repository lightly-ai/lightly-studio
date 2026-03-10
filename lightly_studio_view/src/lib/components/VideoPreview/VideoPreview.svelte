<script lang="ts">
    import { cn } from '$lib/utils';
    import { Play } from '@lucide/svelte';
    import type { HTMLVideoAttributes } from 'svelte/elements';

    const {
        className,
        src,
        videoProps
    }: {
        className?: string;
        src: string;
        videoProps?: HTMLVideoAttributes;
    } = $props();
</script>

<div class={cn('relative aspect-square', className)}>
    <video
        {src}
        class="h-full w-full rounded-lg bg-black object-cover"
        preload="metadata"
        muted
        {...videoProps}
    ></video>
    <div
        class="pointer-events-none absolute inset-0 flex items-center justify-center rounded-lg bg-black/20 transition-opacity"
    >
        <div class="rounded-full bg-black/60 p-3 backdrop-blur-sm">
            <Play class="h-6 w-6 fill-white text-white" />
        </div>
    </div>
</div>
