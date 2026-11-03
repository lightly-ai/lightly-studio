<script lang="ts">
    import { Pencil } from '@lucide/svelte';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import { cn } from '$lib/utils';

    interface Props {
        sourceName: string;
        /** Whether new annotations are written to this source. */
        isTarget: boolean;
        /** Whether no source is picked yet, so every button asks for a click. */
        needsPick: boolean;
        onSetTarget: () => void;
    }

    let { sourceName, isTarget, needsPick, onSetTarget }: Props = $props();

    const label = $derived(
        isTarget ? `New annotations go to ${sourceName}` : `Add new annotations to ${sourceName}`
    );
</script>

<Tooltip content={label}>
    <button
        type="button"
        aria-label={label}
        aria-pressed={isTarget}
        class={cn(
            'flex size-6 shrink-0 items-center justify-center rounded-md transition-colors',
            isTarget && 'bg-primary text-primary-foreground',
            !isTarget && needsPick && 'text-amber-400 hover:bg-amber-400/15',
            !isTarget &&
                !needsPick &&
                'text-muted-foreground/40 hover:bg-muted hover:text-foreground'
        )}
        onclick={(e) => {
            e.stopPropagation();
            onSetTarget();
        }}
        data-testid={`annotation-target-${sourceName}`}
    >
        <Pencil class="size-3.5" />
    </button>
</Tooltip>
