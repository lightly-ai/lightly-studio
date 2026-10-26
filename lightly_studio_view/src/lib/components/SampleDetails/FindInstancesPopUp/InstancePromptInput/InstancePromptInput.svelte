<script lang="ts">
    import { Loader2, Sparkles, SquareDashedMousePointer } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import { Input } from '$lib/components/ui/input';
    import type { useFindInstances } from '$lib/components/SampleDetails/FindInstancesOverlay/useFindInstances.svelte';

    interface Props {
        prompt: string;
        onPromptChange: (prompt: string) => void;
        isDrawingBox: boolean;
        onDrawBoxChange: (isDrawingBox: boolean) => void;
        instances: ReturnType<typeof useFindInstances>;
    }

    let { prompt, onPromptChange, isDrawingBox, onDrawBoxChange, instances }: Props = $props();

    const onKeydown = (event: KeyboardEvent) => {
        // Enter also confirms an input method candidate, which must not start a search.
        // Safari sends that Enter with isComposing false and keyCode 229.
        const isComposing = event.isComposing || event.keyCode === 229;
        if (event.key !== 'Enter' || isComposing || !instances.canGenerate) return;
        void instances.generate();
    };
</script>

<div class="flex items-center gap-1.5">
    <Input
        class="h-8"
        wrapperClass="min-w-0 flex-1"
        aria-label="Instance prompt"
        placeholder="e.g. cars"
        value={prompt}
        oninput={(event) => onPromptChange(event.currentTarget.value)}
        onkeydown={onKeydown}
    />
    <Button
        variant={isDrawingBox ? 'secondary' : 'outline'}
        size="icon"
        class="size-8 shrink-0"
        aria-label="Draw box"
        aria-pressed={isDrawingBox}
        title="Draw box"
        onclick={() => onDrawBoxChange(!isDrawingBox)}
    >
        <SquareDashedMousePointer />
    </Button>
    <Button
        size="icon"
        class="size-8 shrink-0"
        aria-label="Find instances"
        title="Find instances"
        disabled={!instances.canGenerate}
        onclick={() => void instances.generate()}
    >
        {#if instances.isGenerating}
            <Loader2 class="animate-spin" />
        {:else}
            <Sparkles />
        {/if}
    </Button>
</div>
