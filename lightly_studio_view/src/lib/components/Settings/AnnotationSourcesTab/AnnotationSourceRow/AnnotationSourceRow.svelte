<script lang="ts">
    import ColorMarker from '$lib/components/SideMenu/ColorMarker/ColorMarker.svelte';
    import { Input } from '$lib/components/ui/input';
    import { cn, formatInteger } from '$lib/utils';
    import { AnnotationClassRowActions } from '../../AnnotationClassesTab/AnnotationClassRowActions';

    interface Props {
        name: string;
        annotationCount: number;
        isHighlighted?: boolean;
        onRename: (name: string) => Promise<unknown>;
        onDelete: () => void;
    }

    const { name, annotationCount, isHighlighted = false, onRename, onDelete }: Props = $props();

    let row = $state<HTMLLIElement>();

    $effect(() => {
        if (!isHighlighted || !row) return;
        const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        row.scrollIntoView({ block: 'center', behavior: reduceMotion ? 'auto' : 'smooth' });
    });

    let isRenaming = $state(false);
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
        await onRename(trimmed);
    };
    // The input is inside the settings form, so Enter must not submit it.
    const onRenameKeyDown = (event: KeyboardEvent) => {
        if (event.isComposing || event.keyCode === 229) return;
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
    data-testid="annotation-source-row"
>
    <ColorMarker label={name} enableColorPicker />
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
        <button
            type="button"
            class="min-w-0 flex-1 truncate text-left text-sm"
            title={name}
            onclick={startRename}>{name}</button
        >
        <span class="shrink-0 text-xs tabular-nums text-muted-foreground">
            {formatInteger(annotationCount)}
            {annotationCount === 1 ? 'annotation' : 'annotations'}
        </span>
        <AnnotationClassRowActions {name} onRename={startRename} {onDelete} />
    {/if}
</li>
