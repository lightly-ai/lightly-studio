<script lang="ts">
    import type { ViewportState } from 'embedding-atlas/svelte';

    interface Props {
        viewportState: ViewportState | null;
        onViewportState: (state: ViewportState) => void;
    }

    let { viewportState, onViewportState }: Props = $props();
</script>

<output data-testid="plot-viewport">{JSON.stringify(viewportState)}</output>
<button onclick={() => onViewportState({ x: 1, y: 1, scale: 3 })}>Pan plot</button>
