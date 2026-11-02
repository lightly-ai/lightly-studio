<script lang="ts">
    import { X } from '@lucide/svelte';
    import { Tooltip } from '$lib/components/ui/tooltip';

    interface Props {
        tagName: string;
        count: number;
        total: number;
        canRemove: boolean;
        busy: boolean;
        onRemove: () => void;
    }

    let { tagName, count, total, canRemove, busy, onRemove }: Props = $props();
</script>

{#if count > 0}
    <span
        class="shrink-0 rounded-full bg-primary/15 px-1.5 text-[11px] tabular-nums text-foreground"
        data-testid="tag-selection-count"
    >
        {count} / {total}
    </span>
    {#if canRemove}
        <Tooltip content={`Remove "${tagName}" from ${count} selected`} position="right">
            <button
                type="button"
                class="inline-flex size-6 shrink-0 items-center justify-center rounded-md text-muted-foreground opacity-0 hover:bg-destructive hover:text-destructive-foreground focus-visible:opacity-100 disabled:opacity-50 group-hover:opacity-100"
                aria-label={`Remove tag ${tagName} from selection`}
                disabled={busy}
                onclick={(event: MouseEvent) => {
                    event.stopPropagation();
                    onRemove();
                }}
            >
                <X class="size-3.5" />
            </button>
        </Tooltip>
    {/if}
{/if}
