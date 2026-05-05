<script lang="ts">
    import type { GridItemDragData } from '$lib/components/GridItem/GridItem.constants';
    import { useGridItemDrag } from './useGridItemDrag.svelte';

    let { dragData }: { dragData?: GridItemDragData } = $props();

    const drag = useGridItemDrag(() => dragData);
</script>

<div
    data-testid="drag-host"
    onpointerdown={drag.handlePointerDown}
    onpointermove={drag.handlePointerMove}
    onpointerup={drag.handlePointerUp}
    onpointercancel={drag.handlePointerCancel}
    onlostpointercapture={drag.handleLostPointerCapture}
    role="button"
    tabindex="0"
>
    {#if drag.isPointerDragging}
        <div data-testid="is-dragging"></div>
    {/if}
    {#if drag.dragPreview}
        <div data-testid="drag-preview"></div>
    {/if}
</div>
