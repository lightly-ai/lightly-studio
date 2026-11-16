<script lang="ts">
    import Maximize from '@lucide/svelte/icons/maximize';
    import Minus from '@lucide/svelte/icons/minus';
    import Plus from '@lucide/svelte/icons/plus';
    import { Button } from '$lib/components';
    import { getTimelineViewport } from '../useTimelineViewport.svelte';

    /** Buttons to zoom the timeline in, out, or back to showing every frame. */
    const ZOOM_STEP = 1.5;
    const viewport = getTimelineViewport();
    const buttonClass = 'h-7 w-7 p-0';
</script>

<div class="flex items-center" data-testid="timeline-zoom-controls">
    <Button
        variant="ghost"
        icon={Minus}
        ariaLabel="Zoom out timeline"
        buttonProps={{
            onclick: () => viewport.zoomBy(1 / ZOOM_STEP),
            disabled: !viewport.canZoomOut,
            size: 'sm',
            class: buttonClass
        }}
    />
    <Button
        variant="ghost"
        icon={Plus}
        ariaLabel="Zoom in timeline"
        buttonProps={{
            onclick: () => viewport.zoomBy(ZOOM_STEP),
            disabled: !viewport.canZoomIn,
            size: 'sm',
            class: buttonClass
        }}
    />
    <Button
        variant="ghost"
        icon={Maximize}
        ariaLabel="Fit timeline"
        buttonProps={{
            onclick: () => viewport.reset(),
            disabled: !viewport.canZoomOut,
            size: 'sm',
            class: buttonClass
        }}
    />
</div>
