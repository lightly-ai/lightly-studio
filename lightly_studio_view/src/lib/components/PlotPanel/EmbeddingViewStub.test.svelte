<script lang="ts">
    import type { DataPoint, ViewportState } from 'embedding-atlas/svelte';

    interface Props {
        viewportState: ViewportState | null;
        onViewportState: (state: ViewportState) => void;
        onSelection: (points: DataPoint[] | null) => void;
    }

    let { viewportState, onViewportState, onSelection }: Props = $props();
</script>

<output data-testid="plot-viewport">{JSON.stringify(viewportState)}</output>
<button onclick={() => onViewportState({ x: 1, y: 1, scale: 3 })}>Pan plot</button>
<!-- An input, not a button: the tool pill takes the stub's buttons for the library's tools. -->
<input
    type="button"
    value="Pick point"
    onclick={() => onSelection([{ x: 0, y: 0, identifier: 'sample-1' }])}
/>
