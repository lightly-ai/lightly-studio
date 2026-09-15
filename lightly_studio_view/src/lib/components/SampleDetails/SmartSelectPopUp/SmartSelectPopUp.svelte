<script lang="ts">
    import { Box, SquareDashed } from '@lucide/svelte';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';

    interface Props {
        outputType: 'mask' | 'box';
        onOutputTypeChange: (outputType: 'mask' | 'box') => void;
    }

    let { outputType, onOutputTypeChange }: Props = $props();
    const { setLastSmartSelectOutputType } = useGlobalStorage();
    const select = (value: 'mask' | 'box') => {
        onOutputTypeChange(value);
        setLastSmartSelectOutputType(value);
    };
</script>

<div class="absolute bottom-11 w-full">
    <div class="pointer-events-auto rounded-lg bg-muted p-2 shadow-md">
        <div class="mb-2 text-sm font-semibold text-foreground">Smart select output</div>
        <div class="flex overflow-hidden rounded-lg border border-border">
            <button
                type="button"
                class={`flex h-9 flex-1 items-center justify-center gap-1 text-sm ${outputType === 'mask' ? 'bg-primary/20 text-primary' : 'text-muted-foreground hover:bg-muted'}`}
                aria-label="Mask output"
                onclick={() => select('mask')}
            >
                <SquareDashed class="size-4" /> Mask
            </button>
            <button
                type="button"
                class={`flex h-9 flex-1 items-center justify-center gap-1 text-sm ${outputType === 'box' ? 'bg-primary/20 text-primary' : 'text-muted-foreground hover:bg-muted'}`}
                aria-label="Box output"
                onclick={() => select('box')}
            >
                <Box class="size-4" /> Box
            </button>
        </div>
    </div>
</div>
