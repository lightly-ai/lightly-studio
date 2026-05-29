<script lang="ts">
    import { computeColorByKey } from '$lib/utils';
    import type { HTMLAttributes } from 'svelte/elements';

    interface Props {
        label: string;
        /** Explicit hex color override; if provided, skips label-based computation. */
        color?: string;
        markerProps?: HTMLAttributes<HTMLSpanElement>;
    }

    let { label, color: explicitColor, markerProps }: Props = $props();

    // Convert hex to rgba with given alpha
    const hexToRgba = (hex: string, alpha: number) => {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    };

    const colorFaded = $derived(
        explicitColor ? hexToRgba(explicitColor, 0.35) : computeColorByKey(label, 0.35).color
    );
    const colorBorder = $derived(explicitColor ?? computeColorByKey(label, 1).color);
</script>

<span
    class="inline-block h-3 w-3 shrink-0 rounded-sm border"
    style="background-color: {colorFaded}; border-color: {colorBorder};"
    {...markerProps}
></span>
