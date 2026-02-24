<script lang="ts">
    import type { HTMLAttributes } from 'svelte/elements';
    import GridItem from './GridItem.svelte';

    let {
        content = '',
        width,
        height,
        props
    }: {
        content?: string;
        width?: string | number;
        height?: string | number;
        props?: HTMLAttributes<HTMLDivElement>;
    } = $props();
</script>

<GridItem {width} {height} containerProps={props}>
    {content}
</GridItem>
