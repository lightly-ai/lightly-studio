<script lang="ts">
    import { Tooltip } from '$lib/components/ui/tooltip';
    import { focusTagAssignInput } from '$lib/components/TagsMenu/tagAssignInput';
    import { formatInteger } from '$lib/utils';
    import { Download, Ellipsis, Tag } from '@lucide/svelte';

    interface Props {
        selectedCount: number;
        onClear: () => void;
        /** Opens the export dialog for the current collection. */
        onExport: (() => void) | undefined;
        /** Opens the collection's overflow menu (sampling, plugins, settings, …). */
        onMore: (() => void) | undefined;
    }

    const { selectedCount, onClear, onExport, onMore }: Props = $props();

    const iconButtonClass =
        'flex h-7 w-8 items-center justify-center rounded-md border border-border-hard text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-foreground disabled:opacity-40';
</script>

{#if selectedCount > 0}
    <div
        class="m-1.5 rounded-[9px] border border-primary/25 bg-primary/[0.07] p-2.5"
        data-testid="sidebar-selection-actions"
    >
        <div class="mb-2 flex items-center justify-between gap-2">
            <span class="truncate text-xs font-semibold text-primary">
                {formatInteger(selectedCount)}
                {selectedCount === 1 ? 'sample' : 'samples'} selected
            </span>
            <button
                class="shrink-0 text-[11px] text-muted-foreground transition-colors hover:text-foreground"
                onclick={onClear}
                data-testid="clear-selection-button">Clear</button
            >
        </div>
        <div class="flex items-center gap-1.5">
            <button
                class="flex h-7 flex-1 items-center justify-center gap-1.5 rounded-md bg-primary text-xs font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
                onclick={focusTagAssignInput}
                data-testid="sidebar-selection-tag"
            >
                <Tag class="size-[13px]" />
                Tag
            </button>
            <Tooltip content="Export selection" position="top" class="w-max">
                <button
                    class={iconButtonClass}
                    onclick={onExport}
                    disabled={!onExport}
                    aria-label="Export selection"
                    data-testid="sidebar-selection-export"
                >
                    <Download class="size-[13px]" />
                </button>
            </Tooltip>
            <Tooltip content="More actions" position="top" class="w-max">
                <button
                    class={iconButtonClass}
                    onclick={onMore}
                    disabled={!onMore}
                    aria-label="More actions"
                    data-testid="sidebar-selection-more"
                >
                    <Ellipsis class="size-[13px]" />
                </button>
            </Tooltip>
        </div>
    </div>
{/if}
