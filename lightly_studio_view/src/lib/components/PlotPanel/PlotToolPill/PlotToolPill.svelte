<script lang="ts">
    import { untrack, type Component } from 'svelte';
    import { Button } from '$lib/components';
    import { cn } from '$lib/utils';
    import { Hand, Lasso, SquareDashed, type IconProps } from '@lucide/svelte';
    import {
        SELECTION_TOOLS,
        createSelectionToolController,
        type SelectionToolController,
        type ToolMode
    } from './selectionTool';

    interface Props {
        // The element embedding-atlas renders into. Its hidden toolbar is what the pill drives.
        plotContainer: HTMLElement | null;
    }

    let { plotContainer }: Props = $props();

    // embedding-atlas keeps its active selection mode ("none" = pan, "marquee" = rectangle,
    // "lasso") in a component-internal signal with no public setter, so the only way to change
    // it is to click the library's own toolbar buttons. PlotPanel hides those buttons via CSS
    // and this component clicks them: the pure helpers in ./selectionTool find them and decide
    // which one to toggle, and createSelectionToolController owns the MutationObserver wiring.
    const TOOL_ICONS: Record<ToolMode, Component<IconProps>> = {
        pan: Hand,
        rectangle: SquareDashed,
        lasso: Lasso
    };

    // `activeTool` is the user's choice and the pill's source of truth; the controller re-asserts
    // it whenever the library resets to "none" after a selection, keeping the tool sticky.
    let activeTool = $state<ToolMode>('pan');
    let toolController: SelectionToolController | undefined;

    const selectTool = (mode: ToolMode) => {
        activeTool = mode;
        toolController?.reconcile();
    };

    // Read `activeTool` untracked so this effect depends only on `plotContainer`: choosing a tool
    // must not tear the controller (and its pending-click guard) down mid-selection.
    $effect(() => {
        if (plotContainer === null) return;
        toolController = createSelectionToolController(plotContainer, () =>
            untrack(() => activeTool)
        );
        return () => {
            toolController?.destroy();
            toolController = undefined;
        };
    });
</script>

<!-- Bottom-centered, sharing the bottom edge with the legend on the left. The pill is 6rem
     wide, so it claims 3rem either side of the centre line; PlotPanelLegend caps its own width
     at calc(50% - 4.25rem) to stay clear of that (3rem + a 0.5rem gap + its own 0.75rem inset).
     Change one number and the other has to follow. -->
<div
    class="absolute bottom-2 left-1/2 z-10 flex -translate-x-1/2 items-center gap-1 rounded-lg border border-white/10 bg-black/60 p-1 backdrop-blur-sm"
    data-testid="plot-tool-pill"
>
    {#each SELECTION_TOOLS as tool (tool.mode)}
        <Button
            icon={TOOL_ICONS[tool.mode]}
            ariaLabel={tool.label}
            buttonProps={{
                size: 'icon',
                title: tool.label,
                'aria-pressed': activeTool === tool.mode,
                'data-testid': `plot-tool-${tool.mode}`,
                onclick: () => selectTool(tool.mode),
                class: cn(
                    'size-[26px] text-muted-foreground hover:bg-white/10 hover:text-foreground',
                    activeTool === tool.mode && 'bg-white/[0.14] text-foreground'
                )
            }}
        />
    {/each}
</div>
