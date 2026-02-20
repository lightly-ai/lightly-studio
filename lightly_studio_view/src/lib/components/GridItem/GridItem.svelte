<script lang="ts">
    import type { Snippet } from 'svelte';
    import type { HTMLAttributes } from 'svelte/elements';

    let {
        children,
        onclick,
        width = '100px',
        height = '100px',
        ...props
    }: {
        children: Snippet;
        onclick?: (event: MouseEvent) => void;
        width?: string | number;
        height?: string | number;
    } & HTMLAttributes<HTMLDivElement> = $props();

    function handleOnClick(event: MouseEvent) {
        if (onclick) {
            onclick(event);
        }
    }

    function formatSize(value: string | number): string {
        return typeof value === 'number' ? `${value}px` : value;
    }
</script>

<div
    class="relative select-none dark:[color-scheme:dark]"
    role="button"
    tabindex="0"
    onclick={handleOnClick}
    {...props}
>
    <div
        class="relative overflow-hidden rounded-lg"
        style="width: {formatSize(width)}; height: {formatSize(height)};"
    >
        {@render children()}
    </div>
</div>
