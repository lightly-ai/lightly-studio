<script lang="ts">
    import { cn } from '$lib/utils/shadcn.js';

    interface Props {
        selectedColor: string;
        onSelect: (color: string) => void;
    }

    let { selectedColor, onSelect }: Props = $props();

    const PRESET_COLORS = [
        '#ff0000',
        '#ff8000',
        '#ffff00',
        '#80ff00',
        '#00ff00',
        '#00ffff',
        '#0080ff',
        '#0000ff',
        '#8000ff',
        '#ff00ff',
        '#ff0080',
        '#ffffff',
        '#cccccc',
        '#888888',
        '#444444',
        '#000000'
    ];
</script>

<div class="space-y-1">
    <div class="text-xs">Presets</div>
    <div class="grid grid-cols-8 gap-1">
        {#each PRESET_COLORS as color}
            <button
                type="button"
                class={cn(
                    'h-4 w-4 rounded-sm border',
                    color === selectedColor ? 'ring-primary ring-1' : ''
                )}
                style={`background-color: ${color}`}
                onclick={() => onSelect(color)}
                title={color}
                aria-label={color}
                aria-pressed={color === selectedColor}
            ></button>
        {/each}
    </div>
</div>
