<script lang="ts">
    import Box from '@lucide/svelte/icons/box';
    import SquareDashed from '@lucide/svelte/icons/square-dashed';
    import { cn } from '$lib/utils';
    import { Button } from '$lib/components/ui/button';

    type SaveAs = (typeof saveAsOptions)[number]['value'];

    interface Props {
        saveAs: SaveAs;
        onSaveAsChange: (saveAs: SaveAs) => void;
    }

    let { saveAs, onSaveAsChange }: Props = $props();

    const saveAsOptions = [
        { value: 'mask', label: 'Mask', icon: SquareDashed },
        { value: 'box', label: 'Box', icon: Box }
    ] as const;
</script>

<div class="flex overflow-hidden rounded-md border border-border" role="group" aria-label="Save as">
    {#each saveAsOptions as option (option.value)}
        <Button
            variant="ghost"
            class={cn(
                'h-8 flex-1 gap-1 rounded-none',
                saveAs === option.value
                    ? 'bg-primary/20 text-primary hover:bg-primary/20 hover:text-primary'
                    : 'text-muted-foreground'
            )}
            aria-label={`Save as ${option.label}`}
            aria-pressed={saveAs === option.value}
            onclick={() => onSaveAsChange(option.value)}
        >
            <option.icon />
            {option.label}
        </Button>
    {/each}
</div>
