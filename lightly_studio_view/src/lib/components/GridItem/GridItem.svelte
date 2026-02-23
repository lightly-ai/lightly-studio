<script lang="ts">
    import type { Snippet } from 'svelte';
    import type { HTMLAttributes } from 'svelte/elements';

    let {
        children,
        width = 300,
        height = 300,
        props
    }: {
        children: Snippet;
        width?: string | number;
        height?: string | number;
        props?: HTMLAttributes<HTMLDivElement>;
    } = $props();

    function formatSize(value: string | number): string {
        return typeof value === 'number' ? `${value}px` : value;
    }
</script>

<div class="relative select-none dark:[color-scheme:dark]" role="button" tabindex="0" {...props}>
    <div
        class="relative overflow-hidden rounded-lg"
        style="width: {formatSize(width)}; height: {formatSize(height)};"
    >
        {@render children()}
    </div>
</div>
