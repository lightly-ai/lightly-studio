<script lang="ts">
    import { Box, SquareDashed } from '@lucide/svelte';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';

    interface Props {
        outputType: 'mask' | 'box';
        onOutputTypeChange: (outputType: 'mask' | 'box') => void;
        canSave: boolean;
        onSave: () => void;
        onStartFresh: () => void;
    }

    let { outputType, onOutputTypeChange, canSave, onSave, onStartFresh }: Props = $props();
    const { setLastSmartSelectOutputType } = useGlobalStorage();
    const select = (value: 'mask' | 'box') => {
        onOutputTypeChange(value);
        setLastSmartSelectOutputType(value);
    };
</script>

<div class="absolute bottom-11 w-full">
    <div
        class="pointer-events-auto rounded-lg bg-muted p-2 shadow-md"
        role="dialog"
        aria-label="Smart select"
    >
        <div class="mb-1 text-sm font-semibold text-foreground">Smart select</div>
        <p class="mb-2 text-xs text-muted-foreground">
            Click to add positive points. Shift-click to add negative points. Drag to draw a box.
        </p>
        <div class="mb-2 flex gap-2">
            <button
                type="button"
                class="flex-1 rounded bg-primary px-2 py-1.5 text-sm text-primary-foreground transition hover:bg-primary/90 disabled:pointer-events-none disabled:opacity-50"
                aria-label="Save smart selection"
                disabled={!canSave}
                onclick={onSave}>Save</button
            >
            <button
                type="button"
                class="rounded border border-border px-2 py-1.5 text-sm text-muted-foreground transition hover:bg-muted-foreground/10"
                aria-label="Start fresh"
                onclick={onStartFresh}>Start fresh</button
            >
        </div>
        <div class="mb-1 text-xs font-semibold text-muted-foreground">Output</div>
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
