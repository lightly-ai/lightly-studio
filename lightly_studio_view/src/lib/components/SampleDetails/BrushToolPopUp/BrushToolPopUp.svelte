<script lang="ts">
    import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';
    import { Brush, Eraser } from '@lucide/svelte';

    const { context: sampleDetailsToolbarContext, setBrushMode } = useSampleDetailsToolbarContext();
</script>

<div class="absolute bottom-11 w-full">
    <div
        class="
      pointer-events-auto
      flex
      w-full
      select-none
      flex-col
      items-stretch
      gap-1
      rounded-lg
      bg-muted
      shadow-md
    "
    >
        <div class="px-4 py-3 text-left">
            <h3 class="text-sm font-semibold text-foreground">Brush Tool</h3>
        </div>

        <div class="space-y-4 px-4">
            <div class="flex items-center gap-4">
                <span class="w-16 text-sm text-muted-foreground"> Mode: </span>

                <div class="flex overflow-hidden rounded-lg border border-border">
                    <button
                        aria-label="Brush mode"
                        class="
              flex h-9 w-12 items-center justify-center transition
              {sampleDetailsToolbarContext.brush.mode === 'brush'
                            ? 'bg-primary/20 text-primary'
                            : 'text-muted-foreground hover:bg-muted'}
            "
                        onclick={() => setBrushMode('brush')}
                    >
                        <Brush class="h-4 w-4" />
                    </button>

                    <button
                        aria-label="Eraser mode"
                        class="
              flex h-9 w-12 items-center justify-center transition
              {sampleDetailsToolbarContext.brush.mode === 'eraser'
                            ? 'bg-primary/20 text-primary'
                            : 'text-muted-foreground hover:bg-muted'}
            "
                        onclick={() => setBrushMode('eraser')}
                    >
                        <Eraser class="h-4 w-4" />
                    </button>
                </div>
            </div>

            <div class="flex items-center gap-4 pb-4">
                <span class="w-16 text-sm text-muted-foreground"> Size: </span>

                <input
                    aria-label="Brush size"
                    type="range"
                    min="1"
                    max="100"
                    bind:value={sampleDetailsToolbarContext.brush.size}
                    class="w-full accent-primary"
                />
            </div>
        </div>
    </div>
</div>
