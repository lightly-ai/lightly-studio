<script lang="ts">
    import { cn } from '$lib/utils';
    import type { HTMLAttributes } from 'svelte/elements';

    const {
        className,
        src,
        imgProps
    }: {
        className?: string;
        src?: string;
        imgProps?: HTMLAttributes<HTMLImageElement>;
    } = $props();
</script>

<img
    {src}
    alt={src}
    class={cn('image rounded-lg bg-black', className)}
    loading="lazy"
    {...imgProps}
/>
