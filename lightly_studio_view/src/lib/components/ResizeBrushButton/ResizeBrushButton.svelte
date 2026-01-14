<script lang="ts">
    import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { SlidersHorizontal } from '@lucide/svelte';

    let { value = $bindable<number>(), collectionId }: { value: number; collectionId: string } =
        $props();

    let showSlider = $state(false);

    const { updateLastAnnotationBrushSize } = useGlobalStorage();

    function onFocusOutSettings(event: FocusEvent) {
        const currentTarget = event.currentTarget as HTMLElement;
        const relatedTarget = event.relatedTarget as HTMLElement | null;

        if (!currentTarget.contains(relatedTarget)) {
            showSlider = false;
        }
    }

    let { setStatus } = useSampleDetailsToolbarContext();
</script>

<div class="relative" tabindex="-1" onfocusout={onFocusOutSettings}>
    <button
        type="button"
        aria-label="Toggle slider"
        onclick={() => {
            setStatus('settings');
            showSlider = !showSlider;
        }}
        class="flex items-center justify-center rounded-md p-2 transition-colors
                   hover:bg-black/20 focus:outline-none"
    >
        <SlidersHorizontal class="size-6 " />
    </button>

    {#if showSlider}
        <div
            class="
                    absolute left-full top-1/2 z-50 ml-2
                    w-40 -translate-y-1/2 rounded-md border
                    bg-background p-3 shadow-lg
                "
        >
            <input
                type="range"
                bind:value
                onchange={() => updateLastAnnotationBrushSize(collectionId, value)}
                min="2"
                max="10"
                class="w-full accent-primary"
            />
        </div>
    {/if}
</div>
