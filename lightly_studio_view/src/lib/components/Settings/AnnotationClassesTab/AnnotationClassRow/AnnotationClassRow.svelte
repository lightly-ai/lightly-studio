<script lang="ts">
    import { AnnotationColorLegend } from '$lib/components/AnnotationColorLegend';
    import { Input } from '$lib/components/ui/input';
    import { cn, formatInteger } from '$lib/utils';
    import {
        NameListRowActions,
        scrollIntoViewWhen,
        useInlineRename
    } from '$lib/components/Settings/NameList';
    import { DeleteAnnotationClassDialog } from '../DeleteAnnotationClassDialog';

    interface Props {
        name: string;
        annotationCount: number;
        isHighlighted?: boolean;
        onRename: (name: string) => Promise<unknown>;
        onDelete: () => Promise<unknown>;
    }

    const { name, annotationCount, isHighlighted = false, onRename, onDelete }: Props = $props();

    let isDeleteDialogOpen = $state(false);
    const rename = useInlineRename(() => ({ name, onRename }));
</script>

<li
    use:scrollIntoViewWhen={isHighlighted}
    class={cn(
        'group flex h-10 items-center gap-3 rounded-md px-2 focus-within:bg-accent/50 hover:bg-accent/50',
        isHighlighted && 'bg-primary/15 ring-1 ring-inset ring-primary/60 hover:bg-primary/20'
    )}
    data-testid="annotation-class-row"
>
    <AnnotationColorLegend labelName={name} className="size-3" selected />
    {#if rename.isRenaming}
        <Input
            bind:value={rename.draft}
            aria-label={`New name for ${name}`}
            class="h-8"
            wrapperClass="flex-1"
            autofocus
            onfocus={(event) => event.currentTarget.select()}
            onkeydown={rename.onKeyDown}
            onblur={rename.save}
        />
    {:else}
        <span class="min-w-0 flex-1 truncate text-sm" title={name}>{name}</span>
        <span class="shrink-0 text-xs tabular-nums text-muted-foreground">
            {formatInteger(annotationCount)}
            {annotationCount === 1 ? 'annotation' : 'annotations'}
        </span>
        <NameListRowActions
            {name}
            onRename={rename.start}
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
