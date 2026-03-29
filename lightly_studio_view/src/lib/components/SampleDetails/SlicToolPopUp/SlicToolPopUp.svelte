<script lang="ts">
    import { useSampleDetailsToolbarContext, type SlicLevel } from '$lib/contexts/SampleDetailsToolbar.svelte';

    const { context: sampleDetailsToolbarContext, setSlicLevel } = useSampleDetailsToolbarContext();

    const levelLabels: Record<SlicLevel, string> = {
        coarse: 'Coarse',
        medium: 'Medium',
        fine: 'Fine'
    };

    const orderedLevels: SlicLevel[] = ['coarse', 'medium', 'fine'];
</script>

<div class="absolute bottom-11 flex w-full justify-center">
    <div
        data-testid="slic-tool-popup"
        class="
      pointer-events-auto
      flex
      w-[280px]
      max-w-full
      select-none
      flex-col
      items-stretch
      gap-2
      rounded-lg
      bg-muted
      p-2
      shadow-md
    "
    >
        <div class="text-left">
            <h3 class="text-sm font-semibold text-foreground">AI-Assisted Labeling</h3>
            <p class="text-xs text-muted-foreground">Click a superpixel to toggle it.</p>
        </div>

        <div class="flex flex-col gap-1">
            <span class="text-sm text-muted-foreground">Level</span>
            <div class="grid grid-cols-3 gap-1">
                {#each orderedLevels as level}
                    <button
                        type="button"
                        class={`min-w-0 rounded px-2 py-1 text-center text-xs transition
                            ${sampleDetailsToolbarContext.slic.level === level
                                ? 'bg-primary text-primary-foreground'
                                : 'bg-background text-muted-foreground hover:bg-accent hover:text-foreground'}`}
                        onclick={() => setSlicLevel(level)}
                    >
                        {levelLabels[level]}
                    </button>
                {/each}
            </div>
        </div>

        <div class="flex items-center justify-between gap-2 text-xs">
            <span class="text-muted-foreground">Status</span>
            <span class="font-medium text-foreground">{sampleDetailsToolbarContext.slic.status}</span>
        </div>
    </div>
</div>
