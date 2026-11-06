<script lang="ts">
    import ColorMarker from '$lib/components/SideMenu/ColorMarker/ColorMarker.svelte';
    import { formatInteger } from '$lib/utils';
    import { NameListRowActions } from '$lib/components/Settings/NameList';

    interface Props {
        name: string;
        annotationCount: number;
        onDelete: () => void;
    }

    const { name, annotationCount, onDelete }: Props = $props();
</script>

<li
    class="group flex h-10 items-center gap-3 rounded-md px-2 focus-within:bg-accent/50 hover:bg-accent/50"
    data-testid="annotation-source-row"
>
    <ColorMarker label={name} enableColorPicker />
    <span class="min-w-0 flex-1 truncate text-sm" title={name}>{name}</span>
    <span class="shrink-0 text-xs tabular-nums text-muted-foreground">
        {formatInteger(annotationCount)}
        {annotationCount === 1 ? 'annotation' : 'annotations'}
    </span>
    <NameListRowActions {name} {onDelete} />
</li>
