<script lang="ts">
    import { Database, Tag } from '@lucide/svelte';
    import { cn } from '$lib/utils/shadcn';
    import type { GroupBy } from './groupPairRows';

    interface Props {
        value: GroupBy;
        onChange: (value: GroupBy) => void;
    }

    let { value, onChange }: Props = $props();

    const options = [
        { value: 'source', label: 'By source', icon: Database },
        { value: 'class', label: 'By class', icon: Tag }
    ] as const;
</script>

<div class="flex rounded-md bg-muted p-0.5 text-sm" role="group" aria-label="Group the tree">
    {#each options as option (option.value)}
        {@const selected = value === option.value}
        <button
            type="button"
            aria-pressed={selected}
            class={cn(
                'flex flex-1 items-center justify-center gap-1.5 rounded px-2 py-1 transition-colors',
                selected
                    ? 'bg-background text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
            )}
            onclick={() => onChange(option.value)}
        >
            <option.icon class="size-3.5" aria-hidden="true" />
            {option.label}
        </button>
    {/each}
</div>
