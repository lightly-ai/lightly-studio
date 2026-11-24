<script lang="ts">
    import { useThrelte } from '@threlte/core';
    import { onDestroy } from 'svelte';
    import type { WebGLRenderer } from 'three';

    // Threlte disposes the renderer on unmount but keeps its WebGL context until garbage
    // collection. Browsers cap live contexts and drop the oldest one, which blanks the main
    // viewport after the Top, Side, and Front views mount a few times.
    const { renderer } = useThrelte<WebGLRenderer>();
    onDestroy(() => renderer.forceContextLoss());
</script>
