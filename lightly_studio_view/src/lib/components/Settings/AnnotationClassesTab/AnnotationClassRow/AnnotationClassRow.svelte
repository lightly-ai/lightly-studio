<script lang="ts">
    import { AnnotationColorLegend } from '$lib/components/AnnotationColorLegend';
    import { Input } from '$lib/components/ui/input';
    import { cn, formatInteger } from '$lib/utils';
    import { AnnotationClassRowActions } from '../AnnotationClassRowActions';
    import { DeleteAnnotationClassDialog } from '../DeleteAnnotationClassDialog';

    interface Props {
        name: string;
        annotationCount: number;
        isHighlighted?: boolean;
        onRename: (name: string) => Promise<unknown>;
        onDelete: () => Promise<unknown>;
    }

    const { name, annotationCount, isHighlighted = false, onRename, onDelete }: Props = $props();

    let row = $state<HTMLLIElement>();

    $effect(() => {
        if (!isHighlighted || !row) return;
        const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        row.scrollIntoView({ block: 'center', behavior: reduceMotion ? 'auto' : 'smooth' });
    });

    let isRenaming = $state(false);
    let isDeleteDialogOpen = $state(false);
    let draft = $state('');

    const startRename = () => {
        draft = name;
        isRenaming = true;
    };
    const saveRename = async () => {
        if (!isRenaming) return;
        isRenaming = false;
        const trimmed = draft.trim();
        if (!trimmed || trimmed === name) return;
        try {
            await onRename(trimmed);
        } catch {
            // The caller already reports the failure; keep showing the old name.
        }
    };
    // The input is inside the settings form, so Enter must not submit it.
    const onRenameKeyDown = (event: KeyboardEvent) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            saveRename();
        } else if (event.key === 'Escape') {
            event.preventDefault();
            event.stopPropagation();
            isRenaming = false;
        }
    };
</script>

<li
    bind:this={row}
    class={cn(
        'group flex h-10 items-center gap-3 rounded-md px-2 focus-within:bg-accent/50 hover:bg-accent/50',
        isHighlighted && 'bg-primary/15 ring-1 ring-inset ring-primary/60 hover:bg-primary/20'
    )}
    data-testid="annotation-class-row"
>
    <AnnotationColorLegend labelName={name} className="size-3" selected />
    {#if isRenaming}
        <Input
            bind:value={draft}
            aria-label={`New name for ${name}`}
            class="h-8"
            wrapperClass="flex-1"
            autofocus
            onfocus={(event) => event.currentTarget.select()}
            onkeydown={onRenameKeyDown}
            onblur={saveRename}
        />
    {:else}
        <span class="min-w-0 flex-1 truncate text-sm" title={name}>{name}</span>
        <span class="shrink-0 text-xs tabular-nums text-muted-foreground">
            {formatInteger(annotationCount)}
            {annotationCount === 1 ? 'annotation' : 'annotations'}
        </span>
        <AnnotationClassRowActions
            {name}
            onRename={startRename}
            onDelete={() => (isDeleteDialogOpen = true)}
        />
    {/if}
</li>

<DeleteAnnotationClassDialog
    bind:open={isDeleteDialogOpen}
    {name}
    {annotationCount}
    onConfirm={onDelete}
/>
