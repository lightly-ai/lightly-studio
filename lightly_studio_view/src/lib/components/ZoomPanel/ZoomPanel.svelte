<script lang="ts">
    import { ZoomIn, ZoomOut } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import type { Snippet } from 'svelte';

    const {
        onZoomReset,
        onZoomIn,
        onZoomOut,
        scale,
        isZoominDisabled,
        isZoomoutDisabled,
        isResetDisabled,
        content
    }: {
        onZoomIn: () => void;
        onZoomOut: () => void;
        scale: number;
        onZoomReset: () => void;
        isZoominDisabled?: boolean;
        isZoomoutDisabled?: boolean;
        isResetDisabled?: boolean;
        content?: Snippet;
    } = $props();
</script>

<div class="pointer-events-none absolute bottom-0 left-1 z-20 w-[200px]">
    {#if content}
        {@render content()}
    {/if}
    <div
        class="
      pointer-events-auto
      flex
      w-full
      items-center
      gap-1
      rounded-lg
      bg-muted/80
      shadow-md
      backdrop-blur-sm
    "
    >
        <Button
            variant="ghost"
            size="sm"
            onclick={onZoomReset}
            disabled={isResetDisabled}
            data-testid="zoom-reset-button"
        >
            Reset
        </Button>

        <div class="h-6 w-px bg-white/20"></div>

        <Button
            title="zoom out"
            variant="ghost"
            size="icon"
            onclick={onZoomOut}
            disabled={isZoominDisabled}
            data-testid="zoom-out-button"
        >
            <ZoomOut class="h-4 w-4" />
        </Button>

        <div class="w-[32px] text-center text-sm text-muted-foreground" data-testid="zoom-scale">
            {Math.round(scale * 100)}%
        </div>

        <Button
            title="zoom in"
            variant="ghost"
            size="icon"
            onclick={onZoomIn}
            disabled={isZoomoutDisabled}
            data-testid="zoom-in-button"
        >
            <ZoomIn class="h-4 w-4" />
        </Button>
    </div>
</div>
