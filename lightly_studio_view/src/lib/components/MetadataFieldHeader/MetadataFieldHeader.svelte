<script lang="ts">
    import { ChevronDown, ChevronRight, X } from '@lucide/svelte';
    import { Button as IconButton } from '$lib/components/ui/button';

    interface Props {
        /** Field name as stored, e.g. `split` or `Width`. */
        title: string;
        /** Short state text after the title, e.g. "Updating…". */
        status?: string;
        /** Whether the field body shows. Only used with `onToggleExpanded`. */
        expanded?: boolean;
        /** Makes the title a button that shows or hides the field body. */
        onToggleExpanded?: () => void;
        /** Shows a remove button that takes the field out of the filters. */
        onRemove?: () => void;
    }

    const { title, status, expanded = true, onToggleExpanded, onRemove }: Props = $props();
</script>

<div class="flex min-h-6 items-center justify-between gap-2">
    <h3 class="min-w-0 truncate text-sm font-medium" {title}>
        {#if onToggleExpanded}
            <button
                type="button"
                class="flex w-full min-w-0 items-center gap-1 text-left"
                aria-expanded={expanded}
                onclick={onToggleExpanded}
            >
                {#if expanded}
                    <ChevronDown class="size-4 shrink-0" />
                {:else}
                    <ChevronRight class="size-4 shrink-0" />
                {/if}
                <span class="truncate">{title}</span>
            </button>
        {:else}
            {title}
        {/if}
    </h3>
    <div class="flex shrink-0 items-center gap-1">
        {#if status}
            <span class="text-xs text-muted-foreground" role="status">{status}</span>
        {/if}
        {#if onRemove}
            <IconButton
                variant="ghost"
                size="icon"
                class="size-6"
                aria-label={`Remove metadata field ${title}`}
                onclick={onRemove}
            >
                <X class="size-4" />
            </IconButton>
        {/if}
    </div>
</div>
