<script lang="ts">
    import * as Popover from '$lib/components/ui/popover';
    import { MoreHorizontal, Pencil, Trash2 } from '@lucide/svelte';
    import type { TagView } from '$lib/services/types';

    const actionButtonClass =
        'flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm text-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50';
    const defaultActionButtonClass = `${actionButtonClass} hover:bg-accent`;
    const destructiveActionButtonClass = `${actionButtonClass} hover:bg-destructive hover:text-destructive-foreground`;

    let {
        tag,
        open,
        deletingTagId,
        renamingTagId,
        onOpenChange,
        onCloseAutoFocus,
        onRename,
        onDelete
    }: {
        tag: TagView;
        open: boolean;
        deletingTagId: string | null;
        renamingTagId: string | null;
        onOpenChange: (open: boolean) => void;
        onCloseAutoFocus: (event: Event) => void;
        onRename: (tag: TagView, event: MouseEvent) => void;
        onDelete: (tag: TagView, event: MouseEvent) => void;
    } = $props();
</script>

<Popover.Root {open} onOpenChange={(o) => onOpenChange(o)}>
    <Popover.Trigger
        class="inline-flex size-7 shrink-0 items-center justify-center rounded-md hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-50"
        aria-label={`Open actions for tag ${tag.name}`}
        data-testid={`tag-actions-trigger-${tag.tag_id}`}
        disabled={deletingTagId === tag.tag_id || renamingTagId === tag.tag_id}
        onclick={(event: MouseEvent) => {
            event.stopPropagation();
        }}
    >
        <MoreHorizontal />
    </Popover.Trigger>
    <Popover.Content
        class="w-40 p-1"
        align="end"
        {onCloseAutoFocus}
        onclick={(event: MouseEvent) => {
            event.stopPropagation();
        }}
    >
        <button
            type="button"
            class={defaultActionButtonClass}
            data-testid={`rename-tag-${tag.tag_id}`}
            disabled={deletingTagId !== null || renamingTagId !== null}
            onclick={(event: MouseEvent) => {
                onRename(tag, event);
            }}
        >
            <Pencil class="size-4" />
            Rename tag
        </button>
        <button
            type="button"
            class={destructiveActionButtonClass}
            data-testid={`delete-tag-${tag.tag_id}`}
            disabled={deletingTagId !== null || renamingTagId !== null}
            onclick={(event: MouseEvent) => {
                void onDelete(tag, event);
            }}
        >
            <Trash2 class="size-4" />
            {deletingTagId === tag.tag_id ? 'Deleting...' : 'Delete tag'}
        </button>
    </Popover.Content>
</Popover.Root>
