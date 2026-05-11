<script lang="ts">
    import { computeColorByKey } from '$lib/utils';
    import type { HTMLAttributes } from 'svelte/elements';

    interface Props {
        label: string;
        markerProps?: HTMLAttributes<HTMLSpanElement>;
    }

    let { label, markerProps }: Props = $props();

    const colorFaded = $derived(computeColorByKey(label, 0.35));
    const color = $derived(computeColorByKey(label, 1));
</script>

<span
    class="inline-block h-3 w-3 shrink-0 rounded-sm border"
    style="background-color: {colorFaded.color}; border-color: {color.color};"
    {...markerProps}
></span>
