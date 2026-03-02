<script lang="ts">
    import type { HTMLAttributes } from 'svelte/elements';
    import Image from './Image.svelte';

    let {
        src,
        className,
        imgProps
    }: {
        src?: string;
        className?: string;
        imgProps?: HTMLAttributes<HTMLImageElement>;
    } = $props();
</script>

<Image {src} {className} {imgProps} />
