<script lang="ts">
    import * as Command from '$lib/components/ui/command/index.js';
    import { cn } from '$lib/utils';

    interface Props {
        /**
         * `value` is unique per row. A create row offers its label as a new name. A disabled
         * row shows its note and can't be picked.
         */
        row: {
            value: string;
            label: string;
            onPick: () => void;
            isCreate?: boolean;
            disabled?: boolean;
            note?: string;
        };
        disabled: boolean;
    }

    const { row, disabled }: Props = $props();
</script>

<Command.Item
    value={row.value}
    disabled={disabled || row.disabled}
    onSelect={row.onPick}
    class={row.isCreate ? 'border-t' : undefined}
>
    {#if row.isCreate}<span class="opacity-50">Create:</span>{/if}
    <span class={cn('min-w-0 truncate', row.isCreate && 'font-semibold')}>{row.label}</span>
    {#if row.note}
        <span class="ml-auto text-xs text-muted-foreground">{row.note}</span>
    {/if}
</Command.Item>
