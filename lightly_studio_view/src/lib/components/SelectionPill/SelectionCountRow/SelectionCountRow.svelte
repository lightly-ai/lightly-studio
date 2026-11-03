<script lang="ts">
    import { Plus, X } from '@lucide/svelte';
    import * as Command from '$lib/components/ui/command';
    import CoverageBar from '../CoverageBar/CoverageBar.svelte';

    interface Props {
        /** The tag or annotation class name. */
        name: string;
        /** How many selected items have it. */
        count: number;
        total: number;
        busy: boolean;
        /** The number key that adds it, shown as a badge. */
        shortcut?: number;
        onAdd: () => void;
        onRemove: () => void;
    }
    let { name, count, total, busy, shortcut, onAdd, onRemove }: Props = $props();

    const canAdd = $derived(count < total);
    const canRemove = $derived(count > 0);
    const buttonClass =
        'hidden rounded p-0.5 hover:bg-accent group-hover:block group-data-[selected]:block';
</script>

<Command.Item
    value={name}
    class="group h-8 justify-between"
    disabled={busy}
    onSelect={() => canAdd && onAdd()}
>
    <span class="flex min-w-0 items-center gap-1.5">
        {#if shortcut !== undefined}
            <kbd
                class="w-4 shrink-0 rounded border border-border bg-muted text-center text-[10px] text-muted-foreground"
                >{shortcut}</kbd
            >
        {/if}
        <span class="min-w-0 truncate">{name}</span>
    </span>
    <span class="flex items-center gap-1.5">
        <CoverageBar {count} {total} />
        <span class="text-xs tabular-nums text-muted-foreground">{count}/{total}</span>
        {#if canAdd}
            <button
                class={buttonClass}
                aria-label={`Add ${name} to selection`}
                disabled={busy}
                onclick={(e) => {
                    e.stopPropagation();
                    onAdd();
                }}><Plus class="size-3.5" /></button
            >
        {/if}
        {#if canRemove}
            <button
                class={buttonClass}
                aria-label={`Remove ${name} from selection`}
                disabled={busy}
                onclick={(e) => {
                    e.stopPropagation();
                    onRemove();
                }}><X class="size-3.5" /></button
            >
        {/if}
    </span>
</Command.Item>
