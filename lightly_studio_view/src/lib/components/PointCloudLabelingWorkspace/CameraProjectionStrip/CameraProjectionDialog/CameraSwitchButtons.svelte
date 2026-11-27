<script lang="ts">
    import ChevronLeft from '@lucide/svelte/icons/chevron-left';
    import ChevronRight from '@lucide/svelte/icons/chevron-right';
    import { Button } from '$lib/components/ui/button';

    interface Props {
        /** Shows the previous camera; the button is disabled without it. */
        onPrevious?: () => void;
        /** Shows the next camera; the button is disabled without it. */
        onNext?: () => void;
        previousKey: string;
        nextKey: string;
    }

    const { onPrevious, onNext, previousKey, nextKey }: Props = $props();
</script>

<div class="flex items-center gap-1">
    <Button
        variant="outline"
        size="xs"
        aria-label="Previous camera"
        title={`Shortcut: ${previousKey}`}
        disabled={!onPrevious}
        onclick={onPrevious}
    >
        <ChevronLeft />
    </Button>
    <Button
        variant="outline"
        size="xs"
        aria-label="Next camera"
        title={`Shortcut: ${nextKey}`}
        disabled={!onNext}
        onclick={onNext}
    >
        <ChevronRight />
    </Button>
</div>
