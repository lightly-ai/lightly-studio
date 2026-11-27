<script lang="ts">
    import ColorMarker from '$lib/components/SideMenu/ColorMarker/ColorMarker.svelte';
    import { formatInteger } from '$lib/utils';
    import { NameListRowActions } from '$lib/components/Settings/NameList';

    interface Props {
        name: string;
        /** Where the source lives, for example "Frames". Shown after the name. */
        owner?: string;
        annotationCount: number;
        onDelete: () => void;
    }

    const { name, owner, annotationCount, onDelete }: Props = $props();
</script>

<li
    class="group flex h-10 items-center gap-3 rounded-md px-2 focus-within:bg-accent/50 hover:bg-accent/50"
    data-testid="annotation-source-row"
>
    <ColorMarker label={name} enableColorPicker />
    <span class="flex min-w-0 flex-1 items-baseline gap-2">
        <span class="truncate text-sm" title={name}>{name}</span>
        {#if owner}
            <span class="shrink-0 text-xs text-muted-foreground">{owner}</span>
        {/if}
    </span>
    <span class="shrink-0 text-xs tabular-nums text-muted-foreground">
        {formatInteger(annotationCount)}
        {annotationCount === 1 ? 'annotation' : 'annotations'}
    </span>
    <NameListRowActions {name} {onDelete} />
</li>
