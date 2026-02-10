<script lang="ts">
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';

    type SteppingNavigationProps = {
        hasPrevious: boolean;
        hasNext: boolean;
        onNext: () => void;
        onPrevious: () => void;
    };
    const { hasPrevious, hasNext, onNext, onPrevious }: SteppingNavigationProps = $props();
    const { context: annotationLabelContext } = useAnnotationLabelContext();

    const handleKeyDownEvent = (event: KeyboardEvent) => {
        if (annotationLabelContext.isDrawing) return;
        switch (event.key) {
            case 'ArrowRight':
                onNext();
                break;
            case 'ArrowLeft':
                onPrevious();
                break;
        }
    };
</script>

{#if hasPrevious}
    <button
        class="absolute left-4 top-1/2 z-30 -translate-y-1/2 rounded-full bg-black/30 p-2 text-white opacity-50 transition-opacity hover:opacity-100"
        class:pointer-events-none={annotationLabelContext.isDrawing}
        class:opacity-20={annotationLabelContext.isDrawing}
        onclick={onPrevious}
        aria-label="Previous sample"
        disabled={annotationLabelContext.isDrawing}
    >
        <svg
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
        >
            <path d="m15 18-6-6 6-6" />
        </svg>
    </button>
{/if}

{#if hasNext}
    <button
        class="absolute right-4 top-1/2 z-30 -translate-y-1/2 rounded-full bg-black/30 p-2 text-white opacity-50 transition-opacity hover:opacity-100"
        class:pointer-events-none={annotationLabelContext.isDrawing}
        class:opacity-20={annotationLabelContext.isDrawing}
        onclick={onNext}
        aria-label="Next sample"
        disabled={annotationLabelContext.isDrawing}
    >
        <svg
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
        >
            <path d="m9 18 6-6-6-6" />
        </svg>
    </button>
{/if}

<svelte:window onkeydown={handleKeyDownEvent} />
