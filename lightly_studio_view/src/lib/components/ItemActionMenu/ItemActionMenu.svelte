<script lang="ts">
    import * as Popover from '$lib/components/ui/popover';
    import { MoreHorizontal, Pencil, Trash2 } from '@lucide/svelte';
    import { Button } from '$lib/components';

    const actionButtonClass =
        'h-7 w-full justify-start gap-2 rounded-sm px-2 py-1 text-xs font-normal text-foreground';
    const defaultActionButtonClass = `${actionButtonClass} hover:bg-accent`;
    const destructiveActionButtonClass = `${actionButtonClass} hover:bg-destructive hover:text-destructive-foreground`;

    let {
        id,
        name,
        kind,
        open,
        deletingId,
        renamingId,
        onOpenChange,
        onCloseAutoFocus,
        onRename,
        onDelete
    }: {
        id: string;
        name: string;
        /** What the item is, as users read it, e.g. "tag" or "annotation source". */
        kind: string;
        open: boolean;
        deletingId: string | null;
        renamingId: string | null;
        onOpenChange: (open: boolean) => void;
        onCloseAutoFocus?: (event: Event) => void;
        onRename: (event: MouseEvent) => void;
        onDelete: (event: MouseEvent) => void;
    } = $props();

    const testIdKind = $derived(kind.replaceAll(' ', '-'));
    const busy = $derived(deletingId !== null || renamingId !== null);
</script>

<Popover.Root {open} onOpenChange={(o) => onOpenChange(o)}>
    <Popover.Trigger
        class="inline-flex size-7 shrink-0 items-center justify-center rounded-md hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-50"
        aria-label={`Open actions for ${kind} ${name}`}
        data-testid={`${testIdKind}-actions-trigger-${id}`}
        disabled={deletingId === id || renamingId === id}
        onclick={(event: MouseEvent) => {
            event.stopPropagation();
        }}
    >
        <MoreHorizontal />
    </Popover.Trigger>
    <Popover.Content
        class="w-max min-w-24 p-1"
        align="end"
        {onCloseAutoFocus}
        onclick={(event: MouseEvent) => {
            event.stopPropagation();
        }}
    >
        <Button
            icon={Pencil}
            buttonProps={{
                type: 'button',
                class: defaultActionButtonClass,
                'data-testid': `rename-${testIdKind}-${id}`,
                'aria-label': `Rename ${kind} ${name}`,
                disabled: busy,
                onclick: onRename
            }}
        >
            Rename
        </Button>
        <Button
            icon={Trash2}
            isPending={deletingId === id}
            buttonProps={{
                type: 'button',
                class: destructiveActionButtonClass,
                'data-testid': `delete-${testIdKind}-${id}`,
                'aria-label': `Delete ${kind} ${name}`,
                disabled: busy,
                onclick: onDelete
            }}
        >
            {deletingId === id ? 'Deleting...' : 'Delete'}
        </Button>
    </Popover.Content>
</Popover.Root>
