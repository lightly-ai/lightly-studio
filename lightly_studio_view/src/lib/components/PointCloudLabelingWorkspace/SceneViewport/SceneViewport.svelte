<script lang="ts">
    import { Box } from '@lucide/svelte';

    /**
     * Placeholder for the interactive 3D scene. The real renderer is Three.js-based and must
     * keep being imported lazily (e.g. `await import(...)`) from within this component so its
     * bundle only loads once the workspace is actually open, never from the route shell.
     */
</script>

<div
    class="flex flex-1 flex-col items-center justify-center gap-2 bg-muted/30 text-muted-foreground"
    data-testid="workspace-scene-viewport"
>
    <Box class="size-8" aria-hidden="true" />
    <p class="text-sm">3D scene</p>
</div>
