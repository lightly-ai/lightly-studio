<script lang="ts">
    import { cn } from '$lib/utils/shadcn';

    interface Props {
        value: 'class' | 'source';
        onChange: (value: 'class' | 'source') => void;
    }

    let { value, onChange }: Props = $props();

    const options = [
        { value: 'class', label: 'Class' },
        { value: 'source', label: 'Source' }
    ] as const;
</script>

<div class="flex items-center gap-2 text-sm">
    <span class="shrink-0 text-muted-foreground">Color by</span>
    <div class="flex flex-1 rounded-md bg-muted p-0.5" role="group" aria-label="Color by">
        {#each options as option (option.value)}
            {@const selected = value === option.value}
            <button
                type="button"
                aria-pressed={selected}
                class={cn(
                    'flex-1 rounded px-2 py-1 transition-colors',
                    selected
                        ? 'bg-background text-foreground shadow-sm'
                        : 'text-muted-foreground hover:text-foreground'
                )}
                onclick={() => onChange(option.value)}
            >
                {option.label}
            </button>
        {/each}
    </div>
</div>
