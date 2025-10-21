<script lang="ts">
    import { ZoomIn, ZoomOut } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';

    const {
        onZoomReset,
        onZoomIn,
        onZoomOut,
        scale,
        isZoominDisabled,
        isZoomoutDisabled,
        isResetDisabled
    }: {
        onZoomIn: () => void;
        onZoomOut: () => void;
        scale: number;
        onZoomReset: () => void;
        isZoominDisabled?: boolean;
        isZoomoutDisabled?: boolean;
        isResetDisabled?: boolean;
    } = $props();
</script>

<div
    class="pointer-events-auto absolute bottom-0 left-1 z-20 flex select-none items-center gap-1 rounded-lg bg-muted bg-opacity-80 shadow-md backdrop-blur-sm"
>
    <Button
        variant="ghost"
        data-testid="zoom-reset"
        size="sm"
        onclick={onZoomReset}
        disabled={isResetDisabled}>Reset</Button
    >
    <div class="h-6 w-px bg-white bg-opacity-20"></div>
    <Button
        title="zoom out"
        variant="ghost"
        size="icon"
        data-testid="zoom-out"
        onclick={onZoomOut}
        disabled={isZoominDisabled}
    >
        <ZoomOut class="h-4 w-4" />
    </Button>

    <div class="w-[32px] text-center text-sm text-muted-foreground" data-testid="zoom-level">
        {Math.round(scale * 100)}%
    </div>

    <Button
        title="zoom in"
        variant="ghost"
        size="icon"
        data-testid="zoom-in"
        onclick={onZoomIn}
        disabled={isZoomoutDisabled}
    >
        <ZoomIn class="h-4 w-4" />
    </Button>
</div>
